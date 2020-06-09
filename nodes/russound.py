#!/usr/bin/env python3
"""
Polyglot v2 node server Russound status and control via RNET protocol
Copyright (C) 2020 Robert Paauwe
"""

try:
    import polyinterface
except ImportError:
    import pgc_interface as polyinterface
import sys
import time
import datetime
import requests
import threading
import socket
import math
import re
import russound_main
import node_funcs
from nodes import zone
from rnet_message import RNET_MSG_TYPE

LOGGER = polyinterface.LOGGER

@node_funcs.add_functions_as_methods(node_funcs.functions)
class Controller(polyinterface.Controller):
    id = 'russound'
    hint = [0,0,0,0]

    def __init__(self, polyglot):
        super(Controller, self).__init__(polyglot)
        self.name = 'Russound'
        self.address = 'rnet'
        self.primary = self.address
        self.configured = False
        self.rnet = None
        self.sock = None
        self.mesg_thread = None
        self.source_status = 0x00 # assume all sources are inactive

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

        self.poly.onConfig(self.process_config)

    # Process changes to customParameters
    def process_config(self, config):
        (valid, changed) = self.params.update_from_polyglot(config)
        if changed and not valid:
            LOGGER.debug('-- configuration not yet valid')
            self.removeNoticesAll()
            self.params.send_notices(self)
        elif changed and valid:
            LOGGER.debug('-- configuration is valid')
            self.removeNoticesAll()
            self.configured = True
            # TODO: Run discovery/startup here?
        elif valid:
            LOGGER.debug('-- configuration not changed, but is valid')
            # is this necessary
            #self.configured = True

    def start(self):
        LOGGER.info('Starting node server')
        self.set_logging_level()
        self.check_params()

        # Open a connection to the Russound
        if self.configured:
            self.rnet = russound_main.RNETConnection(self.params.get('IP Address'), self.params.get('Port'), True)
            self.rnet.Connect()

            self.discover()

            if self.rnet.connected:
                # Start a thread that listens for messages from the russound.
                self.mesg_thread = threading.Thread(target=self.rnet.MessageLoop, args=(self.processCommand,))
                self.mesg_thread.daemon = True
                self.mesg_thread.start()

                # Query each zone
                self.rnet.get_info(0, 0x0407)
                time.sleep(2)
                self.rnet.get_info(1, 0x0407)
                time.sleep(2)
                self.rnet.get_info(2, 0x0407)
                time.sleep(2)
                self.rnet.get_info(3, 0x0407)
                time.sleep(2)
                self.rnet.get_info(4, 0x0407)
                time.sleep(2)
                self.rnet.get_info(5, 0x0407)

            LOGGER.info('Node server started')
        else:
            LOGGER.info('Waiting for configuration to be complete')

    def longPoll(self):
        pass

    def shortPoll(self):
        pass

    def query(self):
        for node in self.nodes:
            self.nodes[node].reportDrivers()

    def discover(self, *args, **kwargs):
        LOGGER.debug('in discover() - Setting up zones')
        for z in range(1,7):
            param = 'Zone ' + str(z)
            node = zone.Zone(self, self.address, 'zone_' + str(z), self.params.get(param))
            node.setRNET(self.rnet)

            try:
                old = self.poly.getNode('zone_' + str(z))
                if old['name'] != self.params.get(param):
                    self.delNode('zone_' + str(z))
                    time.sleep(1)  # give it time to remove from database
            except:
                LOGGER.warning('Failed to delete node ' + param)

            self.addNode(node)

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

    def check_params(self):
        # NEW code, try this:
        self.removeNoticesAll()

        if self.params.get_from_polyglot(self):
            LOGGER.debug('All required parameters are set!')
            self.configured = True
        else:
            LOGGER.debug('Configuration required.')
            LOGGER.debug('IP Address = ' + self.params.get('IP Address'))
            LOGGER.debug('Port = ' + self.params.get('Port'))
            self.params.send_notices(self)

    def remove_notices_all(self, command):
        self.removeNoticesAll()

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

        if zone >= 0x70:
            LOGGER.debug('Message target not a zone: ' + str(zone))
            return

        if msg.MessageType() == RNET_MSG_TYPE.ZONE_STATE:
            # It looks like the zone state is in the TS field. 
            LOGGER.debug(' -> Zone %d state = 0x%x' % (msg.TargetZone(), msg.EventTS()))
            zone_addr = 'zone_' + str(msg.TargetZone() + 1)
            self.nodes[zone_addr].set_power(int(msg.EventTS()))
        elif msg.MessageType() == RNET_MSG_TYPE.ZONE_SOURCE:
            LOGGER.debug(' -> Zone %d source = 0x%x' % (zone, msg.MessageData()[20]))
            self.nodes[zone_addr].set_source(int(msg.MessageData()[20]))
        elif msg.MessageType() == RNET_MSG_TYPE.ZONE_VOLUME:
            # See what we get here.  Then try to update the actual node
            # for the zone
            LOGGER.debug(' -> Zone %d volume = 0x%x' % (zone, msg.MessageData()[0]))
            self.nodes[zone_addr].set_volume(int(msg.MessageData()[0]))
        elif msg.MessageType() == RNET_MSG_TYPE.ZONE_BASS:
            LOGGER.debug(' -> Zone %d bass = 0x%x' % (zone, msg.MessageData()[20]))
            self.nodes[zone_addr].set_bass(int(msg.MessageData()[20]))
        elif msg.MessageType() == RNET_MSG_TYPE.ZONE_TREBLE:
            LOGGER.debug(' -> Zone %d treble = 0x%x' % (zone, msg.MessageData()[20]))
            self.nodes[zone_addr].set_treble(int(msg.MessageData()[20]))
        elif msg.MessageType() == RNET_MSG_TYPE.ZONE_BALANCE:
            LOGGER.debug(' -> Zone %d balance = 0x%x' % (zone, msg.MessageData()[20]))
            LOGGER.warning('   ' + ' '.join('{:02x}'.format(x) for x in msg.MessageData()))
            self.nodes[zone_addr].set_balance(int(msg.MessageData()[20]))
        elif msg.MessageType() == RNET_MSG_TYPE.ZONE_LOUDNESS:
            LOGGER.debug(' -> Zone %d loudness = 0x%x' % (zone, msg.MessageData()[20]))
            self.nodes[zone_addr].set_loudness(int(msg.MessageData()[20]))
        elif msg.MessageType() == RNET_MSG_TYPE.ZONE_PARTY_MODE:
            LOGGER.debug(' -> Zone %d party mode = 0x%x' % (zone, msg.MessageData()[20]))
            self.nodes[zone_addr].set_party_mode(int(msg.MessageData()[20]))
        elif msg.MessageType() == RNET_MSG_TYPE.ZONE_DO_NOT_DISTURB:
            LOGGER.debug(' -> Zone %d do not disturb = 0x%x' % (zone, msg.MessageData()[20]))
            self.nodes[zone_addr].set_dnd(int(msg.MessageData()[20]))
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
            # param 0x90 is volume?
            # event data:
            #  0x01 (01) == 2
            #  0x0c (12) == 24
            #  0x0d (13) == 26
            #  0x0e (14) == 28
            #  0x16 (22) == 44
            LOGGER.debug(' -> param 0x%x = 0x%x for zone %d' % (msg.EventId(), msg.EventData(), msg.EventZone()))

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

            self.nodes[zone_addr].set_power(int(msg.MessageData()[0]))
            self.nodes[zone_addr].set_source(int(msg.MessageData()[1]))
            self.nodes[zone_addr].set_volume(int(msg.MessageData()[2]))
            self.nodes[zone_addr].set_bass(int(msg.MessageData()[3]))
            self.nodes[zone_addr].set_treble(int(msg.MessageData()[4]))
            self.nodes[zone_addr].set_loudness(int(msg.MessageData()[5]))
            self.nodes[zone_addr].set_balance(int(msg.MessageData()[6]))
            self.nodes[zone_addr].set_party_mode(int(msg.MessageData()[7]))
            self.nodes[zone_addr].set_dnd(int(msg.MessageData()[8]))

            self.set_source_selection(msg.MessageData()[0], msg.MessageData()[1])

        elif msg.MessageType() == RNET_MSG_TYPE.KEYPAD_POWER:
            # The power key is special. We'd like it to send either DON or DOF
            # depending on what state we'll be moving into
            zone_addr = 'zone_' + str(msg.SourceZone() + 1)
            if self.nodes[zone_addr].get_power():
                self.nodes[zone_addr].keypress('DOF')
            else:
                self.nodes[zone_addr].keypress('DON')
        elif msg.MessageType() == RNET_MSG_TYPE.KEYPAD_FAV1:
            zone_addr = 'zone_' + str(msg.SourceZone() + 1)
            self.nodes[zone_addr].keypress('GV18')
        elif msg.MessageType() == RNET_MSG_TYPE.KEYPAD_FAV2:
            zone_addr = 'zone_' + str(msg.SourceZone() + 1)
            self.nodes[zone_addr].keypress('GV19')
        elif msg.MessageType() == RNET_MSG_TYPE.KEYPAD_PLUS:
            zone_addr = 'zone_' + str(msg.SourceZone() + 1)
            self.nodes[zone_addr].keypress('BRT')
        elif msg.MessageType() == RNET_MSG_TYPE.KEYPAD_MINUS:
            zone_addr = 'zone_' + str(msg.SourceZone() + 1)
            self.nodes[zone_addr].keypress('DIM')
        elif msg.MessageType() == RNET_MSG_TYPE.KEYPAD_NEXT:
            zone_addr = 'zone_' + str(msg.SourceZone() + 1)
            self.nodes[zone_addr].keypress('GV16')
        elif msg.MessageType() == RNET_MSG_TYPE.KEYPAD_PREVIOUS:
            zone_addr = 'zone_' + str(msg.SourceZone() + 1)
            self.nodes[zone_addr].keypress('GV15')
        elif msg.MessageType() == RNET_MSG_TYPE.KEYPAD_SOURCE:
            zone_addr = 'zone_' + str(msg.SourceZone() + 1)
            self.nodes[zone_addr].keypress('GV14')
        elif msg.MessageType() == RNET_MSG_TYPE.KEYPAD_PLAY:
            zone_addr = 'zone_' + str(msg.SourceZone() + 1)
            self.nodes[zone_addr].keypress('GV17')
        elif msg.MessageType() == RNET_MSG_TYPE.KEYPAD_VOL_UP:
            zone_addr = 'zone_' + str(msg.SourceZone() + 1)
            self.nodes[zone_addr].keypress('GV12')
        elif msg.MessageType() == RNET_MSG_TYPE.KEYPAD_VOL_DOWN:
            zone_addr = 'zone_' + str(msg.SourceZone() + 1)
            self.nodes[zone_addr].keypress('GV13')
        elif msg.MessageType() == RNET_MSG_TYPE.KEYPAD_NEXT:
            LOGGER.debug(' -> Keypad next')
        elif msg.MessageType() == RNET_MSG_TYPE.UNKNOWN_SET:
            # don't think we really care about these
            LOGGER.debug('US -> ' + ' '.join('{:02x}'.format(x) for x in msg.MessageRaw()))
        else:
            LOGGER.debug(' -> TODO: message id ' + str(msg.MessageType().name) + ' not yet implemented.')


    def set_logging_level(self, level=None):
        if level is None:
            try:
                level = self.get_saved_log_level()
            except:
                LOGGER.error('set_logging_level: get saved level failed.')

            if level is None:
                level = 10
            level = int(level)
        else:
            level = int(level['value'])

        self.save_log_level(level)

        LOGGER.info('set_logging_level: Setting log level to %d' % level)
        LOGGER.setLevel(level)


    commands = {
            'UPDATE_PROFILE': update_profile,
            'REMOVE_NOTICES_ALL': remove_notices_all,
            'DEBUG': set_logging_level,
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

