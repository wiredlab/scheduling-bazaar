# Filters for returning only necessary data for analysis
# Includes: passes_per_gs()
#           passes_per_sat()
#           passes_gs_sat()

import datetime
import collections
import intervaltree as iv


# passes_per_gs() function definition
def passes_per_gs(passes, gs):
    """Returns Interval Tree containing all pass intervals over spec ground station

    Arguments:
    passes - initial dictionary of all passes for all gs/sat combos
    gs - specific ground station name string
    """
    passtree = iv.IntervalTree()
    Names = collections.namedtuple('Names', ['gs', 'sat', 'pass_data'])
    for (t1, t2), value in passes.items():
        for satpass in value:
            if t1 == gs:
                begin = datetime.datetime.timestamp(satpass['start'])
                end = datetime.datetime.timestamp(satpass['end'])
                data = Names(gs, t2, satpass)
                passtree.addi(begin, end, data)
    return passtree


# passes_per_sat() function definition
def passes_per_sat(passes, sat):
    """Returns Interval Tree containing all pass intervals for specified satellite

    Arguments:
    passes - initial dictionary of all passes for all gs/sat combos
    sat - specific satellite name string
    """
    passtree = iv.IntervalTree()
    Names = collections.namedtuple('Names', ['gs', 'sat', 'pass_data'])
    for (t1, t2), value in passes.items():
        for satpass in value:
            if t2 == sat:
                begin = datetime.datetime.timestamp(satpass['start'])
                end = datetime.datetime.timestamp(satpass['end'])
                data = Names(t1, sat, satpass)
                passtree.addi(begin, end, data)
    return passtree


# passes_gs_sat() function definition
def passes_gs_sat(passes, gs, sat):
    """Returns Interval Tree containing all pass intervals for one gs/sat combo

    Arguments:
    passes - initial dictionary of all passes for all gs/sat combos
    gs - specific ground station name string
    sat - specific satellite name string
    """
    passtree = iv.IntervalTree()
    Names = collections.namedtuple('Names', ['gs', 'sat', 'pass_data'])
    for (t1, t2), value in passes.items():
        for satpass in value:
            if t1 == gs and t2 == sat:
                begin = datetime.datetime.timestamp(satpass['start'])
                end = datetime.datetime.timestamp(satpass['end'])
                data = Names(gs, sat, satpass)
                passtree.addi(begin, end, data)
    return passtree
