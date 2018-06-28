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

import requests
import orbit


# default expire time is 24 hours
orbit.tle.requests_cache.uninstall_cache()
orbit.tle.requests_cache.install_cache(cache_name='requests-cache',
                                       expire_after=60*60)


URL = 'https://db.satnogs.org/api/satellites'
SATELLITES_JSON = 'satellites.json'
TLE_DB = 'tle.sqlite'


# fetch known satellites
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

        # TODO: merge information from
        # https://www.amsat.org/tle/current/nasabare.txt
    except IndexError:
        # bad parse of data, typically response was "No TLE found"
        continue
    else:
        epoch = body.tle_parsed._epoch.datetime()

    try:
        cur.execute(
          'INSERT INTO tle VALUES (?,?,?,?,?,?);',
          (norad,
           epoch,
           body.tle_raw[0],
           body.tle_raw[1],
           body.tle_raw[2],
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
