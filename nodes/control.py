#!/usr/bin/env python3
"""
Polyglot v3 node server Russound status and control via RNET protocol
Copyright (C) 2020,2021,2022 Robert Paauwe
"""

import udi_interface
import sys
import time
import datetime
import requests
import threading
import math
import re
from nodes import russound
from nodes import zone
from nodes import profile
import russound_main
from rnet_message import RNET_MSG_TYPE, ZONE_NAMES, SOURCE_NAMES

LOGGER = udi_interface.LOGGER
Custom = udi_interface.Custom

''' Controller class, not a node!!
  This handles initialization, parameter parsing and general node server
  control (stop, delete).  For the devices configured, it will create the
  parent nodes.
'''
class Controller(object):
    def __init__(self, polyglot):
        self.poly = polyglot
        self.configured = False
        self.controller_list = {}

        self.TypedParameters = Custom(polyglot, "customtypedparams")

        polyglot.subscribe(polyglot.CUSTOMTYPEDPARAMS, self.typeParamsHandler)
        polyglot.subscribe(polyglot.CUSTOMTYPEDDATA, self.typedDataHandler)

        self.TypedParameters.load( [
            {
                'name': 'Controller',
                'title': 'Controller',
                'desc': 'A Russound controller',
                'isList': True,
                'params': [
                    {
                        'name': 'ip_addr',
                        'title': 'IP Address',
                        'isRequired': True,
                    },
                    {
                        'name': 'port',
                        'title': 'IP Port',
                        'defaultValue': 5000,
                        'isRequired': True,
                    },
                    {
                        'name': 'nwprotocol',
                        'title': 'Network Protocol',
                        'defaultValue': 'TCP',
                        'isRequired': True,
                    },
                    {
                        'name': 'protocol',
                        'title': 'RNET or RIO',
                        'defaultValue': 'RNET',
                        'isRequired': True,
                    }
                ]
            }
        ], True)

        self.poly.ready()
        self.poly.setCustomParamsDoc()

    '''
    Called with structure defined above in init.
    '''
    def typeParamsHandler(self, params):
        LOGGER.debug('In Typed Parameter Handler -- got')
        LOGGER.debug(params)

    ''' Called when the user saves changes to the config '''
    def typedDataHandler(self, data):
        self.poly.Notices.clear()
        self.controller_list = {}

        LOGGER.debug('In Typed Data Handler -- got')
        LOGGER.debug(data)
        '''
        'Controller': [
           {
           'ip_addr': '192.168.92.38',
           'port': 5000,
           'nwprotocol': 'TCP',
           'protocol': 'RNET',
           'zones': []
           }
        ]
        '''
        cnt = 1
        for ctrlr in data['Controller']:
            LOGGER.debug('Processing controller {}'.format(ctrlr))
            valid = True
            if ctrlr['nwprotocol'] != 'TCP' and ctrlr['nwprotocol'] != 'UDP':
                self.poly.Notices['nw'] = 'Network protocol invalid, please use "TCP" or "UDP"'
                valid = False
            if ctrlr['protocol'] != 'RNET' and ctrlr['protocol'] != 'RIO':
                self.poly.Notices['rnet'] = 'Russound protocol invalid, please use "RNET" or "RIO"'
                valid = False
            if ctrlr['ip_addr'] is None:
                self.Notices['ip'] = "Please configure the IP address"
                valid = False
            if ctrlr['port'] is None or ctrlr['port'] == '0':
                self.Notices['port'] = "Please configure the port number"
                valid = False

            if valid:
                ctrlr['controller'] = cnt
                ctrlr['host'] = '{}:{}'.format(ctrlr['ip_addr'], ctrlr['port'])
                address = 'rsmain_{}'.format(ctrlr['ip_addr'].split('.')[3])

                LOGGER.debug('Provisioning controller: {} {}'.format(ctrlr['host'], ctrlr['protocol']))
                if self.poly.getNode(address) is not None:
                    # TODO: Update node info??
                    LOGGER.debug('{} needs to be updated'.format(address))
                    node = self.poly.getNode(address)
                    node.provision(ctrlr)
                else:
                    ''' Create node for this controller '''
                    node = russound.RSController(self.poly, address, address, 'RussoundCtl_{}'.format(cnt), ctrlr)

                ctrlr['node'] = node

                self.controller_list[address] = ctrlr
                self.configured = True
            cnt += 1

        ''' Compare controller list with node list and delete any orphans '''
        for node in self.poly.nodes():
            if node.address not in self.controller_list:
                LOGGER.debug('Found orphaned controller {}'.format(node.address))

    def start(self):
        LOGGER.info('Starting node server @ {}'.format(datetime.date.today()))

        self.poly.updateProfile()
        LOGGER.info('Node server started')

    # Delete the node server from Polyglot
    def delete(self):
        LOGGER.info('Removing node server')

    def stop(self):
        LOGGER.info('Stopping node server')

