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

requests_cache.install_cache('.get-satellites-cache.db', expire_after=60*60)


DO_PRINT = False
# DO_PRINT = True


URL = 'https://db.satnogs.org/api/satellites'
SATELLITES_JSON = 'satellites.json'
TLE_DB = 'tle.sqlite'

AMSAT = 'https://www.amsat.org/tle/current/nasabare.txt'


def get_celestrak(norad):
    r = requests.get('http://www.celestrak.com/cgi-bin/TLE.pl?CATNR={}'.format(norad))
    p = html.fromstring(r.text)
    lines = p.xpath('//pre/text()')[0].split('\n')
    if len(lines) == 5:
        return lines[1].strip(), lines[2].strip(), lines[3].strip()
    else:
        raise KeyError('{} not found'.format(norad))


def get_epoch(tle):
    y = int(tle[1][18:20])
    jd = float(tle[1][20:32])
    if y < 57:
        y += 100
    y += 1900
    d = datetime(y, 1, 1) + timedelta(days=jd)
    return d


def read_3LE(fp):
    data = {}
    lines = iter(fp)
    while lines:
        triple = islice(lines, 3)
        tle = [x.rstrip() for x in triple]
        if len(tle) == 3:
            norad = int(tle[1][2:7])
            data[norad] = tle
        else:
            break
    return data


# go ahead and fetch the AMSAT TLEs once for this session
r = requests.get(AMSAT)
amsat = read_3LE(StringIO(r.text))


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

    try:
        tle = get_celestrak(norad)
        if DO_PRINT:
            print('{} TLE from CelesTrak'.format(norad))
    except KeyError:
        # bad parse of data, typically response was "No TLE found"
        if norad in amsat:
            tle = amsat[norad]
            if DO_PRINT:
                print('{} TLE from AMSAT'.format(norad))
        else:
            if DO_PRINT:
                print('{} no TLE'.format(norad))
    else:
        line0, line1, line2 = tle
        epoch = get_epoch(tle)

    try:
        cur.execute(
          'INSERT INTO tle VALUES (?,?,?,?,?,?);',
          (norad, epoch, line0, line1, line2, datetime.utcnow()))
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
