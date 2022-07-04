#!/usr/bin/env python3

"""
Utility to get observations from a SatNOGS Network server and store in a local
SQLite3 database.
"""

import gzip
import json
import requests
import sqlite3
import sys

from pprint import pprint

def print(*args):
    pprint(*args)
    sys.stdout.flush()
# print = pprint.pprint

# just for developing script
# import requests_cache
# requests_cache.install_cache(expire_after=60*60)

OBSERVATIONS_API = 'https://network.satnogs.org/api/observations'
#OBSERVATIONS_JSON = 'observations.json.gz'
# OBSERVATIONS_JSON = 'observations.json'
OBSERVATIONS_DB= 'observations.db'
# OBSERVATIONS_API = 'https://network-dev.satnogs.org/api/observations'
# OBSERVATIONS_JSON = 'observations-dev.json.gz'

MAX_EXTRA_PAGES = 50
# MAX_EXTRA_PAGES = 20
# MAX_EXTRA_PAGES = 5

# RETRY_UNKNOWN_VETTED_OBS = True
RETRY_UNKNOWN_VETTED_OBS = False



client = requests.session()
def get(url):
    print(url)
    return client.get(url) #, verify=False)


try:
    pass
except FileNotFoundError:
    # this creates a new file
    observations = {}

class ObservationsDB(dict):
    def __init__(self, db=OBSERVATIONS_DB):
        self.db_conn = sqlite3.connect('file:' + OBSERVATIONS_DB, uri=True,
                            detect_types=sqlite3.PARSE_DECLTYPES)

        self.db_conn.row_factory = sqlite3.Row
        self.db_cur = self.db_conn.cursor()
        self.db_cur.execute('''CREATE TABLE IF NOT EXISTS observations
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

        self.db_conn.commit()

        # Extract the columns back out so we can construct an INSERT statement
        # with placeholders
        info = self.db_cur.execute('pragma table_info(observations);')
        # (1, 'start', 'TEXT', 0, None, 0)
        # n, name, type, maybe_null, default, primary
        self.keys = [k[1] for k in info]

        columns = ', '.join(self.keys)
        placeholders = ':' + ', :'.join(self.keys)
        self.insert_query = 'INSERT OR REPLACE INTO observations (%s) VALUES (%s)' % (columns, placeholders)
        self.get_query = 'SELECT * from observations;'

    def __setitem__(self, obs_id, obs_dict):
        # ensure keys exist for all DB columns
        d = {k:None for k in self.keys}

        # d.update(obs_dict) but detect extra keys
        for k,v in obs_dict.items():
            if k in self.keys:
                d[k] = obs_dict[k]
            else:
                raise KeyError(f'Unknown or new column: {k}:{v}')

        columns = ', '.join(obs_dict.keys())
        placeholders = ':' + ', :'.join(obs_dict.keys())
        insert_query = 'INSERT OR REPLACE INTO observations (%s) VALUES (%s)' % (columns, placeholders)
        self.db_cur.execute(insert_query, obs_dict)
        self.db_conn.commit()

    def __getitem__(self, key):
        self.db_conn.row_factory = sqlite3.Row
        query = f'SELECT * from observations WHERE id = {key};'
        result = self.db_cur.execute(query)
        # print(result.fetchone())
        item = result.fetchone()
        if item is None:
            return item
        else:
            d = {k:item[k] for k in item.keys()}
        return d

    def commit(self):
        self.db_conn.commit()

    def close(self):
        self.db_conn.close()


observations = ObservationsDB()

def update(obs, observations):
    # Is either an empty list or a list of objects
    obs['demoddata'] = str(obs['demoddata'])

    # handle missing entries
    # d = {k:None for k in observations.keys}
    # d.update(obs)

    # Translate True/False to db-compatible 1/0 integers
    for k,v in obs.items():
        if isinstance(v, bool):
            if v:
                obs[k] = 1
            else:
                obs[k] = 0

    o_id = int(obs['id'])
    was_updated = False

    db_obs = observations[o_id]
    if db_obs is None:
        print('%i new' % o_id)
        observations[o_id] = obs
        was_updated = True

    elif obs.get('detail'):
        print('%i was deleted' % o_id)
        del obs[o_id]

    elif obs != observations[o_id]:
        # get symmetric difference
        # ignore user-updated keys: 'station_*'
        #
        # converting to a 'k: v' string is a hack around ignorance...
        orig = tuple(['%s: %s' % (k,v) for k,v in observations[o_id].items() if not (k.startswith('station') or k == 'tle')])
        new = tuple(['%s: %s' % (k,v) for k,v in obs.items() if not k.startswith('station')])
        orig = set(orig)
        new = set(new)
        diff = orig ^ new

        if len(diff) > 0:
            print('%i different data' % o_id)
            print(diff)
            observations[o_id] = obs
            was_updated = True

    return was_updated


r = get(OBSERVATIONS_API)
updated = [update(o, observations) for o in r.json()]
any_updated = any(updated)

nextpage = r.links.get('next')
extra_pages = MAX_EXTRA_PAGES

try:  # allow KeyboardInterrupt to stop the update but save data
    while (extra_pages > 0) and nextpage:
        r = get(nextpage['url'])
        # network-dev returns a 500 server error at some point 350+ pages in
        # try:
        updated = [update(o, observations) for o in r.json()]
        # except Exception as e:
            # print('Error on response:', r)
            # print(e)
            # raise e

        nextpage = r.links.get('next')

        # heuristic to capture recent updates to observations
        # keep fetching pages of observations until we see
        # MAX_EXTRA_PAGES in a row with no updates
        if not any(updated):
            extra_pages -= 1
        else:
            extra_pages = MAX_EXTRA_PAGES
        print(extra_pages)

except KeyboardInterrupt as e: #anything...    KeyboardInterrupt:
    print(e)
    print('Stopping...')


## filter out the bad data
#print('**************************')
#print('* Filtering out bad data')
#print('**************************')
#badkeys = [k for k,v in observations.items() if not isinstance(v, dict)]
#for k in badkeys:
#    del observations[k]



print('')
if RETRY_UNKNOWN_VETTED_OBS:
    print('******************************')
    print('* FIXME: TODO: db version    *')
    print('* Getting unknown vetted obs *')
    print('******************************')
    try:  # allow KeyboardInterrupt to stop the update but save data
        # try to fetch old obs with no vetting
        for o_id, o in sorted(observations.items(), reverse=True)[1000:]:
            if o['vetted_status'] == 'unknown':
                r = get(OBSERVATIONS_API + '/' + str(o_id))
                d = r.json()
                if d.get('detail'):
                    print('%i was deleted' % o_id)
                    del observations[o_id]
                else:
                    update(d, observations)
    except KeyboardInterrupt: #anything...    KeyboardInterrupt:
        e = sys.exc_info()
        print(e)
        print('Stopping...')
else:
    print('***********************************')
    print('* NOT UPDATING unknown vetted obs *')
    print('***********************************')

print('Finished getting new/updated obs.')
observations.commit()
observations.close()

# print('Saving ' + OBSERVATIONS_JSON)
# if OBSERVATIONS_JSON.endswith('.gz'):
    # with gzip.open(OBSERVATIONS_JSON, 'wt') as fp:
        # json.dump(observations, fp, sort_keys=True, indent=2)
# else:
    # with open(OBSERVATIONS_JSON, 'w') as fp:
        # json.dump(observations, fp, sort_keys=True, indent=2)

print('Done!')

