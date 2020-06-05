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
        self.uom = {}
        self.sock = None

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
            LOGGER.info('finish startup code if not already complete.')
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
            self.sock = russound_main.russound_connect_udp(self.params.get('Port'))

            self.discover()

            # TODO:
            # do we need to start a thread that listens for messages from
            # the russound and hands those off to the appropriate zone?
            if self.sock != None:
                russound_main.russound_loop_udp(self.sock, self.processCommand)

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
        LOGGER.debug('in discover() - Look up zone/source info?')

        for z in range(1,7):
            #LOGGER.debug('zone %d power = %d' % (z, self.r.get_power('1', z)))
            node = zone.Zone(self, self.address, 'zone_' + str(z), 'Zone ' + str(z))
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

    def processCommand(self, msg):
        zone = msg.TargetZone()

        if zone >= 0x70:
            LOGGER.warning('Message target not a zone: ' + str(zone))
            return

        if msg.MessageType() == RNET_MSG_TYPE.ZONE_STATE:
            # It looks like the zone state is in the TS field. 
            LOGGER.warning(' -> Zone %d state = 0x%x' % (msg.TargetZone(), msg.EventTS()))
            zone_addr = 'zone_' + str(msg.TargetZone() + 1)
            self.nodes[zone_addr].set_power(int(msg.EventTS()))
        elif msg.MessageType() == RNET_MSG_TYPE.ZONE_SOURCE:
            LOGGER.warning(' -> Zone %d source = 0x%x' % (msg.TargetZone(), msg.MessageData()[0]))
        elif msg.MessageType() == RNET_MSG_TYPE.ZONE_VOLUME:
            # See what we get here.  Then try to update the actual node
            # for the zone
            LOGGER.warning(' -> Zone %d volume = 0x%x' % (msg.TargetZone(), msg.MessageData()[0]))
            zone_addr = 'zone_' + str(msg.TargetZone() + 1)
            self.nodes[zone_addr].set_volume(int(msg.MessageData()[0]) * 2)
        elif msg.MessageType() == RNET_MSG_TYPE.ZONE_BASS:
            LOGGER.warning(' -> Zone %d bass = 0x%x' % (msg.TargetZone(), msg.MessageData()[0]))
        elif msg.MessageType() == RNET_MSG_TYPE.ZONE_TREBLE:
            LOGGER.warning(' -> Zone %d treble = 0x%x' % (msg.TargetZone(), msg.MessageData()[0]))
        elif msg.MessageType() == RNET_MSG_TYPE.ZONE_BALANCE:
            LOGGER.warning(' -> Zone %d balance = 0x%x' % (msg.TargetZone(), msg.MessageData()[0]))
        elif msg.MessageType() == RNET_MSG_TYPE.UPDATE_SOURCE_SELECTION:
            # Seem to get this a lot
            # Looks like MessageData[0] is a bit field where each bit
            # represents the source so we get:
            # 0, 1, 2, 4, 8 as we cycle through source 1, 2, 3, 4
            LOGGER.warning(' -> Update Zone source 0x%x 0x%x' % (msg.MessageData()[0], msg.MessageData()[1]))
            #LOGGER.warning('    evt = ' + ''.join('{:02x}'.format(x) for x in msg.EventRaw()))
            #LOGGER.warning('    msg = ' + ''.join('{:02x}'.format(x) for x in msg.MessageRaw()))
            source_bit = msg.MessageData()[0]
            if source_bit & 0x01:
                source = 1
            elif source_bit & 0x02:
                source = 2
            elif source_bit & 0x04:
                source = 3
            elif source_bit & 0x08:
                source = 4
            elif source_bit & 0x0f:
                source = 5
            elif source_bit & 0x10:
                source = 6
            elif source_bit & 0x20:
                source = 7

            zone_addr = 'zone_' + str(msg.TargetZone() + 1)
            LOGGER.warning('    zone = ' + zone_addr)
            self.nodes[zone_addr].set_source(source)
        elif msg.MessageType() == RNET_MSG_TYPE.UNDOCUMENTED:
            # param 0x90 is volume?
            # event data:
            #  0x01 (01) == 2
            #  0x0c (12) == 24
            #  0x0d (13) == 26
            #  0x0e (14) == 28
            #  0x16 (22) == 44
            LOGGER.warning(' -> param 0x%x = 0x%x for zone %d' % (msg.EventId(), msg.EventData(), msg.EventZone()))

        # Do we care about keypad events?  Maybe in the sense that we'd
        # like to create a program that is something like:
        #
        #  if zone keypress == Next then do something
        #
        # which means we need a node driver that holds the last keypress
        # value.
        elif msg.MessageType() == RNET_MSG_TYPE.KEYPAD_NEXT:
            LOGGER.warning(' -> Keypad next')
        elif msg.MessageType() == RNET_MSG_TYPE.KEYPAD_POWER:
            LOGGER.warning(' -> Keypad power' + str(msg.EventData()))
            #LOGGER.warning('    raw = ' + ''.join('{:02x}'.format(x) for x in msg.EventRaw()))
            #LOGGER.warning('    raw = ' + ''.join('{:02x}'.format(x) for x in msg.MessageData()))
        elif msg.MessageType() == RNET_MSG_TYPE.UNKNOWN_SET:
            # don't think we really care about these
            LOGGER.warning(' -> ' + ''.join('{:02x}'.format(x) for x in msg.MessageData()))
        else:
            LOGGER.warning(' -> TODO: message id ' + str(msg.MessageType().name))


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
            {'driver': 'GV0', 'value': 0, 'uom': 2},   # On/off status
            ]

