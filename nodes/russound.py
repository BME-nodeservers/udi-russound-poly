#!/usr/bin/env python3
"""
Polyglot v3 node server Russound status and control via RNET protocol
Copyright (C) 2020,2021 Robert Paauwe
"""

import udi_interface
import sys
import time
import datetime
import requests
import threading
import socket
import math
import re
import russound_main
from nodes import zone
from nodes import profile
from rnet_message import RNET_MSG_TYPE, ZONE_NAMES, SOURCE_NAMES

LOGGER = udi_interface.LOGGER
Custom = udi_interface.Custom

class Controller(udi_interface.Node):
    id = 'russound'

    def __init__(self, polyglot, primary, address, name):
        super(Controller, self).__init__(polyglot, primary, address, name)
        self.name = name
        self.address = address
        self.primary = primary
        self.configured = False
        self.wait = True
        self.rnet = None
        self.sock = None
        self.mesg_thread = None
        self.zone_count = 0
        self.zone_names = []
        self.source_count = 0
        self.source_names = []
        self.raw_config = bytearray(0)
        self.source_status = 0x00 # assume all sources are inactive

        self.Parameters = Custom(polyglot, "customparams")
        self.Notices = Custom(polyglot, "notices")

        self.poly.subscribe(self.poly.CUSTOMPARAMS, self.parameterHandler)
        self.poly.subscribe(self.poly.START, self.start, address)

        self.poly.ready()
        self.poly.addNode(self)

    # Process changes to customParameters
    def parameterHandler(self, params):
        self.configured = False
        validIP = False
        validPort = False
        validProt = False
        self.Parameters.load(params)

        self.Notices.clear()

        if self.Parameters['IP Address'] is not None and self.Parameters['IP Address'] != '':
            validIP = True
        else:
            self.Notices['ip'] = "Please configure the IP address"
            LOGGER.error('ip address = {}'.format(self.Parameters['IP Address']))

        if self.Parameters['Port'] != '0':
            validPort = True
        else:
            self.Notices['port'] = "Please configure the port number"
            LOGGER.error('port = {}'.format(self.Parameters['Port']))

        if self.Parameters['Network Protocol'].lower() == 'udp' or self.Parameters['Network Protocol'].lower() == 'tcp':
            validProt = True
        else:
            self.Notices['prot'] = "Please configure the network protocol to either UDP or TCP"

        if validIP and validPort and validProt:
            LOGGER.error('Configuration is valid')
            self.configured = True

        self.zone_count = 0
        for z in self.Parameters:
            if z.startswith('Zone'):
                self.zone_count += 1


    def start(self):
        LOGGER.info('Starting node server')
        self.poly.updateProfile()
        self.poly.setCustomParamsDoc()

        if len(self.Parameters) == 0:
            self.Notices['cfg'] = "Please configure IP address, port and network protocol"

        while not self.configured:
            LOGGER.error('Waiting for configuration')
            time.sleep(10)

        # Open a connection to the Russound
        if self.Parameters['Network Protocol'].upper() == 'UDP':
            self.rnet = russound_main.RNETConnection(self.Parameters['IP Address'], self.Parameters['Port'], True)
        else:
            self.rnet = russound_main.RNETConnection(self.Parameters['IP Address'], self.Parameters['Port'], False)

        self.reconnect()

        LOGGER.info('Node server started')

    def reconnect(self):
        self.rnet.Connect()

        if self.rnet.connected:
            # Start a thread that listens for messages from the russound.
            self.mesg_thread = threading.Thread(target=self.rnet.MessageLoop, args=(self.processCommand,))
            self.mesg_thread.daemon = True
            self.mesg_thread.start()

            # Get zone/source configuration for controller 1
            self.rnet.request_config(0) 
            self.wait = True

            # wait for the procesCommand thread to handle the above request.
            # it can take a couple of minutes
            while self.wait:
                time.sleep(2)

            # We now know the number of zones and sources, configure the nodes.
            self.discover()

            # Query each zone
            for z in range(0, self.zone_count):
                self.rnet.get_info(z, 0x0407)
                time.sleep(2)

        if not self.rnet.connected:
            # Connection has failed.
            time.sleep(60)

    def query(self):
        self.reportDrivers()

    def discover(self, *args, **kwargs):
        LOGGER.debug('in discover() - Setting up {} sources'.format(self.source_count))
        """
          TODO:
              Update the NLS file with the source names.  The NLS entries
              are  'SOURCE-[num] = self.sources[num]'

              Update the editor file with the proper range for the sources
              The editor id is "source"
        """
        profile.nls("SOURCE", self.source_names)
        profile.editor('source', min=0, max=self.source_count, uom=25, nls="SOURCE")
        self.poly.updateProfile()

        LOGGER.debug('in discover() - Setting up {} zones'.format(self.zone_count))
        for z in range(0, self.zone_count):
            param = 'Zone ' + str(z + 1)
            zaddr = 'zone_' + str(z + 1)
            node = zone.Zone(self.poly, self.address, zaddr, self.zone_names[z])
            node.setRNET(self.rnet)

            try:
                """
                  if the node exist in the Polyglot database and the name
                  is changing remove it from the database so we can add it
                  with the new name.  Polyglot doesn't let us change the
                  name with addNode()
                """
                old = self.poly.getNode(zaddr)
                if old is not None:
                    if old['name'] != self.zone_names[z]:
                        LOGGER.debug('Need to rename {} to {}'.format(old['name'], self.zone_names[z]))
                        self.delNode(zaddr)
                        time.sleep(1)  # give it time to remove from database
            except:
                LOGGER.warning('Failed to delete node {} {}'.format(old['name'], zaddr))

            self.poly.addNode(node)

    # Delete the node server from Polyglot
    def delete(self):
        LOGGER.info('Removing node server')

    def stop(self):
        LOGGER.info('Stopping node server')

    def update_profile(self, command):
        st = self.poly.installprofile()
        return st

    def set_source_selection(self, state, source):
        source_map = ['GV1', 'GV2', 'GV3', 'GV4', 'GV5', 'GV6']

        # if state is on, set source bit else clear source bit
        if state == 0x01:
            LOGGER.info('Source ' + str(source+1) + ' is ACTIVE')
            self.source_status = self.source_status | (1 >> source)
            self.reportCmd(source_map[source], 1, 25)
            self.setDriver(source_map[source], 1)
        else:
            LOGGER.info('Source ' + str(source+1) + ' is INACTIVE')
            self.source_status = self.source_status & ~(1 >> source)
            self.reportCmd(source_map[source], 0, 25)
            self.setDriver(source_map[source], 0)
        
    """
      When we query the controller for the configuration it sends
      back a large block of data that contains the zone and source
      configuration information.  This includes the names.  It
      also includes the user defined custom names.  This info
      appears to be just a small part of the data.  The rest is 
      still unknown.
    """
    def decode_config(self, cfgdata):
        custom_names = []
        self.zone_names = []
        self.source_names = ['Inactive']

        LOGGER.debug('Number of zones = {}'.format(cfgdata[0]))
        zones = cfgdata[0]
        LOGGER.debug('Number of sources = {}'.format(cfgdata[1]))
        sources = cfgdata[0]

        for c in range(0, 10):
            st = 0x2728 + c * 20
            custom_names.append(cfgdata[st:st+13].decode('utf-8').replace('\x00', ''))
            LOGGER.debug('custom name {} = {}'.format(c, custom_names[c]))

        for s in range(0, sources):
            idx = int(cfgdata[2 + s * 24])
            if idx >= 73 and idx <= 82:
                # custom name, replace
                self.source_names.append(custom_names[idx - 73])
            else:
                self.source_names.append(SOURCE_NAMES[idx])
            LOGGER.debug('source {} = {} ({})'.format(s, self.source_names[s], idx))

        for z in range(0, zones):
            idx = int(cfgdata[0x92 + z * 562])
            if idx >= 52 and idx <= 61:
                # custom name, replace
                self.zone_names.append(custom_names[idx - 52])
            else:
                self.zone_names.append(ZONE_NAMES[idx])
            LOGGER.debug('zone {} = {} ({})'.format(z, self.zone_names[z], idx))

        self.zone_count = zones
        self.source_count = sources

    def processCommand(self, msg):
        zone = msg.TargetZone() + 1
        zone_addr = 'zone_' + str(zone)

        if msg.MessageType() == RNET_MSG_TYPE.LOST_CONNECTION:
            LOGGER.error('Got lost connection message!!  Restart?')
            self.reconnect()
            return

        if zone == 0x7d:
            LOGGER.debug('Message is targeted at RNET peripherals, not a zone')
            return

        if zone >= 0x70:
            LOGGER.debug('Message target not a zone: ' + str(zone))
            return

        if msg.MessageType() == RNET_MSG_TYPE.ZONE_STATE:
            # It looks like the zone state is in the TS field. 
            LOGGER.debug(' -> Zone %d state = 0x%x' % (msg.TargetZone(), msg.MessageData()))
            zone_addr = 'zone_' + str(msg.TargetZone() + 1)
            self.poly.nodes[zone_addr].set_power(int(msg.MessageData()))
        elif msg.MessageType() == RNET_MSG_TYPE.ZONE_SOURCE:
            LOGGER.debug(' -> Zone %d source = 0x%x' % (zone, msg.MessageData()+1))
            self.poly.nodes[zone_addr].set_source(int(msg.MessageData()))
        elif msg.MessageType() == RNET_MSG_TYPE.ZONE_VOLUME:
            # See what we get here.  Then try to update the actual node
            # for the zone
            LOGGER.debug(' -> Zone %d volume = 0x%x' % (zone, msg.MessageData()))
            self.poly.nodes[zone_addr].set_volume(int(msg.MessageData()))
        elif msg.MessageType() == RNET_MSG_TYPE.ZONE_BASS:
            LOGGER.debug(' -> Zone %d bass = 0x%x' % (zone, msg.MessageData()))
            self.poly.nodes[zone_addr].set_bass(int(msg.MessageData()))
        elif msg.MessageType() == RNET_MSG_TYPE.ZONE_TREBLE:
            LOGGER.debug(' -> Zone %d treble = 0x%x' % (zone, msg.MessageData()))
            self.poly.nodes[zone_addr].set_treble(int(msg.MessageData()))
        elif msg.MessageType() == RNET_MSG_TYPE.ZONE_BALANCE:
            LOGGER.debug(' -> Zone %d balance = 0x%x' % (zone, msg.MessageData()))
            self.poly.nodes[zone_addr].set_balance(int(msg.MessageData()))
        elif msg.MessageType() == RNET_MSG_TYPE.ZONE_LOUDNESS:
            LOGGER.debug(' -> Zone %d loudness = 0x%x' % (zone, msg.MessageData()))
            self.poly.nodes[zone_addr].set_loudness(int(msg.MessageData()))
        elif msg.MessageType() == RNET_MSG_TYPE.ZONE_PARTY_MODE:
            LOGGER.debug(' -> Zone %d party mode = 0x%x' % (zone, msg.MessageData()))
            self.poly.nodes[zone_addr].set_party_mode(int(msg.MessageData()))
        elif msg.MessageType() == RNET_MSG_TYPE.ZONE_DO_NOT_DISTURB:
            LOGGER.debug(' -> Zone %d do not disturb = 0x%x' % (zone, msg.MessageData()))
            self.poly.nodes[zone_addr].set_dnd(int(msg.MessageData()))
        elif msg.MessageType() == RNET_MSG_TYPE.UPDATE_SOURCE_SELECTION:
            # We can use this to check for sources going on/off (or really
            # being activated/deactivated). The value returned is a bitmap
            # that indicates which sources are active.  By looking at what
            # has changed since the last time we saw this message, we can
            # track the source state transitions.
            LOGGER.debug(' -> Update Zone source 0x%x 0x%x' % (msg.MessageData()[0], msg.MessageData()[1]))

            # First, look only at what has changed since the last time this
            # was called.
            ns = msg.MessageData()[0]
            ss = ns ^ self.source_status

            # Based on what changed send a command to the ISY that
            # can be used as a source activated trigger.
            if (ss & 0x01) == 0x01:  # source 1 changed
                LOGGER.info('Source 1 changed')
                if (ns & 0x01) == 0x01: # source 1 activated
                    self.setDriver('GV1', 1)
                else:
                    self.setDriver('GV1', 0)
            if (ss & 0x02) == 0x02:  # source 2 changed
                LOGGER.info('Source 2 changed')
                if (ns & 0x02) == 0x02: # source 2 activated
                    self.setDriver('GV2', 1)
                else:
                    self.setDriver('GV2', 0)
            if (ss & 0x04) == 0x04:  # source 3 changed
                LOGGER.info('Source 3 changed')
                if (ns & 0x04) == 0x04: # source 3 activated
                    self.setDriver('GV3', 1)
                else:
                    self.setDriver('GV3', 0)
            if (ss & 0x08) == 0x08:  # source 4 changed
                LOGGER.info('Source 4 changed')
                if (ns & 0x08) == 0x08: # source 4 activated
                    self.setDriver('GV4', 1)
                else:
                    self.setDriver('GV4', 0)
            if (ss & 0x10) == 0x10:  # source 5 changed
                LOGGER.info('Source 5 changed')
                if (ns & 0x10) == 0x10: # source 5 activated
                    self.setDriver('GV5', 1)
                else:
                    self.setDriver('GV5', 0)
            if (ss & 0x20) == 0x20:  # source 6 changed
                LOGGER.info('Source 6 changed')
                if (ns & 0x20) == 0x20: # source 6 activated
                    self.setDriver('GV6', 1)
                else:
                    self.setDriver('GV6', 0)

            self.source_status = ns
        elif msg.MessageType() == RNET_MSG_TYPE.CONTROLLER_CONFIG:
            """
              This is a multi-packet message.  We need to combine
              all the packets into one binary blob.  Then we can
              process the blob to get zone names, source names,
              number of zones, number of sources, etc.
            """
            LOGGER.debug('Got packet {} of {}'.format(msg.PacketNumber(), msg.PacketCount()))
            if msg.PacketNumber() == 0:  # first packet
                self.raw_config = bytearray(0)
            
            if msg.PacketNumber() == msg.PacketCount() - 1: # last packet
                self.raw_config.extend(msg.MessageData())
                self.decode_config(self.raw_config)
                self.wait = False
            else:
                self.raw_config.extend(msg.MessageData())

        elif msg.MessageType() == RNET_MSG_TYPE.UNDOCUMENTED:
            """
            FIXME: This should now be handled by approprate message
            types.
            # this seems to be the only thing we get when we select
            # a source from the keypad.
            # example:
            #   49 03 00 00 05
            #   MessageData[0] varies
            #   MessageData[1] is the source
            #   MessageData[4] is 5, does this mean source select?
            # param 0x90 is volume?
            # event data:
            #  0x01 (01) == 2
            #  0x0c (12) == 24
            #  0x0d (13) == 26
            #  0x0e (14) == 28
            #  0x16 (22) == 44
            if msg.EventId() == 0x90:
                LOGGER.debug(' -> Volume adjusted to: ' + str(msg.EventData()))
            elif msg.MessageData()[4] == 0x05: #  source selection
                LOGGER.debug(' -> Zone {} set to source {}'.format(zone_addr, msg.MessageData()[1]+1))
                self.poly.nodes[zone_addr].set_source(int(msg.MessageData()[1]))
            else:
                LOGGER.debug(' -> param 0x%x = 0x%x for zone %d' % (msg.EventId(), msg.EventData(), msg.EventZone()))
                #LOGGER.debug('   D ' + ' '.join('{:02x}'.format(x) for x in msg.MessageData()))
            """

        # Do we care about keypad events?  Maybe in the sense that we'd
        # like to create a program that is something like:
        #
        #  if zone keypress == Next then do something
        #
        # which means we need a node driver that holds the last keypress
        # value.
        elif msg.MessageType() == RNET_MSG_TYPE.ALL_ZONE_INFO:
            LOGGER.info('All zone info for ' + zone_addr)
            LOGGER.debug('   ' + ' '.join('{:02x}'.format(x) for x in msg.MessageData()))
            LOGGER.info('   power state = ' + str(msg.MessageData()[0]))
            LOGGER.info('   source      = ' + str(msg.MessageData()[1] + 1))
            LOGGER.info('   volume      = ' + str(msg.MessageData()[2]))
            LOGGER.info('   bass        = ' + str(msg.MessageData()[3]))
            LOGGER.info('   treble      = ' + str(msg.MessageData()[4]))
            LOGGER.info('   loudness    = ' + str(msg.MessageData()[5]))
            LOGGER.info('   balance     = ' + str(msg.MessageData()[6]))
            LOGGER.info('   party       = ' + str(msg.MessageData()[7]))
            LOGGER.info('   dnd         = ' + str(msg.MessageData()[8]))

            self.poly.nodes[zone_addr].set_power(int(msg.MessageData()[0]))
            self.poly.nodes[zone_addr].set_source(int(msg.MessageData()[1]))
            self.poly.nodes[zone_addr].set_volume(int(msg.MessageData()[2]))
            self.poly.nodes[zone_addr].set_bass(int(msg.MessageData()[3]))
            self.poly.nodes[zone_addr].set_treble(int(msg.MessageData()[4]))
            self.poly.nodes[zone_addr].set_loudness(int(msg.MessageData()[5]))
            self.poly.nodes[zone_addr].set_balance(int(msg.MessageData()[6]))
            self.poly.nodes[zone_addr].set_party_mode(int(msg.MessageData()[7]))
            self.poly.nodes[zone_addr].set_dnd(int(msg.MessageData()[8]))

            self.set_source_selection(msg.MessageData()[0], msg.MessageData()[1])

        elif msg.MessageType() == RNET_MSG_TYPE.KEYPAD_POWER:
            # The power key is special. We'd like it to send either DON or DOF
            # depending on what state we'll be moving into
            zone_addr = 'zone_' + str(msg.SourceZone() + 1)
            if self.poly.nodes[zone_addr].get_power():
                self.poly.nodes[zone_addr].keypress('DOF')
            else:
                self.poly.nodes[zone_addr].keypress('DON')
        elif msg.MessageType() == RNET_MSG_TYPE.KEYPAD_FAV1:
            zone_addr = 'zone_' + str(msg.SourceZone() + 1)
            self.poly.nodes[zone_addr].keypress('GV18')
        elif msg.MessageType() == RNET_MSG_TYPE.KEYPAD_FAV2:
            zone_addr = 'zone_' + str(msg.SourceZone() + 1)
            self.poly.nodes[zone_addr].keypress('GV19')
        elif msg.MessageType() == RNET_MSG_TYPE.KEYPAD_PLUS:
            zone_addr = 'zone_' + str(msg.SourceZone() + 1)
            self.poly.nodes[zone_addr].keypress('BRT')
        elif msg.MessageType() == RNET_MSG_TYPE.KEYPAD_MINUS:
            zone_addr = 'zone_' + str(msg.SourceZone() + 1)
            self.poly.nodes[zone_addr].keypress('DIM')
        elif msg.MessageType() == RNET_MSG_TYPE.KEYPAD_NEXT:
            zone_addr = 'zone_' + str(msg.SourceZone() + 1)
            self.poly.nodes[zone_addr].keypress('GV16')
        elif msg.MessageType() == RNET_MSG_TYPE.KEYPAD_PREVIOUS:
            zone_addr = 'zone_' + str(msg.SourceZone() + 1)
            self.poly.nodes[zone_addr].keypress('GV15')
        elif msg.MessageType() == RNET_MSG_TYPE.KEYPAD_SOURCE:
            zone_addr = 'zone_' + str(msg.SourceZone() + 1)
            self.poly.nodes[zone_addr].keypress('GV14')
        elif msg.MessageType() == RNET_MSG_TYPE.KEYPAD_PLAY:
            zone_addr = 'zone_' + str(msg.SourceZone() + 1)
            self.poly.nodes[zone_addr].keypress('GV17')
        elif msg.MessageType() == RNET_MSG_TYPE.KEYPAD_VOL_UP:
            zone_addr = 'zone_' + str(msg.SourceZone() + 1)
            self.poly.nodes[zone_addr].keypress('GV12')
        elif msg.MessageType() == RNET_MSG_TYPE.KEYPAD_VOL_DOWN:
            zone_addr = 'zone_' + str(msg.SourceZone() + 1)
            self.poly.nodes[zone_addr].keypress('GV13')
        elif msg.MessageType() == RNET_MSG_TYPE.KEYPAD_NEXT:
            LOGGER.debug(' -> Keypad next')
        elif msg.MessageType() == RNET_MSG_TYPE.UNKNOWN_SET:
            # don't think we really care about these
            LOGGER.debug('US -> ' + ' '.join('{:02x}'.format(x) for x in msg.MessageRaw()))
        else:
            LOGGER.debug(' -> TODO: message id ' + str(msg.MessageType().name) + ' not yet implemented.')


    commands = {
            'UPDATE_PROFILE': update_profile,
            }

    # For this node server, all of the info is available in the single
    # controller node.
    drivers = [
            {'driver': 'ST', 'value': 1, 'uom': 2},   # node server status
            {'driver': 'GV1', 'value': 0, 'uom': 25},  # source 1 On/off status
            {'driver': 'GV2', 'value': 0, 'uom': 25},  # source 2 On/off status
            {'driver': 'GV3', 'value': 0, 'uom': 25},  # source 3 On/off status
            {'driver': 'GV4', 'value': 0, 'uom': 25},  # source 4 On/off status
            {'driver': 'GV5', 'value': 0, 'uom': 25},  # source 5 On/off status
            {'driver': 'GV6', 'value': 0, 'uom': 25},  # source 6 On/off status
            ]

