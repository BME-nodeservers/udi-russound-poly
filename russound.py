#!/usr/bin/env python3
"""
Polyglot v2 node server for Russound control/status via RNET
Copyright (C) 2020 Robert Paauwe
"""
import sys
import time
try:
    import polyinterface
except ImportError:
    import pgc_interface as polyinterface
from nodes import russound
from nodes import zone

LOGGER = polyinterface.LOGGER

if __name__ == "__main__":
    try:
        polyglot = polyinterface.Interface('Russound')
        polyglot.start()
        control = russound.Controller(polyglot)
        control.runForever()
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)
        

