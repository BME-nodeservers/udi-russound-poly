#!/usr/bin/env python3
"""
Polyglot v3 node server for Russound control/status via RNET
Copyright (C) 2020,2021 Robert Paauwe
"""
import sys
import time
import udi_interface
from nodes import russound
from nodes import zone

LOGGER = udi_interface.LOGGER

if __name__ == "__main__":
    try:
        polyglot = udi_interface.Interface([russound.Controller, zone.Zone])
        polyglot.start()
        russound.Controller(polyglot, "controller", "controller", "Russound")
        polyglot.runForever()
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)
        

