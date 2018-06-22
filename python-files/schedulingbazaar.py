# Python module for scheduling bazaar project
# Includes: TLE class
#           load_gs()
#           load_tles()
#           get_passes()
#           calc_access_time()
#           plot_access_time()

# Import necessary libraries
from datetime import timedelta
from itertools import islice
import json
import math


import ephem
import matplotlib.pyplot as plt
# import seaborn


# TLE class definition
class TLE:
    """TLE class used for various tle attributes.

    Args: a three element list containing tle lines
    """
    def __init__(self, tle):
        self.tle = tle
        self.tle0 = tle[0]
        self.tle1 = tle[1]
        self.tle2 = tle[2]
        self.name = tle[0].rstrip()
        self.noradid = tle[1][2:7]
        self.epoch = tle[1][18:32]
        self.inclination = tle[2][8:16]

    def __str__(self):
        return '%s\n%s\n%s' % (self.tle0, self.tle1, self.tle2)


# load_tles() function definition
def load_tles(filename):
    """Returns a list of tle's from a file.

    Arguments:
    filename -- file name string containing unparsed tles
    """
    data = []
    with open(filename) as f:
        while True:
            # an iterator that returns the next N lines and stops
            tripleline = islice(f, 3)
            # loop over these N lines, removing trailing spaces and \n
            tle = [x.rstrip() for x in tripleline]

            # only accept complete data
            # the end of the file *should* have len(tle)==0 but
            # this also handles extra junk at the end
            if len(tle) == 3:
                data.append(tle)
            else:
                break
    return data



## calc_access_time() function definition
#def calc_access_time(start, gs, tle, days, horizon='00:00'):
#    """Calculates Access Time in seconds/day.
#
#    Arguments:
#    start -- string formatted 'yyyy/mm/dd HH:MM:SS'
#    gs -- 4 element list containing desired [name,lat,lon,alt]
#    tle -- 3 element list containing desired tle [line0,line1,line2]
#    days -- num of day to calc/plot access time
#    horizon -- str optional specification for observer horizon (defualt 0 deg)
#    """
#    time = days
#    start_time = ephem.date(start)
#    access_list = []
#    day_list = []
#
#    for days in range(time):
#        num_passes = None
#        duration = 24.0
#        gs_passes = {}
#
#        gs_passes[tle.noradid] = get_passes(gs, tle.tle, start_time,
#                                            num_passes=num_passes,
#                                            duration=duration,
#                                            horizon=horizon)
#
#        access_time = 0
#        for sat, passes in gs_passes.items():
#            for obs in passes:
#                access_time = access_time + obs['duration']
#        access_list.append(access_time)
#        day_list.append(days)
#        start_time = start_time + 1
#    return day_list, access_list


# plot_access_time() function definition
def plot_access_time(start, gs, tle, days, horizon='00:00'):
    """Plots Access Time in seconds/day.

    Arguments:
    start -- string formatted 'yyyy/mm/dd HH:MM:SS'
    gs -- 4 element list containing desired [name,lat,lon,alt]
    tle -- 3 element list containing desired tle [line0,line1,line2]
    days -- num of day to calc/plot access time
    horizon -- str optional specification for observer horizon (defualt 0 deg)
    """
    tle = TLE(tle)

    day_list, access_list = calc_access_time(start, gs, tle, days,
                                             horizon=horizon)

    fig = plt.figure(1)
    fig.suptitle('%s Access time for %s GS' % (tle.name, gs[0]))

    s1 = plt.subplot(221)
    s1.plot(day_list, access_list, 'b.')
    plt.xlabel('Days from %s' % (start))
    plt.ylabel('Access time (sec/day)')

    plt.subplot(222)
    plt.plot(day_list, access_list, 'b-')
    plt.xlabel('Days from %s' % (start))

    plt.show()
