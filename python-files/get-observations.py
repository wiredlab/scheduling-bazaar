#!/usr/bin/env python3

"""
Utility to get observations from a SatNOGS Network server and store in a local
SQLite3 database.
"""

import argparse
from pprint import pprint
import gzip
from itertools import islice
import json
import os.path
import sqlite3
import sys

import requests



parser = argparse.ArgumentParser()
parser.add_argument('db', metavar='observations.db',
                    help='Database of observations')
parser.add_argument('--create', action='store_true', default=False,
                    help="Create the DB if it doesn't exist")
parser.add_argument('--fetch', action=argparse.BooleanOptionalAction,
                    dest='fetch_new', default=True,
                    help='Fetch new observations')
parser.add_argument('--pages', nargs=1, dest='MAX_EXTRA_PAGES',
                    type=int, default=[50],
                    help='Extra pages to fetch (default: %(default)s)')
parser.add_argument('--retry-unknown',
                    action='store_true',
                    dest='retry_unknown', default=False,
                    help='Retry fetching obs. with "unknown" status')
parser.add_argument('--retry-observer',
                    action='store_true',
                    dest='retry_observer_null', default=False,
                    help='Retry fetching obs. with null "observer" field')
parser.add_argument('--reverse',
                    action='store_true', default=False,
                    help='Retry obs by descending ID')
parser.add_argument('--idstart', action='store', type=int,
                    help='First obs ID to inspect when retrying')
parser.add_argument('--idend', action='store', type=int,
                    help='Last obs ID to inspect when retrying')
parser.add_argument('--start', action='store', type=str,
                    help='Obs beginning after this datetime (RFC3339)')
parser.add_argument('--end', action='store', type=str,
                    help='Obs ending before this datetime (RFC3339)')


# just for developing script
# import requests_cache
# requests_cache.install_cache(expire_after=60*60)

OBSERVATIONS_API = 'https://network.satnogs.org/api/observations'



def print(*args):
    pprint(*args)
    sys.stdout.flush()
# print = pprint.pprint


client = requests.session()
def get(url, params=None):
    result = client.get(url, params=params) #, verify=False)
    print(result.url)
    return result



class ObservationsDB(dict):
    def __init__(self, db):
        self.db_conn = sqlite3.connect(f'file:{db}', uri=True,
                            detect_types=sqlite3.PARSE_DECLTYPES)

        self.db_conn.row_factory = sqlite3.Row
        self.db_conn.execute('''CREATE TABLE IF NOT EXISTS observations
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
            center_frequency INTEGER,
            observer INTEGER);''')

        self.db_conn.commit()

        with self.db_conn:
            # Extract the columns back out so we can construct an INSERT
            # statement with placeholders
            info = self.db_conn.execute('PRAGMA table_info(observations);')
            # (1, 'start', 'TEXT', 0, None, 0)
            # n, name, type, maybe_null, default, primary
            self.keys = [k[1] for k in info]

            # Allow reads when there is a writer
            result = self.db_conn.execute('PRAGMA journal_mode=WAL;')
            assert(result.fetchone()[0] == 'wal')

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

        with self.db_conn:
            self.db_conn.execute(insert_query, obs_dict)

    def __getitem__(self, key):
        self.db_conn.row_factory = sqlite3.Row
        query = f'SELECT * FROM observations WHERE id = {key};'

        with self.db_conn:
            result = self.db_conn.execute(query)
            item = result.fetchone()
            if item is None:
                return item
            else:
                d = {k:item[k] for k in item.keys()}

        return d

    def __delitem__(self, key):
        query = f'DELETE FROM observations where id = {key};'
        with self.db_conn:
            result = self.db_conn.execute(query)

    def find(self, query):
        """Execute the query and return a list of id's that match."""
        q = f'SELECT id FROM observations WHERE {query};'

        with self.db_conn:
            result = self.db_conn.execute(q)
            # save the results to a list so we can close the cursor
            ids = [x['id'] for x in result]

        return ids

    def get_unknown(self, reverse, idstart=None, idend=None):
        query = 'status = "unknown"'
        if reverse:
            order = 'DESC'
            if idstart:
                query += f' AND id <= {idstart}'
            if idend:
                query += f' AND id >= {idend}'
        else:
            order = 'ASC'
            if idstart:
                query += f' AND id >= {idstart}'
            if idend:
                query += f' AND id <= {idend}'

        query += f' ORDER BY id {order}'
        print(query)
        ids = self.find(query)
        print(f'found: {len(ids)}')
        return ids

    def get_observer_null(self, reverse, idstart=None, idend=None):
        query = 'observer is NULL'
        if reverse:
            order = 'DESC'
            if idstart:
                query += f' AND id <= {idstart}'
            if idend:
                query += f' AND id >= {idend}'
        else:
            order = 'ASC'
            if idstart:
                query += f' AND id >= {idstart}'
            if idend:
                query += f' AND id <= {idend}'

        query += f' ORDER BY id {order}'
        print(query)
        ids = self.find(query)
        print(f'found: {len(ids)}')
        return ids

    def commit(self):
        self.db_conn.commit()

    def __del__(self):
        self.commit()
        self.db_conn.close()


def update(obs, observations):
    o_id = int(obs['id'])

    if obs.get('detail'):
        print('%i was deleted' % o_id)
        del observations[o_id]
        return True

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

    was_updated = False

    db_obs = observations[o_id]
    if db_obs is None:
        print('%i new' % o_id)
        observations[o_id] = obs
        was_updated = True

    elif obs != db_obs:
        # get symmetric difference
        # ignore user-updated keys: 'station_*'
        #
        # converting to a 'k: v' string is a hack around ignorance...
        orig = tuple(['%s: %s' % (k,v) for k,v in db_obs.items() if not (k.startswith('station') or k == 'tle')])
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


def fetch_new(observations, MAX_EXTRA_PAGES, params=None):
    r = get(OBSERVATIONS_API, params)
    updated = [update(o, observations) for o in r.json()]
    any_updated = any(updated)

    nextpage = r.links.get('next')
    extra_pages = MAX_EXTRA_PAGES

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



## filter out the bad data
#print('**************************')
#print('* Filtering out bad data')
#print('**************************')
#badkeys = [k for k,v in observations.items() if not isinstance(v, dict)]
#for k in badkeys:
#    del observations[k]


def iter_chunks(iterable, size):
    """Iterate over the input in groups of size length."""
    it = iter(iterable)
    while True:
        chunk = tuple(islice(it, size))
        if not chunk:
            break
        yield chunk


def retry_unknown(observations, reverse=False, idstart=None, idend=None):
    print('')
    print('******************************')
    print('* Getting unknown vetted obs *')
    print('******************************')
    # try to fetch old obs with no vetting
    # NOTE: server will silently drop IDs if query is too long
    CHUNK_SIZE = 25
    for ids in iter_chunks(observations.get_unknown(reverse, idstart, idend), CHUNK_SIZE):
        url = OBSERVATIONS_API + '/?observation_id=' + ','.join(map(str, ids))
        r = get(url)
        items = r.json()

        # items list may be shorter than ids list,
        # this happens when observations are deleted from Network
        items_dict = {o['id']:o for o in items}
        items_set = set(items_dict.keys())
        ids_set = set(ids)
        deleted_ids = ids_set - items_set
        for i in deleted_ids:
            # emulate result as for single obs id request
            items_dict[i] = {'id':i, 'detail':'Not found.'}

        for o in items_dict.values():
            update(o, observations)

        print('requested/got: %d/%d' % (len(items), len(ids)))


def retry_observer_null(observations, reverse=False, idstart=None, idend=None):
    print('')
    print('******************************')
    print('* Getting observer field     *')
    print('******************************')

    # NOTE: server will silently drop IDs if query is too long
    CHUNK_SIZE = 25
    for ids in iter_chunks(observations.get_observer_null(reverse, idstart, idend), CHUNK_SIZE):
        url = OBSERVATIONS_API + '/?observation_id=' + ','.join(map(str, ids))
        r = get(url)
        items = r.json()

        # items list may be shorter than ids list,
        # this happens when observations are deleted from Network
        items_dict = {o['id']:o for o in items}
        items_set = set(items_dict.keys())
        ids_set = set(ids)
        deleted_ids = ids_set - items_set
        for i in deleted_ids:
            # emulate result as for single obs id request
            items_dict[i] = {'id':i, 'detail':'Not found.'}

        # updated = [update(o, observations) for o in items]
        # for o in items:
        for o in items_dict.values():
            update(o, observations)

        print('requested/got: %d/%d' % (len(items), len(ids)))

# print('Saving ' + OBSERVATIONS_JSON)
# if OBSERVATIONS_JSON.endswith('.gz'):
    # with gzip.open(OBSERVATIONS_JSON, 'wt') as fp:
        # json.dump(observations, fp, sort_keys=True, indent=2)
# else:
    # with open(OBSERVATIONS_JSON, 'w') as fp:
        # json.dump(observations, fp, sort_keys=True, indent=2)


if __name__ == '__main__':
    opts = parser.parse_args()

    parameters = {}
    if opts.start:
        parameters['start'] = opts.start

    if opts.end:
        parameters['end'] = opts.end

    if not (os.path.isfile(opts.db) or opts.create):
        raise FileNotFoundError('Database does not exist: {opts.db}')

    observations = ObservationsDB(opts.db)

    try:
        if opts.fetch_new:
            pages = opts.MAX_EXTRA_PAGES[0]

            fetch_new(observations, pages, params=parameters)

        if opts.retry_unknown:
            retry_unknown(observations,
                          reverse=opts.reverse,
                          idstart=opts.idstart,
                          idend=opts.idend)

        if opts.retry_observer_null:
            retry_observer_null(observations,
                          reverse=opts.reverse,
                          idstart=opts.idstart,
                          idend=opts.idend)

    except KeyboardInterrupt:
        print('Cancelled by user, exiting.')

    # print('Finished getting new/updated obs.')
    observations.commit()

