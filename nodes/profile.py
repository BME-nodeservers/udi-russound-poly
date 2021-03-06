#!/usr/bin/env python3

"""
  Profile file manipulation functions

  Copyright (C) 2021 Robert Paauwe

  Utilitye functions to make changes to profile files.

  nls(key, array)
     - Add NLS entries using key for each item in array
     - removes any existing entries for key

  editor(id, min, max, uom, nls)
     - Replace the editor range for id with the passed in args.

"""

import collections
import os
import logging
import in_place

logger = logging.getLogger()


def nls(key, nls_list):
    # first make sure directory exists
    if not os.path.exists("profile/nls"):
        try:
            os.makedirs("profile/nls")
        except:
            logger.error('unable to create node NLS directory.')

    with in_place.InPlace('profile/nls/en_us.txt') as file:
        for line in file:
            if not line.startswith(key):
                file.write(line)
        # append new entries
        idx = 0
        for name in nls_list:
            file.write('{}-{}: {}\n'.format(key, idx, name.strip()))
            idx += 1

def editor(editor_id, min, max, uom, nls):
    found = False
    with in_place.InPlace('profile/editor/editors.xml') as file:
        for line in file:
            if found:
                found = False
                file.write('\t\t<range uom="{}" min="{}" max="{}" nls="{}" />\n'.format(uom, min, max, nls))
            else:
                file.write(line)

            if 'id="' + editor_id in line:
                found = True

            

