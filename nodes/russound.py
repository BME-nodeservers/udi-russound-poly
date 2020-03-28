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
from nodes import zone
import node_funcs

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
            self.sock = russound_main.russound_connect(self.params.get('IP Address'), self.params.get('Port'))

            self.discover()

            # TODO:
            # do we need to start a thread that listens for messages from
            # the russound and hands those off to the appropriate zone?
            if self.sock != None:
                russound_main.russound_loop(self.processCommand, self.sock)

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

    def processCommand(self, message):
        LOGGER.debug('Got message from Russound')

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

