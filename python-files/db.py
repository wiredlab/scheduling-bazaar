"""db` -- Interaction with the database of passes and storage of data
========================================================================

Pass predictions are stored in the database
"""
from collections import namedtuple
import sqlite3

from intervaltree import Interval, IntervalTree
from iso8601 import parse_date


# this should be only defined in one place (schedulingbazaar)
# but I'm not getting it to work right yet...
PassTuple = namedtuple('PassTuple',
                       'start end duration rise_az set_az tca max_el gs sat')

def passrow2interval(pass):
    data = PassTuple(p['start'], p['end'], p['duration'],
                        p['rise_az'], p['set_az'],
                        p['tca'], p['max_el'],
                        p['gs'], p['sat'])
    start = parse_date(data.start)
    end = parse_date(data.end)
    return Interval(start, end, data)


def getpasses(dbfile, gs='%', sat='%'):
    """Return an IntervalTree of PassTuples, filtered by the named GS or Sat.
    Use SQLite wildcards for matching.  Unspecified terms default to matching
    all.
    """
    tree = IntervalTree()

    conn = sqlite3.connect('file:' + dbfile + '?mode=ro', uri=True)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    query = 'SELECT * FROM passes WHERE gs LIKE ? AND sat LIKE ?;'
    args = [gs, sat]

    for p in cur.execute(query, args):
        i = passrow2interval(p)
        tree.add(i)
    conn.close()
    return tree
