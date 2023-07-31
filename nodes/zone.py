# Node definition for a Russound zone
# 

import udi_interface
import json
import time
import datetime
import russound

LOGGER = udi_interface.LOGGER

class Zone(udi_interface.Node):
    id = 'zone'
    power_state = False
    """
    What makes up a zone? 
        Power
        Source
        Volume
        Bass
        Treble
        Party Mode
        Do Not Disturb
    """

    drivers = [
            {'driver': 'ST', 'value': 0, 'uom': 25,   'name': 'Power'},       # zone power
            {'driver': 'GV0', 'value': 0, 'uom': 25,  'name': 'Source'},      # zone source
            {'driver': 'SVOL', 'value': 0, 'uom': 12, 'name': 'Volume'},     # zone volume
            {'driver': 'GV2', 'value': 0, 'uom': 56,  'name': 'Treble'},      # zone treble
            {'driver': 'GV3', 'value': 0, 'uom': 56,  'name': 'Bass'},      # zone bass
            {'driver': 'GV4', 'value': 0, 'uom': 56,  'name': 'Balance'},      # zone balance
            {'driver': 'GV5', 'value': 0, 'uom': 25,  'name': 'Loudness'},       # loudness
            {'driver': 'GV6', 'value': 0, 'uom': 25,  'name': 'Do Not Disturb'},       # do not disturb
            {'driver': 'GV7', 'value': 0, 'uom': 25,  'name': 'Party Mode'},       # party mode
            {'driver': 'GV8', 'value': 0, 'uom': 25,  'name': 'Mute'},       # mute
            {'driver': 'GV9', 'value': 0, 'uom': 25,  'name': 'Page'},       # page
            {'driver': 'GV10', 'value': 0, 'uom': 25, 'name': 'Shared Source'},    # shared source
            ]


    def setRNET(self, rnet):
        self.rnet = rnet

    '''
    Called when the zone's keypad is used.  Send the keypress to the ISY
    '''
    def keypress(self, key):
        LOGGER.debug('Sending ' + key + ' to ISY')
        # is this something the controller class has but the node class
        # doesn't? How can a node send a command?
        self.reportCmd(key, 0)

    def set_power(self, power):
        self.setDriver('ST', power, True, True, 25)
        if power == 0:
            self.power_state = False
        else:
            self.power_state = True

    def set_source(self, source):
        self.setDriver('GV0', source + 1, True, True, 25)

    def set_volume(self, vol):
        self.setDriver('SVOL', vol, True, True, 12)

    def set_treble(self, vol):
        # display is -10 to +10
        self.setDriver('GV2', vol - 10, True, True, 56)

    def set_bass(self, vol):
        # display is -10 to +10
        self.setDriver('GV3', vol - 10, True, True, 56)

    def set_balance(self, vol):
        self.setDriver('GV4', vol - 10, True, True, 56)

    def set_loudness(self, toggle):
        self.setDriver('GV5', toggle, True, True, 25)

    def set_dnd(self, toggle):
        self.setDriver('GV6', toggle, True, True, 25)

    def set_mute(self, toggle):
        self.setDriver('GV8', toggle, True, True, 25)

    def set_page(self, toggle):
        self.setDriver('GV9', toggle, True, True, 25)

    def set_shared_source(self, toggle):
        self.setDriver('GV10', toggle, True, True, 25)

    def set_party_mode(self, toggle):
        self.setDriver('GV7', toggle, True, True, 25)

    def get_power(self):
        return self.power_state

    def process_cmd(self, cmd=None):
        # {'address': 'zone_2', 'cmd': 'VOLUME', 'value': '28', 'uom': '56', 'query': {}}

        LOGGER.debug('ISY sent: ' + str(cmd))
        if self.rnet.protocol == 'RNET':
            zones = {'zone_1':0, 'zone_2':1, 'zone_3':2, 'zone_4':3, 'zone_5':4, 'zone_6':5, 'zone_7':6, 'zone_8':7}
        elif self.rnet.protocol == 'RIO':
            zones = {'zone_1':'C[1].Z[1]',
                     'zone_2':'C[1].Z[2]',
                     'zone_3':'C[1].Z[3]',
                     'zone_4':'C[1].Z[4]',
                     'zone_5':'C[1].Z[5]',
                     'zone_6':'C[1].Z[6]',
                     'zone_7':'C[1].Z[7]',
                     'zone_8':'C[1].Z[8]'
                     }
        if cmd['cmd'] == 'VOLUME':
            self.rnet.volume(zones[cmd['address']], int(cmd['value']))
        elif cmd['cmd'] == 'BASS':
            self.rnet.set_param(zones[cmd['address']], 0, int(cmd['value'])+10)
            if self.rnet.protocol == 'RNET':
                time.sleep(1)
                self.rnet.get_info(zones[cmd['address']], 0x500)
        elif cmd['cmd'] == 'TREBLE':
            self.rnet.set_param(zones[cmd['address']], 1, int(cmd['value'])+10)
            if self.rnet.protocol == 'RNET':
                time.sleep(1)
                self.rnet.get_info(zones[cmd['address']], 0x501)
        elif cmd['cmd'] == 'LOUDNESS':
            self.rnet.set_param(zones[cmd['address']], 2, int(cmd['value']))
            if self.rnet.protocol == 'RNET':
                time.sleep(1)
                self.rnet.get_info(zones[cmd['address']], 0x502)
        elif cmd['cmd'] == 'BALANCE':
            self.rnet.set_param(zones[cmd['address']], 3, int(cmd['value'])+10)
            if self.rnet.protocol == 'RNET':
                time.sleep(1)
                self.rnet.get_info(zones[cmd['address']], 0x503)
        elif cmd['cmd'] == 'MUTE':
            self.rnet.set_param(zones[cmd['address']], 5, int(cmd['value']))
            if self.rnet.protocol == 'RNET':
                time.sleep(1)
                self.rnet.get_info(zones[cmd['address']], 0x505)
        elif cmd['cmd'] == 'DND':
            self.rnet.set_param(zones[cmd['address']], 6, int(cmd['value']))
            if self.rnet.protocol == 'RNET':
                time.sleep(1)
                self.rnet.get_info(zones[cmd['address']], 0x506)
        elif cmd['cmd'] == 'PARTY':
            self.rnet.set_param(zones[cmd['address']], 7, int(cmd['value']))
            if self.rnet.protocol == 'RNET':
                time.sleep(1)
                self.rnet.get_info(zones[cmd['address']], 0x507)
        elif cmd['cmd'] == 'SOURCE':
            self.rnet.set_source(zones[cmd['address']], int(cmd['value'])-1)
            if self.rnet.protocol == 'RNET':
                time.sleep(1)
                self.rnet.get_info(zones[cmd['address']], 0x402)
        elif cmd['cmd'] == 'DFON':
            self.rnet.set_state(zones[cmd['address']], 1)
        elif cmd['cmd'] == 'DFOF':
            self.rnet.set_state(zones[cmd['address']], 0)

    commands = {
            'VOLUME': process_cmd,
            'SOURCE': process_cmd,
            'BASS': process_cmd,
            'TREBLE': process_cmd,
            'BALANCE': process_cmd,
            'LOUDNESS': process_cmd,
            'DND': process_cmd,
            'PARTY': process_cmd,
            'DFON': process_cmd,
            'DFOF': process_cmd,
            }

