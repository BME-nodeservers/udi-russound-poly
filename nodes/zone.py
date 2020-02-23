# Node definition for a Russound zone

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
    drivers = [
            {'driver': 'ST', 'value': 0, 'uom': 2},        # zone power
            ]


