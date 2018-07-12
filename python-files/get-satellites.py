#!/usr/bin/env python3

"""
Utility to get the station information from a SatNOGS Network server.

Collects the paginated objects into a single JSON list and stores in a file.

Script exits with 0 if there were new TLEs to update.
"""

import sys
from datetime import datetime, timedelta
import json
import sqlite3
from itertools import islice
from io import StringIO

from lxml import html
import requests
import requests_cache

from satbazaar.db import TLESource

requests_cache.install_cache('.get-satellites-cache.db', expire_after=60*60)


DO_PRINT = True


URL = 'https://db.satnogs.org/api/satellites'
SATELLITES_JSON = 'satellites.json'
TLE_DB = 'tle.sqlite'


tle_source = TLESource()


# fetch satellites known to the network
r = requests.get(URL)
satlist = r.json()

# satellites[:] = sorted(satellites, key=lambda s: s['norad_cat_id'])
satellites = {s['norad_cat_id']:s for s in satlist}
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
for norad, sat in satellites.items():
    # don't bother getting TLE for a re-entered satellite
    if sat['status'] == 're-entered':
        if DO_PRINT:
            print(norad, 'has re-entered')
        continue

    # TLESource lazily fetches TLEs only when requested.
    # using catching the KeyError is faster than (norad in tle_source)
    #
    # vvv ensure we don't use a tle from the previous loop
    tle = None
    try:
        tle = tle_source[norad]
    except KeyError:
        if DO_PRINT:
            print('{} no TLE'.format(norad))
        continue
    else:
        if DO_PRINT:
            print('{} from {}'.format(norad, tle.source))

    try:
        cur.execute(
          'INSERT INTO tle VALUES (?,?,?,?,?,?);',
          (norad,
           tle.epoch,
           tle.line0,
           tle.line1,
           tle.line2,
           datetime.utcnow()))
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
