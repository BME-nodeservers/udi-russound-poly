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

    def __init__(self, polyglot, primary, address, name):
        super(Zone, self).__init__(polyglot, primary, address, name)
        self.address = address
        self.rnet = None
        self.ready = False
        polyglot.subscribe(polyglot.POLL, self.poll)



    def poll(self, flag):
        if self.rnet != None and self.ready:
            [blank, ctrl, zone] = self.address.split('_')
            if self.rnet.protocol == 'RNET':
                self.rnet.get_info(int(ctrl), int(zone), 0x406)
            elif self.rnet.protocol == 'RIO':
                rioZone = 'C[{}].Z[{}]'.format(ctrl, zone)
                self.rnet.get_info(ctrl, rioZone, 'status')

    def query(self):
        if self.rnet != None:
            [blank, ctrl, zone] = self.address.split('_')
            if self.rnet.protocol == 'RNET':
                self.rnet.get_info(int(ctrl), int(zone), 0x407)
            elif self.rnet.protocol == 'RIO':
                rioZone = 'C[{}].Z[{}]'.format(ctrl, zone)
                self.rnet.get_info(ctrl, rioZone, 'status')
                self.rnet.get_info(ctrl, rioZone, 'volume')
                self.rnet.get_info(ctrl, rioZone, 'currentSource')
                self.rnet.get_info(ctrl, rioZone, 'bass')
                self.rnet.get_info(ctrl, rioZone, 'treble')
                self.rnet.get_info(ctrl, rioZone, 'loundness')
                self.rnet.get_info(ctrl, rioZone, 'balance')
                self.rnet.get_info(ctrl, rioZone, 'turnOnVolume')
                self.rnet.get_info(ctrl, rioZone, 'partyMode')


    def setRNET(self, rnet):
        self.rnet = rnet

    def Ready(self):
        self.ready = True

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
        self.setDriver('GV0', source-1, True, True, 25)

    def set_volume(self, vol, force=False):
        self.setDriver('SVOL', vol, True, force, 12)

    def set_treble(self, vol, force=False):
        # display is -10 to +10
        self.setDriver('GV2', vol - 10, True, force, 56)

    def set_bass(self, vol, force=False):
        # display is -10 to +10
        self.setDriver('GV3', vol - 10, True, force, 56)

    def set_balance(self, vol, force=False):
        self.setDriver('GV4', vol - 10, True, force, 56)

    def set_loudness(self, toggle, force=False):
        self.setDriver('GV5', toggle, True, force, 25)

    def set_dnd(self, toggle, force=False):
        self.setDriver('GV6', toggle, True, force, 25)

    def set_mute(self, toggle):
        self.setDriver('GV8', toggle, True, True, 25)

    def set_page(self, toggle):
        self.setDriver('GV9', toggle, True, True, 25)

    def set_shared_source(self, toggle):
        self.setDriver('GV10', toggle, True, True, 25)

    def set_party_mode(self, toggle, force=False):
        self.setDriver('GV7', toggle, True, force, 25)

    def get_power(self):
        return self.power_state

    def process_cmd(self, cmd=None):
        # {'address': 'zone_1_2', 'cmd': 'VOLUME', 'value': '28', 'uom': '56', 'query': {}}

        LOGGER.debug('ISY sent: ' + str(cmd))
        if self.rnet.protocol == 'RNET':
            [blank, ctrl, zone] = cmd['address'].split('_')
            ctrl = int(ctrl)
            zone = int(zone) - 1
        elif self.rnet.protocol == 'RIO':
            [blank, ctrl, zone] = cmd['address'].split('_')
            zone = 'C[{}].Z[{}]'.format(ctrl, zone)
        if cmd['cmd'] == 'VOLUME':
            self.rnet.volume(ctrl, zone, int(cmd['value']))
            if self.rnet.protocol == 'RNET':
                self.set_volume(int(cmd['value']), True)
        elif cmd['cmd'] == 'BASS':
            self.rnet.set_param(ctrl, zone, 0, int(cmd['value'])+10)
            if self.rnet.protocol == 'RNET':
                self.set_bass(int(cmd['value'])+10, True)
                time.sleep(1)
                self.rnet.get_info(ctrl, zone, 0x500)
        elif cmd['cmd'] == 'TREBLE':
            self.rnet.set_param(ctrl, zone, 1, int(cmd['value'])+10)
            if self.rnet.protocol == 'RNET':
                self.set_treble(int(cmd['value'])+10, True)
                time.sleep(1)
                self.rnet.get_info(ctrl, zone, 0x501)
        elif cmd['cmd'] == 'LOUDNESS':
            self.rnet.set_param(ctrl, zone, 2, int(cmd['value']))
            if self.rnet.protocol == 'RNET':
                # The RNET controller will send an handshake acknowledge
                # but nothing else.
                # Once we send the the command, we either need to send
                # a request to get the current value (and/or) call
                # setDriver to update the status.
                self.set_loudness(int(cmd['value']), True)
                time.sleep(2)
                self.rnet.get_info(ctrl, zone, 0x502)  # Get current loudness value
        elif cmd['cmd'] == 'BALANCE':
            self.rnet.set_param(ctrl, zone, 3, int(cmd['value'])+10)
            if self.rnet.protocol == 'RNET':
                self.set_balance(int(cmd['value'])+10, True)
                time.sleep(1)
                self.rnet.get_info(ctrl, zone, 0x503)
        elif cmd['cmd'] == 'MUTE':
            self.rnet.set_param(ctrl, zone, 5, int(cmd['value']))
            if self.rnet.protocol == 'RNET':
                self.set_mute(int(cmd['value']))
                time.sleep(1)
                self.rnet.get_info(ctrl, zone, 0x505)
        elif cmd['cmd'] == 'DND':
            self.rnet.set_param(ctrl, zone, 6, int(cmd['value']))
            if self.rnet.protocol == 'RNET':
                self.set_dnd(int(cmd['value']), True)
                time.sleep(1)
                self.rnet.get_info(ctrl, zone, 0x506)
        elif cmd['cmd'] == 'PARTY':
            self.rnet.set_param(ctrl, zone, 7, int(cmd['value']))
            if self.rnet.protocol == 'RNET':
                self.set_party_mode(int(cmd['value']), True)
                time.sleep(1)
                self.rnet.get_info(ctrl, zone, 0x507)
        elif cmd['cmd'] == 'SOURCE':
            self.rnet.set_source(ctrl, zone, int(cmd['value']))
            if self.rnet.protocol == 'RNET':
                time.sleep(1)
                self.rnet.get_info(ctrl, zone, 0x402)
        elif cmd['cmd'] == 'DFON':
            self.rnet.set_state(ctrl, zone, 1)
        elif cmd['cmd'] == 'DFOF':
            self.rnet.set_state(ctrl, zone, 0)
        elif cmd['cmd'] == 'GV12':
            if self.rnet.protocol == 'RNET':
                self.rnet.send_volume_up(ctrl, zone)
                self.rnet.get_info(ctrl, zone, 0x401)
            else:
                self.rnet.set_param(ctrl, zone, 9, 1)
        elif cmd['cmd'] == 'GV13':
            if self.rnet.protocol == 'RNET':
                self.rnet.send_volume_down(ctrl, zone)
                self.rnet.get_info(ctrl, zone, 0x401)
            else:
                self.rnet.set_param(ctrl, zone, 9, 0)
        elif cmd['cmd'] == 'GV14': # source toggle
            LOGGER.error('toggle to next source, current source = ')
            self.rnet.send_event(ctrl, zone, 0x6b)
        elif cmd['cmd'] == 'GV15': # reverse
            self.rnet.send_event(ctrl, zone, 0x67)
        elif cmd['cmd'] == 'GV16': # forward
            self.rnet.send_event(ctrl, zone, 0x68)
        elif cmd['cmd'] == 'GV17': # play
            self.rnet.send_event(ctrl, zone, 0x73)
        elif cmd['cmd'] == 'GV18': # favorit 1
            self.rnet.send_event(ctrl, zone, 0x6f)
        elif cmd['cmd'] == 'GV19': # favorit 2
            self.rnet.send_event(ctrl, zone, 0x70)
        elif cmd['cmd'] == 'DIM':  # minus
            self.rnet.send_event(ctrl, zone, 0x6a)
        elif cmd['cmd'] == 'BRT':  # plus
            self.rnet.send_event(ctrl, zone, 0x69)
        elif cmd['cmd'] == 'GV20':  # stop
            self.rnet.send_event(ctrl, zone, 0x6d)
        elif cmd['cmd'] == 'GV21':  # pause
            self.rnet.send_event(ctrl, zone, 0x6e)



    commands = {
            'VOLUME': process_cmd,
            'SOURCE': process_cmd,
            'BASS': process_cmd,
            'TREBLE': process_cmd,
            'BALANCE': process_cmd,
            'LOUDNESS': process_cmd,
            'DND': process_cmd,
            'PARTY': process_cmd,
            'MUTE': process_cmd,
            'DFON': process_cmd,
            'DFOF': process_cmd,
            'GV12': process_cmd,
            'GV13': process_cmd,
            'GV14': process_cmd,
            'GV15': process_cmd,
            'GV16': process_cmd,
            'GV17': process_cmd,
            'GV18': process_cmd,
            'GV19': process_cmd,
            'GV20': process_cmd,
            'GV21': process_cmd,
            'DIM': process_cmd,
            'BRT': process_cmd,
            }

