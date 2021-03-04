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
from rnet_message import RNET_MSG_TYPE

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
        self.rnet = None
        self.sock = None
        self.mesg_thread = None
        self.zone_count = 0
        self.source_status = 0x00 # assume all sources are inactive

        self.Parameters = Custom(polyglot, "customparams")
        self.Notices = Custom(polyglot, "notices")

        self.poly.subscribe(self.poly.CUSTOMPARAMS, self.parameterHandler)
        self.poly.subscribe(self.poly.START, self.start, address)

        self.poly.ready()
        self.poly.addNode(self)

        """
        self.params = node_funcs.NSParameters([{
            'name': 'IP Address',
            'default': 'set me',
            'isRequired': True,
            'notice': 'IP Address of serial network interface must be set',
            },
            {
            'name': 'Port',
            'default': '0',
            'isRequired': True,
            'notice': 'Serial network interface port must be set',
            },
            {
            'name': 'Network Protocol',
            'default': 'UDP',
            'isRequired': False,
            'notice': '',
            },
            {
            'name': 'Zone 1',
            'default': 'Zone 1',
            'isRequired': False,
            'notice': '',
            },
            {
            'name': 'Zone 2',
            'default': 'Zone 2',
            'isRequired': False,
            'notice': '',
            },
            {
            'name': 'Zone 3',
            'default': 'Zone 3',
            'isRequired': False,
            'notice': '',
            },
            {
            'name': 'Zone 4',
            'default': 'Zone 4',
            'isRequired': False,
            'notice': '',
            },
            {
            'name': 'Zone 5',
            'default': 'Zone 5',
            'isRequired': False,
            'notice': '',
            },
            {
            'name': 'Zone 6',
            'default': 'Zone 6',
            'isRequired': False,
            'notice': '',
            },
            ])
            """

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
        self.discover()

        if self.rnet.connected:
            # Start a thread that listens for messages from the russound.
            self.mesg_thread = threading.Thread(target=self.rnet.MessageLoop, args=(self.processCommand,))
            self.mesg_thread.daemon = True
            self.mesg_thread.start()

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
        LOGGER.debug('in discover() - Setting up zones')
        for z in range(0, self.zone_count):
            param = 'Zone ' + str(z + 1)
            zaddr = 'zone_' + str(z + 1)
            node = zone.Zone(self.poly, self.address, zaddr, self.Parameters[param])
            node.setRNET(self.rnet)

            try:
                # if the node exist in the Polyglot database and the name is changing
                # remove it from the database so we can add it with the new name.
                old = self.poly.getNode(zaddr)
                if old['name'] != self.Parameters[param]:
                    self.delNode(zaddr)
                    time.sleep(1)  # give it time to remove from database
            except:
                LOGGER.warning('Failed to delete node ' + param)

            self.poly.addNode(node)

        # configuation should hold name for each zone and name for each
        # source. Here we should map the zone names to what is reported
        # by the russound and create zone nodes.  When we create the
        # zone node, pass in the source name list.


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

