"""db` -- Interaction with the database of passes and storage of data
========================================================================

Pass predictions are stored in a database.

Satellite information is stored in a JSON file, TLE information loaded
from a database.

Ground Station information is stored in a JSON file.
"""
import os
from collections import namedtuple, OrderedDict
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from itertools import product, islice
import json
import multiprocessing
from math import pi
from io import StringIO
import sqlite3
import configparser


from lxml import html

import ephem
from intervaltree import Interval, IntervalTree
import requests
import requests_cache

from satbazaar import util

requests_cache.install_cache('.satbazaar-db-cache', expire_after=60*60)



config = configparser.ConfigParser(
    interpolation=configparser.ExtendedInterpolation(),
)

# defaults
thisdir = os.path.dirname(__file__)
config.read_file(open(os.path.join(thisdir, 'satbazaar.cfg')))

config.read([
    os.path.expanduser('~/.satbazaar.cfg'),
    'satbazaar.cfg',
    ]
)


# used in database of computed sat-gs passes
PassTuple = namedtuple('PassTuple',
                       'start end duration rise_az set_az tca max_el gs norad')

# order used in TLE database
TleTuple = namedtuple('TleTuple',
                      'norad epoch line0 line1 line2 downloaded')

STATION_KEYS = ('alt', 'lat', 'lon', 'min_horizon', 'name', 'status')



class TLE:
    """Class to access TLE attributes."""
    def __init__(self, tle, source=None):
        self.source = source
        self.lines = tle
        self.line0 = tle[0]
        self.line1 = tle[1]
        self.line2 = tle[2]
        self.name = tle[0].strip()
        self.norad = int(tle[1][2:7])
        self.classification = tle[1][7]
        self.cospar = '{}-{}'.format(
            self._year_digits(tle[1][9:11]),
            tle[1][11:17].rstrip(),
        )

        y = self._year_digits(tle[1][18:20])
        year = datetime(y, 1, 1, tzinfo=timezone.utc)
        jd = timedelta(days=float(tle[1][20:32]))
        self.epoch = year + jd

        self.elset = int(tle[1][64:68])

        norad2 = int(tle[2][2:7])
        if self.norad != norad2:
            raise TypeError(
                'Inconsistent catalog numbers: {} - {}'.format(
                    self.norad, norad2))

        self.inclination = float(tle[2][8:16])
        self.raan = float(tle[2][17:25])
        self.eccentricity = float('0.' + tle[2][26:33])
        self.ap = float(tle[2][34:42])
        self.mean_anomaly = float(tle[2][43:51])
        self.mean_motion = float(tle[2][52:63])
        self.orbit = int(tle[2][63:68])

    def _year_digits(self, y):
        """Returns a year integer from a given two-digit string or integer year."""
        if isinstance(y, str):
            y = int(y)
        if y < 57:
            y += 100
        y += 1900
        return y

    def __str__(self):
        return '\n'.join(self.tle)

    def __repr__(self):
        return "TLE(source={}, line0='{}', line1='{}', line2='{}')".format(
            self.source,
            self.line0,
            self.line1,
            self.line2,
        )


class TLESource(Mapping):
    r"""Dictionary-like mapping which returns a TLE object for a given NORAD number.
    Configured sources are tried in order or raises a KeyError if the number is
    not found in any known source.

    Example:
    >>> d = TLESource()

    >>> str(d[25544])  #doctest: +ELLIPSIS
    'ISS (ZARYA)\n1 25544U 98067A ...'

    >>> repr(d[25544])  #doctest: +ELLIPSIS
    "TLE(source=CelesTrak, line0='ISS (ZARYA)', line1='1 25544U 98067A ..."
    """
    def __init__(self, sources=None, fn=None):
        self._data = {}
        if sources is None:
            sources = TLE_SOURCES

        self.data_source = {}
        for name, method, arg in sources:
            self.data_source[name] = method(name, arg)

    def __getitem__(self, norad):
        for source, d in self.data_source.items():
            if norad in d:
                v = d[norad]
                self._data[norad] = v
                return v
        raise KeyError('Unknown satellite {}'.format(norad))

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)


class APITLESource(TLESource):
    """Mapping which fetches TLEs from an API."""
    def __init__(self, name, template):
        """
        name: short string to identify the source
        template: URL template suitable for .format(norad)
        """
        self.name = name
        self.template = template
        self.client = requests.session()

    def __getitem__(self, norad):
        r = self.client.get(self.template.format(norad))
        p = html.fromstring(r.text)
        lines = p.xpath('//pre/text()')[0].split('\n')
        if len(lines) == 6:
            t = (lines[1].strip(), lines[2].strip(), lines[3].strip())
            return TLE(t, source=self.name)
        else:
            raise KeyError('{} not found'.format(norad))


class FileTLESource(TLESource):
    """Mapping which reads TLEs from text files with 3 lines per satellite."""
    def __init__(self, name, fname):
        """
        name: short string to identify the source
        fname: filename containing 3-line groups
        """
        self.name = name
        self.fname = fname
        self._data = self.read_3LE(fname)

    def __getitem__(self, norad):
        return self._data[norad]

    def _get_fp(self, fname):
        """Return a file-like object to a local file or one served via http."""
        if fname.startswith('http'):
            r = requests.get(fname)
            return StringIO(r.text)
        elif isinstance(fname, file):
            return fname
        elif isinstance(fname, str):
            return open(fname)
        else:
            raise TypeError('Unhandled type {}'.format(type(fname)))

    def read_3LE(self, fname):
        fp = self._get_fp(fname)
        data = {}
        file_iter= iter(fp)
        while file_iter:
            triple = islice(file_iter, 3)
            lines = [x.rstrip() for x in triple]
            if len(lines) == 3:
                tle = TLE(lines, source=self.name)
                data[tle.norad] = tle
            else:
                break
        return data

    def reload(self, fname=None):
        """Re-fetch the file to possibly get new data."""
        self._data = self.read_3LE(fname if fname else self.fname)


class SqliteTLESource(TLESource):
    """Mapping which reads TLEs from an sqlite3 database in read-only mode."""
    def __init__(self, name, dbfile):
        self.name = name
        self.dbfile = dbfile
        self.conn = sqlite3.connect(
            'file:' + dbfile + '?mode=ro',
            uri=True,
            detect_types=sqlite3.PARSE_DECLTYPES)
        self.conn.row_factory = sqlite3.Row
        self.cur = self.conn.cursor()

    def __getitem__(self, norad):
        query = '''SELECT * FROM tle
                     WHERE norad = ?
                     ORDER BY downloaded DESC
                     LIMIT 1'''
        data = self.cur.execute(query, (norad,)).fetchone()
        if data is not None:
            return TLE((data['line0'], data['line1'], data['line2']), source=self.name)
        else:
            raise KeyError('{} not found'.format(norad))


# ordered by fallback priority
TLE_SOURCES = (
    ('CelesTrak', APITLESource, 'http://www.celestrak.com/satcat/tle.php?CATNR={}'),
    ('AMSAT', FileTLESource, 'https://www.amsat.org/tle/current/nasabare.txt'),
    ('CalPolyMSTL', FileTLESource, 'http://mstl.atl.calpoly.edu/~ops/keps/kepler.txt'),
    ('LocalSqliteDB', SqliteTLESource, config['DEFAULT']['tle_db']),
)



def get_stations(outfile=None, networks=None):
    """
    Utility to get download / get station information from the configured
    networks.  Collects into a single dict.  Returns the dict and also writes
    to a JSON file for later retrieval.
    """
    outfile = outfile or config['DEFAULT']['stations_file']

    # default to reading stations from all networks
    if networks is None:
        networks = config.sections()

    stations = {}
    for network in networks:
        url = config[network]['stations_url']

        if url.startswith('http'):
            client = requests.session()
            r = client.get(url)
            data = r.json()

            nextpage = r.links.get('next')
            while nextpage:
                r = client.get(nextpage['url'])
                data.extend(r.json())
                nextpage = r.links.get('next')
        elif os.path.isfile(url):
            data = json.load(open(url))
        else:
            raise TypeError('Unknown protocol for: {}'.format(url))

        for gs in data:
            # normalize keys
            # SatNOGS v1 uses 'lng' for longitude
            if 'lon' not in gs:
                gs['lon'] = gs.get('lng') or gs.get('longitude')

            # SatNOGS v1 uses 'altitude' for station height above sea level
            if 'alt' not in gs:
                gs['alt'] = gs.get('altitude') or gs.get('elevation')

            # verify sufficient information is present
            for k in STATION_KEYS:
                if k not in gs:
                    raise KeyError('Missing key: {}'.format(k))

            # TODO: better to use 'network/id'?  What about GS on multiple networks?
            # key = '/'.join((config['network_name'], gs['id']))
            key = gs['name']
            stations[key] = gs

    with open(outfile, 'w') as fp:
        json.dump(stations, fp, sort_keys=True, indent=2)

    return stations


def load_stations(filename=None, from_cache=True):
    """Returns a dict of gs dicts from a file.

    Arguments:
    filename -- JSON format as returned by SatNOGS Network api/stations endpoint
                if None, use 'stations_file' from the configuration file.

    required keys:
        altitude
        lat
        lon
        min_horizon
        name
        status  (one of: Online, Testing, Offline)
    """
    # also fetch and cache the stations from the configured networks
    if not from_cache:
        return get_stations()

    # just load from the given filename or configured cache
    filename = filename or config['DEFAULT']['stations_file']
    with open(filename) as f:
        stations = json.load(f)
    return stations


def get_satellites():
    # fetch sources
    pass


def load_satellites(satsfile=None, tledb=None):
    """Load satellites from satsfile (json) and pickup the latest TLE from
    tledb.

    Only return satellites with complete information (a known TLE).
    """

    satsfile = satsfile or config['DEFAULT']['satellites_file']
    tledb = tledb or config['DEFAULT']['tle_db']

    with open(satsfile) as f:
        sats = json.load(f)
    sats = {int(norad):sat for norad, sat in sats.items()}

    conn = sqlite3.connect('file:' + tledb + '?mode=ro',
                           uri=True,
                           detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    def get_info(norad):
        query = 'SELECT * FROM tle WHERE norad = ? ORDER BY downloaded DESC LIMIT 1'
        cur.execute(query, (norad,))
        return cur.fetchone()

    for norad, sat in sats.items():
        row = get_info(norad)
        if not row:
            continue

        sat['epoch'] = row['epoch']
        sat['tle'] = (row['line0'], row['line1'], row['line2'])

    d = {norad:sat for (norad, sat) in sats.items() if 'tle' in sat}
    return d



def load_observations(obsfile=None):
    """Load a, possibly compressed, file of JSON observations."""
    obsfile = obsfile or config['DEFAULT']['observations_file']
    return json.load(util.open_compressed(obsfile))


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
            tle TEXT);''')

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

    def find(self, query):
        """Execute the query and return a list of id's that match."""
        q = f'SELECT id FROM observations WHERE {query};'

        with self.db_conn:
            result = self.db_conn.execute(q)
            # save the results to a list so we can close the cursor
            ids = [x['id'] for x in result]

        return ids

    def values(self, num):
        """Return an iterator over all observations."""
        q = f'SELECT * FROM observations LIMIT {num};'
        with self.db_conn:
            result = self.db_conn.execute(q)
            return result


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

    def commit(self):
        self.db_conn.commit()

    def close(self):
        self.db_conn.close()


def passrow2interval(p):
    data = PassTuple(**p)
    return Interval(data.start, data.end, data)


def getpasses(passes_db=None, gs=None, sat=None, start=None, end=None):
    """Retrieve all matching Satellite--Ground passes from the database.

    Unspecified arguments match all values.  Set `start` == `end` to select
    passes which overlap a time instant.

    Parameters
    ----------
    passes_db : str
        Filename of SQLite3 database of pre-computed passes.
    gs : str
        Glob string selecting a Ground Station name.
    sat : int
        Glob selecting satellite(s).
    start : datetime or SQlite3 datetime string
        Select passes which end on or after `start` time.
    end : datetime or SQlite3 datetime string
        Select passes which start on or before `end` time.

    Returns
    -------
    IntervalTree
        All matching passes from the database with `.data` set to a `PassTuple`.
    """
    passes_db = passes_db or config['DEFAULT']['passes_db']
    tree = IntervalTree()

    conn = sqlite3.connect('file:' + passes_db + '?mode=ro',
                           uri=True,
                           detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row

    query = 'SELECT * FROM passes'
    args = []
    conditions = []
    for (name, var) in (('gs', gs), ('sat', sat),):
        if var is not None:
            conditions.append('{} GLOB ?'.format(name))
            args.append(var)

    # return passes which overlap the end points
    if start is not None:
        conditions.append("end >= datetime('{}')".format(start))

    if end is not None:
        conditions.append("start <= datetime('{}')".format(end))

    if conditions:
        query += ' WHERE ' + ' AND '.join(conditions)

    for p in conn.execute(query, args):
        tree.add(passrow2interval(p))
    conn.close()
    return tree


def compute_passes_ephem(args):
    """Config obs and sat, Return pass data for all passes in given interval.
    uses PyEphem library

    Arguments:
    observer -- 4 element list containing desired [name,lat,lon,alt]
    tle -- 3 element list containing desired tle [line0,line1,line2]
    start_time -- ephem.date string formatted 'yyyy/mm/dd hr:min:sec'
    num_passes -- integer number of desired passes (defualt None)
    duration -- float number of hours or fraction of hours (default None)

    Specify either num_passes or duration.
    If both, use min(num_passes, duration).
    If neither, find passes for next 24 hours.
    """
    (observer, satellite, start_time, num_passes, duration) = args
    # s = "%s <--> %s | " % (observer['name'], satellite['name'].strip())
    s = "%3i <--> %5i | " % (observer['id'], satellite['norad_cat_id'])

    tle_line0, tle_line1, tle_line2 = satellite['tle']

    # Set up location of observer
    ground_station = ephem.Observer()
    ground_station.name = observer['name']        # name string
    ground_station.lon = str(observer['lon'])          # in degrees (+E)
    ground_station.lat = str(observer['lat'])          # in degrees (+N)
    ground_station.elevation = observer['altitude']       # in meters
    ground_station.date = ephem.date(start_time)  # in UTC
    ground_station.horizon = str(observer['min_horizon'])  # in degrees
    ground_station.pressure = 0  # ignore atmospheric refraction at the horizon

    # Read in most recent satellite TLE data
    sat = ephem.readtle(tle_line0, tle_line1, tle_line2)

    contacts = []

    if duration is None and num_passes is None:
        # get passes for next 24 hrs
        duration = 24
        # set num_passes > max passes possible in duration.
        # duration is in hours, so 4 per hour is large
        # enough for duration to break out of loop.
        num_passes = 4 * int(duration)
        # set end_time longer than suggested length for tle's
        end_time = ephem.date(ground_station.date+5*365)
    if duration is not None and num_passes is None:
        # set num_passes > max passes possible in duration.
        # duration is in hours, so 4 per hour is large
        # enough for duration to break out of loop.
        num_passes = 4 * int(duration)
        end_time = ephem.date(ground_station.date+duration*ephem.hour)
    if duration is None and num_passes is not None:
        # set end_time longer than suggested length for tle's
        end_time = ephem.date(ground_station.date+5*365)
    if num_passes is not None and duration is not None:
        # if both are given, use minimum
        end_time = ephem.date(ground_station.date+duration*ephem.hour)

    for i in range(num_passes):
        # have we reached the requested duration?
        if ground_station.date > end_time:
            break

        # fill in all body attributes for sat
        sat.compute(ground_station)

        # next pass command yields array with [0]=rise time,
        # [1]=rise azimuth, [2]=max alt time, [3]=max alt,
        # [4]=set time, [5]=set azimuth
        try:
            info = ground_station.next_pass(sat)
        except ValueError:
            # could not find a rise time
            s += 'E'
            print(s)
            # print('pyephem: ValueError')
            return []

        # check None indicating libastro NORISE, NOSET, NOTRANS flags
        if not all(info):
            s += 'F'
            # print('pyephem: NORISE NOSET NOTRANS')
            # keep looking
            ground_station.date = ground_station.date + ephem.minute
            continue

        rise_time, rise_az, max_alt_time, max_alt, set_time, set_az = info

        deg_per_rad = 180.0/pi

        pass_duration = timedelta(days=set_time-rise_time)  # timedelta
        r_angle = rise_az * deg_per_rad
        s_angle = set_az * deg_per_rad
        rising = rise_time.datetime()
        setting = set_time.datetime()
        pass_seconds = timedelta.total_seconds(pass_duration)
        tca = max_alt_time.datetime()
        max_el = max_alt * deg_per_rad

        if setting > rising:
            pass_data = {
                'start': rising,
                'end': setting,
                'duration': pass_seconds,
                'rise_az': r_angle,
                'set_az': s_angle,
                'tca': tca,
                'max_el': max_el,
                'gs': observer['name'],
                'norad': satellite['norad_cat_id'],
            }
            # update current time
            ground_station.date = set_time
            contacts.append(pass_data)
            s += '.'
        else:
            s += 'N'
            # print('pyephem: AOS > LOS')

        # increase by 1 min and look for next pass
        ground_station.date = ground_station.date + ephem.minute

    print(s)
    # convert to namedtuples since the info doesn't change
    data = []
    for p in contacts:
        d = PassTuple(**p)
        data.append(d)
    return data


def compute_passes_orbital(args):
    """Config obs and sat, Return pass data for all passes in given interval.
    uses Pyorbital library

    Arguments:
    observer -- 4 element list containing desired [name,lat,lon,alt]
    tle -- 3 element list containing desired tle [line0,line1,line2]
    start_time -- ephem.date string formatted 'yyyy/mm/dd hr:min:sec'
    num_passes -- integer number of desired passes (defualt None)
    duration -- float number of hours or fraction of hours (default None)

    Specify either num_passes or duration.
    If both, use min(num_passes, duration).
    If neither, find passes for next 24 hours.
    """
    from pyorbital.orbital import Orbital

    (observer, satellite, start_time, num_passes, duration) = args
    print("%s <--> %s" % (observer['name'], satellite['name'].strip()), flush=True)

    tle = satellite['tle']

    try:
        body = Orbital(tle[0], line1=tle[1], line2=tle[2])
    except NotImplementedError:
        # pyorbital doesn't implement the SDP4 for orbital periods >225 minutes
        # considered deep-space or not near-earth by NORAD
        print('*** deep space')
        return []

    start_time = ephem.date(start_time).datetime()

    try:
        passes = body.get_next_passes(
            start_time,
            duration,
            observer['lng'],
            observer['lat'],
            observer['altitude'],
            horizon=observer['min_horizon'])
    except Exception:
        # or just plain crashed
        print('*** crash')
        return []

    contacts = []
    for rise, fall, maxtime in passes:
        pass_duration = fall - rise  # timedelta
        pass_seconds = timedelta.total_seconds(pass_duration)
        tca = maxtime

        # ignore bogus passes
        if pass_seconds < 1.0:
            continue

        def azel(time):
            az, el = body.get_observer_look(
                time,
                observer['lng'],
                observer['lat'],
                observer['altitude']
            )
            return az, el

        _, max_el = azel(maxtime)
        r_angle, _ = azel(rise)
        s_angle, _ = azel(fall)

        pass_data = {
            'start': rise,
            'end': fall,
            'duration': pass_seconds,
            'rise_az': r_angle,
            'set_az': s_angle,
            'tca': tca,
            'max_el': max_el,
            'gs': observer['name'],
            'norad': satellite['norad_cat_id'],
        }
        contacts.append(pass_data)
    # convert to namedtuples since the info doesn't change
    data = []
    for p in contacts:
        d = PassTuple(**p)
        data.append(d)
    return data


def compute_all_passes(stations, satellites, start_time,
                       passes_db=None,
                       num_passes=None, duration=None,
                       num_processes=4,
                       compute_function=compute_passes_ephem):
    """Finds passes for all combinations of stations and satellites.

    Saves the pass info as rows in an sqlite3 database and returns the data as
    an IntervalTree with each data member set to the pass info as a namedtuple.

    num_processes > 1 (default: 4) will use a parallel map() for computation.
    """
    passes_db = passes_db or config['DEFAULT']['passes_db']

    conn = sqlite3.connect('file:' + passes_db, uri=True,
                           detect_types=sqlite3.PARSE_DECLTYPES)
    cur = conn.cursor()
    cur.execute('''DROP TABLE IF EXISTS passes;''')

    # column order needs to match PassTuple order
    cur.execute('''CREATE TABLE passes
              (start timestamp,
              end timestamp,
              duration real,
              rise_az real,
              set_az real,
              tca timestamp,
              max_el real,
              gs text,
              norad integer);''')
    cur.execute('''CREATE INDEX idx_gs ON passes (gs);''')
    cur.execute('''CREATE INDEX idx_norad ON passes (norad);''')
    cur.execute('''CREATE INDEX idx_gs_norad ON passes (gs, norad);''')

    tree = IntervalTree()

    jobargs = product(stations,
                      satellites,
                      (start_time,),  # single args are repeated
                      (num_passes,),
                      (duration,))

    if num_processes > 1:
        with multiprocessing.Pool(num_processes) as pool:
            result = pool.map(compute_function, jobargs)
    else:
        result = list(map(compute_function, jobargs))

    print('Computed', len(result), 'Sat--GS pairs')

    for passdata in result:
        for d in passdata:
            try:
                tree.addi(d.start, d.end, d)
                cur.execute(
                        'INSERT INTO passes VALUES (?,?,?,?,?,?,?,?,?);', d)
            except ValueError:
                print('!!! Invalid pass !!!')
                print(d.start)
                print(d.end)
                print(d)
    conn.commit()
    conn.close()
    print('%i passes' % len(tree))
    return tree
