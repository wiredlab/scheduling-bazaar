
from collections import namedtuple
from datetime import datetime, timezone
import sqlite3

import intervaltree

from schedulingbazaar import rfc3339_to_dt


# this should be only defined in one place (schedulingbazaar)
# but I'm not getting it to work right yet...
PassTuple = namedtuple('PassTuple',
                       'start end duration rise_az set_az tca max_el gs sat')


def getpasses(dbfile, gs='%', sat='%'):
    """Return an IntervalTree of PassTuples, filtered by the named GS or Sat.
    """
    tree = intervaltree.IntervalTree()

    conn = sqlite3.connect('file:' + dbfile + '?mode=ro', uri=True)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    query = 'SELECT * FROM passes WHERE gs LIKE ? AND sat LIKE ?;'
    args = [gs, sat]

    for p in cur.execute(query, args):
        data = PassTuple(p['start'], p['end'], p['duration'],
                         p['rise_az'], p['set_az'],
                         p['tca'], p['max_el'],
                         p['gs'], p['sat'])
        start = rfc3339_to_dt(data.start)
        end = rfc3339_to_dt(data.end)
        tree.addi(start, end, data)
    conn.close()
    return tree
