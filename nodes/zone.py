# Node definition for a Russound zone
# 

try:
    import polyinterface
except ImportError:
    import pgc_interface as polyinterface
import json
import time
import datetime
import russound
import node_funcs

LOGGER = polyinterface.LOGGER

@node_funcs.add_functions_as_methods(node_funcs.functions)
class Zone(polyinterface.Node):
    id = 'zone'
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
            {'driver': 'ST', 'value': 0, 'uom': 2},        # zone power
            {'driver': 'GV0', 'value': 0, 'uom': 25},      # zone source
            {'driver': 'GV1', 'value': 0, 'uom': 12},      # zone volume
            {'driver': 'GV2', 'value': 0, 'uom': 56},      # zone treble
            {'driver': 'GV3', 'value': 0, 'uom': 56},      # zone bass
            {'driver': 'GV4', 'value': 0, 'uom': 56},      # zone balance
            ]


    '''
    TODO:
        Add drivers for all things zone releated
        Add methods to handle updating each driver. These will get called from
        the main process command function.

        Add zone command
    '''

    '''
    Called when the zone's keypad is used.  Send the keypress to the ISY
    '''
    def keypress(self, key):
        LOGGER.info('Sending ' + key + ' to ISY')
        # is this something the controller class has but the node class
        # doesn't? How can a node send a command?
        self.reportCmd(key, 0)

    def set_power(self, power):
        self.setDriver('ST', power, True, True, 2)

    def set_source(self, source):
        self.setDriver('GV0', source, True, True, 56)

    def set_volume(self, vol):
        self.setDriver('GV1', vol, True, True, 12)

    def set_treble(self, vol):
        self.setDriver('GV2', vol, True, True, 56)

    def set_bass(self, vol):
        self.setDriver('GV3', vol, True, True, 56)

    def set_balance(self, vol):
        self.setDriver('GV4', vol, True, True, 56)

    def process_cmd(self, cmd=None):
        LOGGER.info('ISY sent: ' + str(cmd))

    commands = {
            'HOME': process_cmd,
            'REV': process_cmd,
            'FWD': process_cmd,
            'PLAY': process_cmd,
            'SELECT': process_cmd,
            'LEFT': process_cmd,
            'RIGHT': process_cmd,
            'DOWN': process_cmd,
            'UP': process_cmd,
            'BACK': process_cmd,
            'REPLAY': process_cmd,
            'INFO': process_cmd,
            'BACKSPACE': process_cmd,
            'SEARCH': process_cmd,
            'ENTER': process_cmd,
            }

