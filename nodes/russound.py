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

class RSController(udi_interface.Node):
    id = 'russound'

    def __init__(self, polyglot, primary, address, name, details):
        super(RSController, self).__init__(polyglot, primary, address, name)
        self.name = name
        self.address = address
        self.primary = primary
        self.configured = False
        self.wait = True
        self.rnet = None
        self.sock = None
        self.mesg_thread = None
        self.raw_config = bytearray(0)
        self.source_status = 0x00 # assume all sources are inactive
        self.ctrl_config = {
                'sourceInfo': {
                    'source_count': 0,
                    'sources': []
                    },
                'ctrlInfo': [
                    {
                        'controller': 0,
                        'zone_count': 0,
                        'zones': []
                        }
                    ]
                }

        # what does details look like:
        #    details['nwprotocol']
        #    details['ip_addr']
        #    details['port']
        #    details['host']
        #    details['protocol']
        #    details['zones']?
        self.provision(details)

        self.poly.subscribe(self.poly.START, self.start, address)

        self.poly.addNode(self)


    def provision(self, details):
        if details['protocol'].upper() == 'RNET':
            if details['nwprotocol'].upper() == 'UDP':
                self.rnet = russound_main.RNETConnection(details['ip_addr'], details['port'], True)
            else:
                self.rnet = russound_main.RNETConnection(details['ip_addr'], details['port'], False)
        elif details['protocol'].upper() == 'RIO':
            self.rnet = russound_main.RIOConnection(details['ip_addr'], details['port'], False)

        '''
        # [{'zone': 'Master Bedroom'}, {'zone': 'Office'}, {'zone': 'Craft Room'}, {'zone': 'Living Room'}, {'zone': 'Kitchen'}, {'zone': 'Back Yard'}]
        '''

        self.rnet.controller = details['controller']
        self.configured = True

    def start(self):
        LOGGER.info('Starting Russound Controller {}'.format(self.name))

        while not self.configured:
            time.sleep(100)

        while True:
            self.reconnect()
            LOGGER.info('{} started'.format(self.name))
            while self.rnet.connected:
                sleep(30)
            LOGGER.info('{} stopped'.format(self.name))

    def reconnect(self):
        self.rnet.Connect()

        if self.rnet.connected:
            self.setDriver("ST", 1)
            # Start a thread that listens for messages from the russound.
            if self.rnet.protocol == 'RNET':
                self.mesg_thread = threading.Thread(target=self.rnet.MessageLoop, args=(self.RNETProcessCommand,))
            else:
                self.mesg_thread = threading.Thread(target=self.rnet.MessageLoop, args=(self.RIOProcessCommand,))
            self.mesg_thread.daemon = True
            self.mesg_thread.start()

            '''
            For RNET, we send a message to the controller requesting a config packet.
             - ProcessMessages, gets the config package and parses the zone info/source info
               from the packet.
             - We then call discover to create the zone nodes
             - self.source_names, contains the list of source names.  self.source_count is 
               how many sources. Use this to create NLS
             - self.zone_count is how many zones, we loop through and create zone nodes.
               ASSUMPTION that if zone count = 3 we have zones 1, 2, 3

            For RIO, we make get_info calls which resuilts in messages that we can process
            in ProcessMessages.
            - We get a message zone# = name
            - how do we know if we have them all?


            Moving forward, should we create a dict of { zone #: zone name } and pass that to
            discover?

            '''

            
            # TODO: loop through the controllers, not just controller 1?
            #  for RIO we do that in request_config and ctrl_config will have that info (how is TBD)
            #  for RNET we have to call request_config with the controller numbers and see what happens?
            #   can we make use of the queue here?
            if self.rnet.protocol == 'RNET':
                for ctrl in range(1, 6):
                    # Get zone/source configuration for controller 1
                    self.rnet.request_config(ctrl) 
                    controller = self.rnet.getResponse()
                    LOGGER.info('Query for controller {} response = {}'.format(ctrl, controller))
                    if controller == -1:
                        break

            elif self.rnet.protocol == 'RIO':
                # Get zone/source configuration for controller 1
                # We're using a queue to get responses so when request_config finishes, we know 
                # we have all the data.
                LOGGER.debug('Attempting to get zone and source names')
                self.rnet.request_config(self.rnet.controller) 

            # RIO should have self.ctrl_config set
            LOGGER.debug('ctrl_config = {}'.format(self.ctrl_config))

            # We now know the number of zones and sources, configure the nodes.
            self.discover()

            # Query each zone
            LOGGER.debug('Attempting to get zone details')
            for cinfo in self.ctrl_config['ctrlInfo']:
                for z in range(0, cinfo['zone_count']):
                    LOGGER.debug('Request zone {} details.'.format(z))
                    if self.rnet.protocol == 'RNET':
                        self.rnet.get_info(cinfo['controller'], z, 0x0407)
                    elif self.rnet.protocol == 'RIO':
                        self.rnet.get_info(1, 'C['+str(cinfo['controller'])+'].Z['+str(z+1)+']', 'all')
                    time.sleep(2)

        if not self.rnet.connected:
            self.setDriver("ST", 0)
            # Connection has failed.

    def query(self):
        self.reportDrivers()

    def discover(self, *args, **kwargs):
        LOGGER.debug('in discover() - Setting up {} sources'.format(self.ctrl_config['sourceInfo']['source_count']))
        """
          TODO:
              Update the NLS file with the source names.  The NLS entries
              are  'SOURCE-[num] = self.sources[num]'

              Update the editor file with the proper range for the sources
              The editor id is "source"
        """
        profile.nls("SOURCE", self.ctrl_config['sourceInfo']['sources'])
        profile.editor('source', min=0, max=self.ctrl_config['sourceInfo']['source_count'] - 1, uom=25, nls="SOURCE")
        self.poly.updateProfile()

        for cinfo in self.ctrl_config['ctrlInfo']:

            LOGGER.debug('in discover() - Setting up controller {} {} zones'.format(cinfo['controller'], cinfo))
            ctrl = cinfo['controller']
            for z in range(0, cinfo['zone_count']):
                param = 'Zone ' + str(z + 1)
                zaddr = 'zone_' + str(ctrl) + '_' + str(z + 1)
                LOGGER.debug('CREATING ZONE:  {} {} - {}'.format(self.name, self.address, zaddr))
                node = zone.Zone(self.poly, self.address, zaddr, cinfo['zones'][z])
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
                        if old.name != cinfo['zones'][z]:
                            LOGGER.debug('Need to rename {} to {}'.format(old.name, cinfo['zones'][z]))
                            self.delNode(zaddr)
                            time.sleep(1)  # give it time to remove from database
                except:
                    LOGGER.warning('Failed to delete node {}'.format(zaddr))

                self.poly.addNode(node, rename=True)

    # Delete the node server from Polyglot
    def delete(self):
        LOGGER.info('Removing node server')

    def stop(self):
        LOGGER.info('Stopping node server')

    def update_profile(self, command):
        st = self.poly.installprofile()
        return st

    def set_source_selection(self, state, source):
        source_map = ['GV1', 'GV2', 'GV3', 'GV4', 'GV5', 'GV6', 'GV7', 'GV8']

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
        self.ctrl_config['sourceInfo']['sources'] = ['Inactive']

        LOGGER.debug('Number of sources = {}'.format(cfgdata[0]))
        sources = cfgdata[0]
        LOGGER.debug('Number of zones = {}'.format(cfgdata[1]))
        zones = cfgdata[1]

        ctrl = 1 #  FIXME: Need to see if this info is in cfgdata!!!

        self.ctrl_config['sourceInfo']['source_count'] = sources
        self.ctrl_config['ctrlInfo'].append({'controller': ctrl, 'zone_count': zones, 'zones': []})


        for c in range(0, 10):
            st = 0x2728 + c * 20
            # FIXME: any characters after a \x00 should be ignored
            custom_names.append(cfgdata[st:st+13].decode('utf-8').replace('\x00', ''))
            LOGGER.debug('custom name {} = {}'.format(c, custom_names[c]))

        for s in range(0, sources):
            idx = int(cfgdata[2 + s * 24])
            if idx >= 73 and idx <= 82:
                # custom name, replace
                self.ctrl_config['sourceInfo']['sources'].append(custom_names[idx - 73])
            else:
                self.ctrl_config['sourceInfo']['sources'].append(SOURCE_NAMES[idx])
            LOGGER.debug('source {} = {} ({})'.format(s, self.ctrl_config['sourceInfo']['sources'][s], idx))

        for cinfo in self.ctrl_config['ctrlInfo']:
            LOGGER.debug('zones in {}'.format(cinfo))
            if cinfo['controller'] == ctrl:
                for z in range(0, zones):
                    idx = int(cfgdata[0x92 + z * 562])
                    if idx >= 52 and idx <= 61:
                        # custom name, replace
                        cinfo['zones'].append(custom_names[idx - 52])
                    else:
                        cinfo['zones'].append(ZONE_NAMES[idx])
                    LOGGER.debug('zone {} = {} ({})'.format(z, cinfo['zones'][z], idx))

        LOGGER.debug('Did packet processing take more than 5 seconds?')
        self.rnet.IncomingQueue('CTRL: {}'.format(ctrl))


    # This is specific to RNET messages.  
    def RNETProcessCommand(self, msg):
        zone = msg.TargetZone() + 1
        ctrl = msg.TargetController() + 1
        zone_addr = 'zone_' + str(ctrl) + '_' + str(zone)

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
            LOGGER.debug(' -> Zone %d state = 0x%x' % (msg.TargetZone(), int(msg.MessageData())))
            #zone_addr = 'zone_' + str(msg.TargetZone() + 1)
            self.poly.getNode(zone_addr).set_power(int(msg.MessageData()))
        elif msg.MessageType() == RNET_MSG_TYPE.ZONE_SOURCE:
            LOGGER.debug(' -> Zone %d source = 0x%x' % (zone, int(msg.MessageData())))
            self.poly.getNode(zone_addr).set_source(int(msg.MessageData()))
        elif msg.MessageType() == RNET_MSG_TYPE.ZONE_VOLUME:
            # See what we get here.  Then try to update the actual node
            # for the zone
            LOGGER.debug(' -> Zone %d volume = 0x%x' % (zone, msg.MessageData()))
            self.poly.getNode(zone_addr).set_volume(int(msg.MessageData()))
        elif msg.MessageType() == RNET_MSG_TYPE.ZONE_BASS:
            LOGGER.debug(' -> Zone %d bass = 0x%x' % (zone, msg.MessageData()))
            self.poly.getNode(zone_addr).set_bass(int(msg.MessageData()))
        elif msg.MessageType() == RNET_MSG_TYPE.ZONE_TREBLE:
            LOGGER.debug(' -> Zone %d treble = 0x%x' % (zone, msg.MessageData()))
            self.poly.getNode(zone_addr).set_treble(int(msg.MessageData()))
        elif msg.MessageType() == RNET_MSG_TYPE.ZONE_BALANCE:
            LOGGER.debug(' -> Zone %d balance = 0x%x' % (zone, msg.MessageData()))
            self.poly.getNode(zone_addr).set_balance(int(msg.MessageData()))
        elif msg.MessageType() == RNET_MSG_TYPE.ZONE_LOUDNESS:
            LOGGER.debug(' -> Zone %d loudness = 0x%x' % (zone, msg.MessageData()))
            self.poly.getNode(zone_addr).set_loudness(int(msg.MessageData()))
        elif msg.MessageType() == RNET_MSG_TYPE.ZONE_PARTY_MODE:
            LOGGER.debug(' -> Zone %d party mode = 0x%x' % (zone, msg.MessageData()))
            self.poly.getNode(zone_addr).set_party_mode(int(msg.MessageData()))
        elif msg.MessageType() == RNET_MSG_TYPE.ZONE_DO_NOT_DISTURB:
            LOGGER.debug(' -> Zone %d do not disturb = 0x%x' % (zone, msg.MessageData()))
            self.poly.getNode(zone_addr).set_dnd(int(msg.MessageData()))
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

            self.poly.getNode(zone_addr).set_power(int(msg.MessageData()[0]))
            self.poly.getNode(zone_addr).set_source(int(msg.MessageData()[1]))
            self.poly.getNode(zone_addr).set_volume(int(msg.MessageData()[2]))
            self.poly.getNode(zone_addr).set_bass(int(msg.MessageData()[3]))
            self.poly.getNode(zone_addr).set_treble(int(msg.MessageData()[4]))
            self.poly.getNode(zone_addr).set_loudness(int(msg.MessageData()[5]))
            self.poly.getNode(zone_addr).set_balance(int(msg.MessageData()[6]))
            self.poly.getNode(zone_addr).set_party_mode(int(msg.MessageData()[7]))
            self.poly.getNode(zone_addr).set_dnd(int(msg.MessageData()[8]))

            #self.set_source_selection(msg.MessageData()[0], msg.MessageData()[1])

        elif msg.MessageType() == RNET_MSG_TYPE.KEYPAD_POWER:
            # The power key is special. We'd like it to send either DON or DOF
            # depending on what state we'll be moving into
            zone_addr = 'zone_' + str(msg.SourceZone() + 1)
            if self.poly.getNode(zone_addr).get_power():
                self.poly.getNode(zone_addr).keypress('DOF')
            else:
                self.poly.getNode(zone_addr).keypress('DON')
        elif msg.MessageType() == RNET_MSG_TYPE.KEYPAD_FAV1:
            zone_addr = 'zone_' + str(msg.SourceZone() + 1)
            self.poly.getNode(zone_addr).keypress('GV18')
        elif msg.MessageType() == RNET_MSG_TYPE.KEYPAD_FAV2:
            zone_addr = 'zone_' + str(msg.SourceZone() + 1)
            self.poly.getNode(zone_addr).keypress('GV19')
        elif msg.MessageType() == RNET_MSG_TYPE.KEYPAD_PLUS:
            zone_addr = 'zone_' + str(msg.SourceZone() + 1)
            self.poly.getNode(zone_addr).keypress('BRT')
        elif msg.MessageType() == RNET_MSG_TYPE.KEYPAD_MINUS:
            zone_addr = 'zone_' + str(msg.SourceZone() + 1)
            self.poly.getNode(zone_addr).keypress('DIM')
        elif msg.MessageType() == RNET_MSG_TYPE.KEYPAD_NEXT:
            zone_addr = 'zone_' + str(msg.SourceZone() + 1)
            self.poly.getNode(zone_addr).keypress('GV16')
        elif msg.MessageType() == RNET_MSG_TYPE.KEYPAD_PREVIOUS:
            zone_addr = 'zone_' + str(msg.SourceZone() + 1)
            self.poly.getNode(zone_addr).keypress('GV15')
        elif msg.MessageType() == RNET_MSG_TYPE.KEYPAD_SOURCE:
            zone_addr = 'zone_' + str(msg.SourceZone() + 1)
            self.poly.getNode(zone_addr).keypress('GV14')
        elif msg.MessageType() == RNET_MSG_TYPE.KEYPAD_PLAY:
            zone_addr = 'zone_' + str(msg.SourceZone() + 1)
            self.poly.getNode(zone_addr).keypress('GV17')
        elif msg.MessageType() == RNET_MSG_TYPE.KEYPAD_VOL_UP:
            zone_addr = 'zone_' + str(msg.SourceZone() + 1)
            self.poly.getNode(zone_addr).keypress('GV12')
        elif msg.MessageType() == RNET_MSG_TYPE.KEYPAD_VOL_DOWN:
            zone_addr = 'zone_' + str(msg.SourceZone() + 1)
            self.poly.getNode(zone_addr).keypress('GV13')
        elif msg.MessageType() == RNET_MSG_TYPE.KEYPAD_NEXT:
            LOGGER.debug(' -> Keypad next')
        elif msg.MessageType() == RNET_MSG_TYPE.UNKNOWN_SET:
            # don't think we really care about these
            LOGGER.debug('US -> ' + ' '.join('{:02x}'.format(x) for x in msg.MessageRaw()))
        else:
            LOGGER.debug(' -> TODO: message id ' + str(msg.MessageType().name) + ' not yet implemented.')

    def RIOProcessCommand(self, msg):
        # S successful response
        # E error response
        # N notification

        # GET <key>  results in message S<key>=value
        #    <key>  looks like C[#].<keytype>
        #    EX: S C[1].Z[1].name --> get zone 1 name  controller range 1-6, zone range 1-6?
        if msg != 'S':  #Ignore a 'S' message with optional data
            if msg[2:4] != 'S[':  # system or source message???
                LOGGER.debug('From Russound: ' + msg)
            if msg[0] == 'N' or msg[0] == 'S':
                if msg[2] == 'C' and msg[6] == '.' and msg[8] != '[': # controller info C[c].xxxx
                    curValue = msg[msg.find('=')+2:-1]   # value comes after the '=' size
                    LOGGER.debug('controller info: {}, value = {}'.format(msg, curValue))
                    self.rnet.IncomingQueue(curValue)
                if msg[2] == 'C' and msg[10] == ']' and msg[7] == 'Z':  # controller/zone C[c][z]
                    curZone = 'zone_' + msg[4] + '_' + msg[9]  # msg[4] = controller #, msg[9] = zone #
                    #curZone = 'zone_' + msg[9]  # msg[4] = controller #, msg[9] = zone FIXME: addNode not using controller yet
                    curCommand = msg[12: msg.find('=')]  # msg[12] start of command, 
                    curValue = msg[msg.find('=')+2:-1]   # value comes after the '=' size

                    self.rnet.IncomingQueue(curValue)
                    LOGGER.debug('zone = {}, command = {}, value = {}'.format(curZone, curCommand, curValue))

                    #Change ON/OFF to 1/0
                    if curValue == 'OFF' : 
                        curValue = 0
                    if curValue == 'ON' : 
                        curValue = 1

                    if curCommand == 'status' : #power status (on/off)
                        self.poly.getNode(curZone).set_power(curValue)
                    # This is where we get the name info from a zone and add the node
                    elif curCommand == 'name' and msg[0] == 'S':  # name of zone
                        if curValue == '':
                            curValue = 'Unused'
                        else:
                            #LOGGER.debug('Updating ctrl_config = {}'.format(self.ctrl_config))
                            LOGGER.debug('Found zone {} on ctrl {}'.format(curValue, msg[4]))
                            LOGGER.debug('controller info = {}'.format(self.ctrl_config['ctrlInfo']))
                            try:
                                if len(self.ctrl_config['ctrlInfo']) <= int(msg[4]):
                                    self.ctrl_config['ctrlInfo'].append({'controller': int(msg[4]), 'zones':[curValue], 'zone_count': 1})
                                else:
                                    LOGGER.debug('Look up array index for controller {}'.format(msg[4]))
                                    for cinfo in self.ctrl_config['ctrlInfo']:
                                        if cinfo['controller'] == int(msg[4]):
                                            LOGGER.debug('Found array index for {}: {}'.format(msg[4], cinfo))
                                            cinfo['zones'].append(curValue)
                                            cinfo['zone_count'] += 1
                            except Exception as e:
                                LOGGER.error('Error: Unable to add zone {} to controller config:: {}'.format(curValue, e))

                    elif curCommand == 'volume' :  # zone volume (0 - 50)
                        self.poly.getNode(curZone).set_volume(int(curValue))
                    elif curCommand == 'turnOnVolume' : # turn on volume (0 to 50)
                        LOGGER.debug('Turn on volume not setup yet')
                    elif curCommand == 'mute' : # mute status (on/off)
                        self.poly.getNode(curZone).set_mute(curValue)
                    elif curCommand == 'page' : # page (on/off)
                        self.poly.getNode(curZone).set_page(curValue)
                    elif curCommand == 'sharedSource' : # sharded source (on/off)
                        self.poly.getNode(curZone).set_shared_source(curValue)
                    elif curCommand == 'treble' : # treble (-10 to 10)
                        self.poly.getNode(curZone).set_treble(int(curValue)+10)
                    elif curCommand == 'bass' :  # bass (-10 to 10)
                        self.poly.getNode(curZone).set_bass(int(curValue)+10)
                    elif curCommand == 'balance' : # balance (-10 to 10)
                        self.poly.getNode(curZone).set_balance(int(curValue)+10)
                    elif curCommand == 'currentSource' : # current source (1 to max source)
                        self.poly.getNode(curZone).set_source(int(curValue)-1)
                    elif curCommand == 'loudness' : # loudness (on / off)
                        self.poly.getNode(curZone).set_loudness(curValue)
                    elif curCommand == 'partyMode' : # party mode off/on/master
                        self.poly.getNode(curZone).set_party_mode(curValue)
                    elif curCommand == 'doNotDisturb' : #do not disturb (off/on/slave)
                        self.poly.getNode(curZone).set_dnd(curValue)
                    elif curCommand == 'enabled' : # True/False
                        LOGGER.debug('zone {} is enabled? {}'.format(curZone, curValue))
                    elif curCommand == 'sleepTimeDefault' : # 15 minutes
                        LOGGER.debug('zone {} default sleep time {} minutes'.format(curZone, curValue))
                    elif curCommand == 'sleepTimeRemaining' : # 0 to 60 minutes
                        LOGGER.debug('zone {} remaining sleep time {} minutes'.format(curZone, curValue))
                    '''
                    elif curCommand == 'favorite' : # [f].valid  in use (true/false)
                    elif curCommand == 'favorite' : # [f].name  name of favorite
                    '''
                if msg[2] == 'C' and msg[6] == '.': # controller info C[c].xxxx
                    curCommand = msg[7: msg.find('=')]  # msg[12] start of command, 
                    curValue = msg[msg.find('=')+2:-1]   # value comes after the '=' size
                    if curCommand == 'type':  # type of controller
                        # might want to use this to figure out zones?  MCA-66 vs MCA-88
                        LOGGER.debug('Controller is {}'.format(curValue))

                if msg[2] == 'S':  # Source table S S[xx].name = "theName"
                    curSource = 'source_' + msg[4: msg.find(']')]  # msg[4] = source #,
                    curCommand = msg[msg.find('.')+1: msg.find('=')]  # msg[7] start of command, 
                    curValue = msg[msg.find('=')+2:-1]   # value comes after the '=' size
                    self.rnet.IncomingQueue(curValue)
                    LOGGER.debug('source = {}, command = {}, value = {}'.format(curSource, curCommand, curValue))

                    if curCommand == 'name' and msg[0] == 'S':  # name of source
                        if curValue == '':
                            curValue = 'Unused'
                        else:
                            self.ctrl_config['sourceInfo']['sources'].append(curValue)
                            self.ctrl_config['sourceInfo']['source_count'] += 1
                    elif curCommand == 'type': # type of source
                        LOGGER.debug('source {} is {}'.format(curSource, curValue))
                    '''
                    elif curCommand == 'channel':
                    elif curCommand == 'coverArtURL':
                    elif curCommand == 'channelName':
                    elif curCommand == 'genre':
                    elif curCommand == 'artistName':
                    elif curCommand == 'albumName':
                    elif curCommand == 'playlistName':
                    elif curCommand == 'songName':
                    elif curCommand == 'programServiceName':
                    elif curCommand == 'radioText':
                    elif curCommand == 'shuffleMode':
                    elif curCommand == 'repeatMode':
                    elif curCommand == 'mode':
                    elif curCommand == 'rating':
                    elif curCommand == 'playStatus':
                    elif curCommand == 'availableControls':
                    elif curCommand == 'sampleRate':
                    elif curCommand == 'bitRate':
                    elif curCommand == 'bitDepth':
                    elif curCommand == 'playTime':
                    elif curCommand == 'trackTime':
                    elif curCommand == 'playerData':
                    '''
            elif msg[0] == 'E':
                LOGGER.error('Error from Russound controller:: {}'.format(msg))
                self.rnet.IncomingQueue(msg)


    commands = {
            'DISCOVER': discover,
            }

    # For this node server, all of the info is available in the single
    # controller node.
    drivers = [
            {'driver': 'ST', 'value': 0, 'uom': 2,   'name': 'Connection Status'},    # Russound connection status
            ]
            '''
            {'driver': 'GV1', 'value': 0, 'uom': 25, 'name': 'Source 1'},  # source 1 On/off status
            {'driver': 'GV2', 'value': 0, 'uom': 25, 'name': 'Source 2'},  # source 2 On/off status
            {'driver': 'GV3', 'value': 0, 'uom': 25, 'name': 'Source 3'},  # source 3 On/off status
            {'driver': 'GV4', 'value': 0, 'uom': 25, 'name': 'Source 4'},  # source 4 On/off status
            {'driver': 'GV5', 'value': 0, 'uom': 25, 'name': 'Source 5'},  # source 5 On/off status
            {'driver': 'GV6', 'value': 0, 'uom': 25, 'name': 'Source 6'},  # source 6 On/off status
            {'driver': 'GV7', 'value': 0, 'uom': 25, 'name': 'Source 7'},  # source 7 On/off status
            {'driver': 'GV8', 'value': 0, 'uom': 25, 'name': 'Source 8'},  # source 8 On/off status
            '''

