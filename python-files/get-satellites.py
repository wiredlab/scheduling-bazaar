#!/usr/bin/env python3

"""
Utility to get the station information from a SatNOGS Network server.

Collects the paginated objects into a single JSON list and stores in a file.
"""

import json
import sqlite3
import requests

import orbit


# default expire time is 24 hours
orbit.tle.requests_cache.configure(expire_after=60*60*6)


URL = 'https://db.satnogs.org/api/satellites'
SATELLITES_JSON = 'satellites.json'
TLE_DB = 'tle.db'


# fetch known satellites
r = requests.get(URL)
satellites = r.json()

with open(SATELLITES_JSON, 'w') as fp:
    json.dump(satellites, fp)


conn = sqlite3.connect('file:' + TLE_DB, uri=True,
                       detect_types=sqlite3.PARSE_DECLTYPES)
cur = conn.cursor()
cur.execute('''CREATE TABLE IF NOT EXISTS tle
            (norad integer,
             epoch timestamp,
             line0 text,
             line1 text,
             line2 text,
             unique(norad, epoch)
            );''')

for sat in satellites:
    norad = sat['norad_cat_id']
    print(norad, end='')
    try:
        tle = orbit.satellite(norad)
    except KeyError:
        print(' ** not at CelesTrak')
        continue

    try:
        cur.execute(
          'INSERT INTO tle VALUES (?,?,?,?,?);',
          (norad, tle.epoch(), tle.tle_raw[0], tle.tle_raw[1], tle.tle_raw[2]))
        # 'INSERT OR IGNORE INTO ...' will suppress the exception
    except sqlite3.IntegrityError:
        pass
    else:
        print(' TLE updated', end='')
    finally:
        print()

conn.commit()
conn.close()
