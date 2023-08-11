#!/usr/bin/env python3
"""
Polyglot v3 node server for Russound control/status via RNET
Copyright (C) 2020,2021 Robert Paauwe
"""
import sys
import time
import udi_interface
from nodes import control
from nodes import russound
from nodes import zone

LOGGER = udi_interface.LOGGER

if __name__ == "__main__":
    try:
        polyglot = udi_interface.Interface([russound.RSController, zone.Zone])
        polyglot.start('2.0.10')
        control.Controller(polyglot)
        polyglot.runForever()
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)
        

