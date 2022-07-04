#!/usr/bin/env python3

import sys
import sqlite3

from json_stream_parser import load_iter


DB_FILE = '../data/observations.db'
JSON_FILE = 'observations.json'

conn = sqlite3.connect('file:' + DB_FILE, uri=True,
                       detect_types=sqlite3.PARSE_DECLTYPES)

cur = conn.cursor()
cur.execute('''CREATE TABLE IF NOT EXISTS observations
    (id INTEGER PRIMARY KEY,
    start TEXT,
    end TEXT,
    ground_station INTEGER,
    transmitter TEXT,
    norad_cat_id INTEGER,
    payload TEXT,
    waterfall TEXT,
    demoddata TEXT,
    station_name TEXT,
    station_lat REAL,
    station_lng REAL,
    station_alt REAL,
    vetted_status TEXT,
    vetted_user INTEGER,
    vetted_datetime TEXT,
    archived INTEGER,
    archive_url TEXT,
    client_version TEXT,
    client_metadata TEXT,
    status TEXT,
    waterfall_status TEXT,
    waterfall_status_user INTEGER,
    waterfall_status_datetime TEXT,
    rise_azimuth REAL,
    set_azimuth REAL,
    max_altitude REAL,
    transmitter_uuid TEXT,
    transmitter_description TEXT,
    transmitter_type TEXT,
    transmitter_uplink_low INTEGER,
    transmitter_uplink_high INTEGER,
    transmitter_uplink_drift INTEGER,
    transmitter_downlink_low INTEGER,
    transmitter_downlink_high INTEGER,
    transmitter_downlink_drift INTEGER,
    transmitter_mode TEXT,
    transmitter_invert INTEGER,
    transmitter_baud REAL,
    transmitter_updated TEXT,
    tle0 TEXT,
    tle1 TEXT,
    tle2 TEXT,
    tle TEXT);''')

conn.commit()


# Extract the columns back out so we can construct an INSERT statement
# with placeholders
info = cur.execute('pragma table_info(observations);')
# (1, 'start', 'TEXT', 0, None, 0)
# n, name, type, maybe_null, default, primary
keys = [k[1] for k in info]

columns = ', '.join(keys)
placeholders = ':' + ', :'.join(keys)
insert_query = 'INSERT OR REPLACE INTO observations (%s) VALUES (%s)' % (columns, placeholders)



sys.exit()





with open(JSON_FILE) as f:
	f.readline()
	count = 0
	for obs in load_iter(f):
		if isinstance(obs, str):
			# consume the ": "
			f.read(2)
			continue

		# Is either an empty list or a list of objects
		obs['demoddata'] = str(obs['demoddata'])

		# handle missing entries
		d = {k:None for k in keys}
		d.update(obs)

		cur.execute(insert_query, d)

		count += 1
		if (count % 1000) == 0:
			print(d['id'])
			conn.commit()

		#consume the trailing ","
		f.read(1)

	# save!
	conn.commit()

conn.close()

