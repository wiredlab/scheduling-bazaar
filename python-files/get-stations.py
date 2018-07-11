#!/usr/bin/env python3

"""
Utility to get the station information from a SatNOGS Network server.

Collects the paginated objects into a single JSON list and stores in a file.
"""

import sys

from satbazaar import db

fname = None
networks = None

argc = len(sys.argv)
if argc > 1:
    fname = sys.argv[1]

    if argc > 2:
        networks = sys.argv[2:]

db.get_stations(fname, networks)
