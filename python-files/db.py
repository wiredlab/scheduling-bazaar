"""db` -- Interaction with the database of passes and storage of data
========================================================================

Pass predictions are stored in the database
"""
from collections import namedtuple
from itertools import product
import multiprocessing
import sqlite3

from intervaltree import Interval, IntervalTree

import schedulingbazaar


# this should be only defined in one place (schedulingbazaar)
# but I'm not getting it to work right yet...
PassTuple = namedtuple('PassTuple',
                       'start end duration rise_az set_az tca max_el gs sat')


def passrow2interval(p):
    data = PassTuple(**p)
    return Interval(data.start, data.end, data)


def getpasses(dbfile, gs='%', sat='%'):
    """Return an IntervalTree of PassTuples, filtered by the named GS or Sat.
    Use SQLite wildcards for matching.  Unspecified terms default to matching
    all.
    """
    tree = IntervalTree()

    conn = sqlite3.connect('file:' + dbfile + '?mode=ro', uri=True,
                           detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    query = 'SELECT * FROM passes WHERE gs LIKE ? AND sat LIKE ?;'
    args = [gs, sat]

    for p in cur.execute(query, args):
        tree.add(passrow2interval(p))
    conn.close()
    return tree


def _compute(args):
    """Wrapper for get_passes() for use with map() and converts the list of
    dicttionaries to a list of namedtuples to save RAM.
    """
    gs, sat, start, npasses, dur, horizon = args
    print(gs[0], sat[0].strip(), flush=True)
    passes = schedulingbazaar.get_passes(
        gs, sat, start,
        num_passes=npasses,
        duration=dur,
        horizon=horizon)
    # convert to namedtuples since the info doesn't change
    data = []
    for p in passes:
        d = PassTuple(**p)
        data.append(d)
    return data


def compute_all_passes(stations, satellites, start_time,
                       dbfile='passes.db',
                       num_passes=None, duration=None, horizon='10:00'):
    """Finds passes for all combinations of stations and satellites.

    Saves the pass info as rows in an sqlite3 database and returns the data as
    an IntervalTree with each data member set to the pass info as a namedtuple.

    horizon is a string in degrees:minutes for pyephem
    """
    conn = sqlite3.connect('file:' + dbfile, uri=True,
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
              sat text);''')

    tree = IntervalTree()

    with multiprocessing.Pool(4) as pool:
        jobargs = product(stations,
                          satellites,
                          (start_time,),
                          (num_passes,),
                          (duration,),
                          (horizon,))
        result = pool.map(_compute, jobargs)
        print('Computed', len(result), 'Sat--GS pairs')

    # for (gs, sat) in product(stations, satellites):
        # passdata = compute(gs, sat)

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
    return tree


def load_all_passes(dbfile='passes.db'):
    """Loads pre-computed passes from the SQLite database into an IntervalTree
    whose data is a namedtuple PassTuple.
    """
    tree = IntervalTree()
    conn = sqlite3.connect('file:' + dbfile + '?mode=ro', uri=True,
                           detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    for p in cur.execute('''SELECT * FROM passes;'''):
        tree.add(passrow2interval(p))
    conn.close()
    return tree
