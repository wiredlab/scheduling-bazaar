#!/usr/bin/env python3

"""
Utility to get observations from a SatNOGS Network server and store in a local
SQLite3 database.
"""

import concurrent.futures
from datetime import datetime
from itertools import islice
import json
import os.path
from pprint import pprint
import sqlite3
import sys
import threading
import time
from urllib.parse import urlparse

import requests
import skyfield.api



# just for developing script
import requests_cache
requests_cache.install_cache(expire_after=4*60*60)
requests_cache.delete(expired=True)

OBSERVATIONS_API = 'https://network.satnogs.org/api/observations'



def print(*args):
    pprint(*args)
    sys.stdout.flush()


client = requests.session()
def get(url, params=None):
    headers = {"Authorization": f"Token {API_TOKEN}"}
    result = client.get(url, headers=headers, params=params) #, verify=False)
    print(result.url)
    return result



class ObservationsDB(dict):
    def __init__(self, db, demoddata_db=None):
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
            transmitter_status TEXT,
            tle0 TEXT,
            tle1 TEXT,
            tle2 TEXT,
            tle_source TEXT,
            center_frequency INTEGER,
            observer INTEGER,
            observation_frequency INTEGER,
            transmitter_unconfirmed INTEGER);''')

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

        if demoddata_db is not None:
            self.demoddata = DemoddataDB(demoddata_db)

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

        with self.db_conn:
            self.db_conn.execute(self.insert_query, obs_dict)

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

    def __del__(self):
        self.db_conn.commit()
        self.db_conn.close()

    def _find(self, query):
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
        ids = self._find(query)
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
        ids = self._find(query)
        print(f'found: {len(ids)}')
        return ids

    def update(self, obs):
        o_id = int(obs['id'])

        if obs.get('detail'):
            print('%i was deleted' % o_id)
            del self[o_id]
            return True

        # Is either an empty list or a list of objects
        obs['demoddata'] = str(obs['demoddata'])

        # Translate True/False to db-compatible 1/0 integers
        for k,v in obs.items():
            if isinstance(v, bool):
                if v:
                    obs[k] = 1
                else:
                    obs[k] = 0

        was_updated = False

        # brand new observation?
        db_obs = self[o_id]
        if db_obs is None:
            print(f'{o_id} new {obs["start"]}')
            self[o_id] = obs
            was_updated = True

        # this is an update
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
                print(f'{o_id} different data {obs["start"]}')
                print(diff)
                self[o_id] = obs
                was_updated = True

        # Fetch the demodulated frames and store in demoddata DB
        frames_downloaded = self.fetch_demoddata(obs)

        was_updated = was_updated or (frames_downloaded > 0)
        return was_updated

    def fetch_demoddata(self, obs):
        # translate the string into proper JSON
        dd = obs['demoddata'].replace("'", "\"")
        frames = json.loads(dd)

        urls = []
        for frame in frames:
            urls.append(frame['payload_demod'])
        return self.demoddata.fetch_data(urls, obs)



class DemoddataDB(dict):
    def __init__(self, db):
        """Connect to demoddata database."""
        self.db_conn = sqlite3.connect(f'file:{db}', uri=True,
                            detect_types=sqlite3.PARSE_DECLTYPES)
        self.db_conn.row_factory = sqlite3.Row
        self.db_conn.execute('''
            CREATE TABLE IF NOT EXISTS obs_demoddata (
                id INTEGER,
                datetime TEXT,
                name TEXT UNIQUE,
                data BLOB,
                azimuth REAL,
                elevation REAL,
                range REAL);''')

        self.db_conn.execute('''CREATE INDEX IF NOT EXISTS idx_obs_demoddata ON obs_demoddata(id);''')
        self.db_conn.execute('''CREATE INDEX IF NOT EXISTS idx_obs_demoddata_name ON obs_demoddata(name);''')
        self.db_conn.commit()

        with self.db_conn:
            # Extract the columns back out so we can construct an INSERT
            # statement with placeholders
            info = self.db_conn.execute('PRAGMA table_info(obs_demoddata);')
            # (1, 'start', 'TEXT', 0, None, 0)
            # n, name, type, maybe_null, default, primary
            self.keys = [k[1] for k in info]

            # Allow reads when there is a writer
            result = self.db_conn.execute('PRAGMA journal_mode=WAL;')
            assert(result.fetchone()[0] == 'wal')
        # thread-local things
        self.thread_local = threading.local()

    def __getitem__(self, key):
        """Get list of frames by observation id, or get a single frame by its
        (unique) filename."""
        if isinstance(key, int):
            query = '''SELECT *
                    FROM obs_demoddata
                    WHERE id = ?
                    ORDER BY datetime ASC;'''
            result = self.db_conn.execute(query, [key])
            items = result.fetchall()
            return items
        else:
            query = '''SELECT *
                    FROM obs_demoddata
                    WHERE name = ?;'''
            result = self.db_conn.execute(query, [key])
            items = result.fetchall()
            return items[0]

    def __del__(self):
        self.db_conn.commit()
        self.db_conn.close()

    def is_name_archived(self, name):
        results = self.db_conn.execute(
            'SELECT * FROM obs_demoddata WHERE name = ?', [name]).fetchall()
        if len(results) > 0:
            have_az = results[0]['azimuth'] is not None
        else:
            have_az = False
        return have_az

    def get_session(self):
        if not hasattr(self.thread_local, "session"):
            #thread_local.session = requests_cache.CachedSession()
            self.thread_local.session = requests.Session()
        return self.thread_local.session

    def get_frame_content(self, f, url):
        session = self.get_session()
        with session.get(url) as r:
            f['data'] = r.content
        return f

    def add_frame(self, frame):
        self.db_conn.execute('PRAGMA busy_timeout = 4000;')
        retries = 4
        while True:
            try:
                self.db_conn.execute('''INSERT INTO obs_demoddata
                    VALUES(:id, :dt, :name,
                            :data, :azimuth, :elevation, :range)
                    ON CONFLICT(name) DO
                    UPDATE SET
                        id=:id, datetime=:dt,
                        azimuth=:azimuth, elevation=:elevation, range=:range;''',
                    frame)
            except sqlite3.OperationalError as e:
                retries -= 1
                if retries == 0:
                    raise e
                continue
            break

    def _setup_tracking(self, obs):
        tle0 = obs['tle0']
        tle1 = obs['tle1']
        tle2 = obs['tle2']
        lat = obs['station_lat']
        lng = obs['station_lng']
        alt = obs['station_alt']

        satellite = skyfield.api.EarthSatellite(tle1, tle2, tle0)
        ground_station = skyfield.api.wgs84.latlon(lat, lng, elevation_m=alt)

        # vector between sat and GS
        gs_sat_pos = satellite - ground_station
        return gs_sat_pos

    def fetch_data(self, urls, observation):
        # potentially thousands of GET requests
        # hence we use threads to have multiple HTTP requests in-flight
        num_frames = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool:
            for batch in iter_chunks(urls, 1000):
                futures = []
                t1 = time.perf_counter()
                num_jobs = 0
                for url in batch:
                    u = urlparse(url)
                    dirname, filename = os.path.split(u.path)

                    # may have multiple "."
                    # but we want the part before any dots at all
                    name, *ext = filename.split('.')
                    head, obspath = os.path.split(dirname)

                    try:
                        prefix, obsid, datestr, *suffix= name.split('_')
                        assert(obsid == obspath)
                        obs = int(obsid)
                    except:
                        print(f"bad,{url}")
                        continue

                    # TODO: for now, we skip items with extensions, remove soon
                    if len(ext) > 0:
                        continue

                    try:
                        year, month, dayhour, minute, second = datestr.split('-')
                        dt = f'{year}-{month}-{dayhour}:{minute}:{second}'
                    except:
                        print(f"bad-date,{url}")
                        dt = 'YYYY-MM-DDTHH:MM:SS'
                        continue

                    # do not re-download
                    if self.is_name_archived(filename):
                        continue

                    frame = dict(id=obs,
                                 dt=dt,
                                 name=filename,
                                 data=None,
                                 azimuth=None,
                                 elevation=None,
                                 range=None)
                    futures.append(
                        pool.submit(
                            self.get_frame_content, frame, url))
                    num_jobs += 1

                if len(futures) == 0:
                    continue


                datalist = []
                for future in concurrent.futures.as_completed(futures):
                    # (obs, dt, filename, data) = future.result()
                    datalist.append(future.result())

                tf2 = time.perf_counter()

                # Compute the pointing vector
                if observation['id'] != obs:
                    raise Error(f"Error: observation ({observation['id']}) does not match frame ({obs})")

                ts = skyfield.api.load.timescale()

                # Occasionally we see a TLE that skyfield / sgp4 doesn't like
                # Report-and-ignore
                try:
                    gs_sat_pos = self._setup_tracking(observation)
                except ValueError as e:
                    print(e)
                    tle0 = observation['tle0']
                    tle1 = observation['tle1']
                    tle2 = observation['tle2']
                    print(F"*** bad TLE for {obs}\n{tle0}\n{tle1}\n{tle2}")
                    continue


                # Only commit() the after all frames, to speed up DB work
                with self.db_conn:
                    for frame in datalist:
                        frame_time = ts.from_datetime(
                                        datetime.fromisoformat(
                                            frame['dt'] + '+00:00'))

                        elevation, azimuth, slant_range = gs_sat_pos.at(frame_time).altaz()

                        frame['elevation'] = elevation.degrees
                        frame['azimuth'] = azimuth.degrees
                        frame['range'] = slant_range.km

                        self.add_frame(frame)
                        num_frames += 1


                t2 = time.perf_counter()
                duration = t2 - t1
                rate = num_jobs / duration

                duration_futures = tf2 - t1
                duration_db = t2 - tf2

                print(f"{obs}: {num_jobs:5d} in {duration:5.1f} s, {rate:5.1f} f/s" +
                      f" | {duration_futures:0.2f} fu, {duration_db:0.2f} db")
        return num_frames




def fetch_new(observations, MAX_EXTRA_PAGES, params=None):
    n_requests = 0
    r = get(OBSERVATIONS_API, params)
    n_requests += 1
    print(f"n_requests: {n_requests}")
    try:
        updated = [observations.update(o) for o in r.json()]
    except:
        print(r.json())
        raise
    any_updated = any(updated)

    nextpage = r.links.get('next')
    extra_pages = MAX_EXTRA_PAGES

    while (extra_pages > 0) and nextpage:
        r = get(nextpage['url'])
        n_requests += 1
        print(f"n_requests: {n_requests}")
        # network-dev returns a 500 server error at some point 350+ pages in
        try:
            updated = [observations.update(o) for o in r.json()]
        except Exception as e:
            print(r.json())
            print(e)
            raise e

        nextpage = r.links.get('next')

        # heuristic to capture recent updates to observations
        # keep fetching pages of observations until we see
        # MAX_EXTRA_PAGES in a row with no updates
        if not any(updated):
            extra_pages -= 1
        else:
            extra_pages = MAX_EXTRA_PAGES
        print(extra_pages)


def iter_chunks(iterable, size):
    """Iterate over the input in groups of size length."""
    it = iter(iterable)
    while chunk := tuple(islice(it, size)):
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
            observations.update(o)

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
            observations.update(o)

        print('requested/got: %d/%d' % (len(items), len(ids)))



if __name__ == '__main__':
    data = DemoddataDB('/mnt/ssd2/satnogs-demoddata/demoddata.db')
