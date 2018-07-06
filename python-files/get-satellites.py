#!/usr/bin/env python3

"""
Utility to get the station information from a SatNOGS Network server.

Collects the paginated objects into a single JSON list and stores in a file.

Script exits with 0 if there were new TLEs to update.
"""

import sys
from datetime import datetime
import json
import sqlite3
from itertools import islice

import requests
import orbit

DO_PRINT = False

# default expire time is 24 hours
orbit.tle.requests_cache.uninstall_cache()
orbit.tle.requests_cache.install_cache(cache_name='requests-cache',
                                       expire_after=60*60)


URL = 'https://db.satnogs.org/api/satellites'
SATELLITES_JSON = 'satellites.json'
TLE_DB = 'tle.sqlite'

AMSAT = 'https://www.amsat.org/tle/current/nasabare.txt'

# go ahead and fetch the AMSAT TLEs once for this session
amsat = {}
r = requests.get(AMSAT)

lines = iter(r.text.splitlines())
while lines:
    triple = islice(lines, 3)
    tle = [x.rstrip() for x in triple]
    if len(tle) == 3:
        norad = int(tle[1][2:7])
        amsat[norad] = tle
    else:
        break


# fetch satellites known to the network
r = requests.get(URL)
satellites = r.json()

satellites[:] = sorted(satellites, key=lambda s: s['norad_cat_id'])
with open(SATELLITES_JSON, 'w') as fp:
    json.dump(satellites, fp, sort_keys=True, indent=2)


conn = sqlite3.connect('file:' + TLE_DB, uri=True,
                       detect_types=sqlite3.PARSE_DECLTYPES)
cur = conn.cursor()
cur.execute('''CREATE TABLE IF NOT EXISTS tle
            (norad integer,
             epoch timestamp,
             line0 text,
             line1 text,
             line2 text,
             downloaded timestamp,
             unique(norad, epoch)
            );''')

UPDATED = 0
for sat in satellites:
    norad = sat['norad_cat_id']
    try:
        # fetch information from CelesTrak
        body = orbit.satellite(norad)
        if DO_PRINT: print('{} TLE from CelesTrak'.format(norad))

        line0, line1, line2 = body.tle_raw

        # TODO: merge information from
        # https://www.amsat.org/tle/current/nasabare.txt
    except IndexError:
        # bad parse of data, typically response was "No TLE found"
        if norad in amsat:
            line0, line1, line2 = amsat[norad]
            if DO_PRINT: print('{} TLE from AMSAT'.format(norad))
        else:
            if DO_PRINT: print('{} no TLE'.format(norad))
    else:
        epoch = body.tle_parsed._epoch.datetime()

    try:
        cur.execute(
          'INSERT INTO tle VALUES (?,?,?,?,?,?);',
          (norad,
           epoch,
           line0,
           line1,
           line2,
           datetime.utcnow().isoformat()))
        # 'INSERT OR IGNORE INTO ...' will suppress the exception
    except sqlite3.IntegrityError:
        pass
    else:
        UPDATED += 1
    finally:
        pass

conn.commit()
conn.close()

if UPDATED:
    print(UPDATED, 'updates')
    sys.exit(0)
else:
    print('no updates')
    sys.exit(1)
