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
def load_tles(file):
    """Returns a list of tle's from a file.

    Arguments:
    file -- file name string containing unparsed tles
    """
    data = []
    with open(file) as f:
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


# load_gs() function definition
def load_gs(file):
    """Returns a list of gs from a file.

    Arguments:
    file -- file name string containing unparsed gs

    gs has four elements: name, lat, lon, alt
    """
    stations = []
    with open(file) as f:
        while True:
            # an iterator that returns the next N lines and stops
            fourline = islice(f, 4)
            # loop over these N lines, removing trailing spaces and \n
            gs = [x.rstrip() for x in fourline]

            # only accept complete data
            # the end of the file *should* have len(tle)==0 but
            # this also handles extra junk at the end
            if len(gs) == 4:
                stations.append(gs)
            else:
                break
    return stations


# get_passes() function definition
def get_passes(observer, tle, start_time,
               num_passes=None, duration=None, horizon='00:00'):
    """Config obs and sat, Return pass data for all passes in given interval.

    Arguments:
    observer -- 4 element list containing desired [name,lat,lon,alt]
    tle -- 3 element list containing desired tle [line0,line1,line2]
    start_time -- ephem.date string formatted 'yyyy/mm/dd hr:min:sec'
    num_passes -- integer number of desired passes (defualt None)
    duration -- float number of hours or fraction of hours (default None)
    horizon -- str optional specification for observer horizon (defualt 0 deg)

    Specify either num_passes or duration.
    If both, use min(num_passes, duration).
    If neither, find passes for next 24 hours.
    """

    obs_name, obs_lat, obs_lon, obs_alt = observer
    tle_line0, tle_line1, tle_line2 = tle

    # Set up location of observer
    ground_station = ephem.Observer()
    ground_station.name = obs_name                # name string
    ground_station.lon = obs_lon                  # in degrees (+E)
    ground_station.lat = obs_lat                  # in degrees (+N)
    ground_station.elevation = int(obs_alt)       # in meters
    ground_station.date = ephem.date(start_time)  # in UTC
    ground_station.horizon = horizon              # in degrees

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

    try:
        for i in range(num_passes):
            if ground_station.date > end_time:
                break
            sat.compute(ground_station)  # compute all body attributes for sat
            # next pass command yields array with [0]=rise time,
            # [1]=rise azimuth, [2]=max alt time, [3]=max alt,
            # [4]=set time, [5]=set azimuth
            info = ground_station.next_pass(sat)
            rise_time, rise_az, max_alt_time, max_alt, set_time, set_az = info
            deg_per_rad = 180.0/math.pi           # use to conv azimuth to deg
            try:
                pass_duration = timedelta(days=set_time-rise_time)  # timedelta
                r_angle = (rise_az*deg_per_rad)
                s_angle = (set_az*deg_per_rad)
            except TypeError:
                # when no set or rise time
                pass
            try:
                rising = rise_time.datetime()
                setting = set_time.datetime()
                pass_seconds = timedelta.total_seconds(pass_duration)
                tca = max_alt_time.datetime()
                max_el = (max_alt * deg_per_rad)
            except AttributeError:
                # when no set or rise time
                pass

            pass_data = {
                'start': rising,
                'end': setting,
                'duration': pass_seconds,
                'rise_az': r_angle,
                'set_az': s_angle,
                'tca': tca,
                'max_el': max_el,
                'gs': obs_name,
                'sat': tle_line0.strip(),
            }

            try:
                # only update if set time > rise time
                if set_time > rise_time:
                    # new obs time = prev set time
                    ground_station.date = set_time
                    if ground_station.date <= end_time:
                        contacts.append(pass_data)
            except TypeError:
                pass

            # increase by 1 min and look for next pass
            ground_station.date = ground_station.date + ephem.minute
    except ValueError:
        # No (more) visible passes
        pass
    return contacts


# calc_access_time() function definition
def calc_access_time(start, gs, tle, days, horizon='00:00'):
    """Calculates Access Time in seconds/day.

    Arguments:
    start -- string formatted 'yyyy/mm/dd HH:MM:SS'
    gs -- 4 element list containing desired [name,lat,lon,alt]
    tle -- 3 element list containing desired tle [line0,line1,line2]
    days -- num of day to calc/plot access time
    horizon -- str optional specification for observer horizon (defualt 0 deg)
    """
    time = days
    start_time = ephem.date(start)
    access_list = []
    day_list = []

    for days in range(time):
        num_passes = None
        duration = 24.0
        gs_passes = {}

        gs_passes[tle.noradid] = get_passes(gs, tle.tle, start_time,
                                            num_passes=num_passes,
                                            duration=duration,
                                            horizon=horizon)

        access_time = 0
        for sat, passes in gs_passes.items():
            for obs in passes:
                access_time = access_time + obs['duration']
        access_list.append(access_time)
        day_list.append(days)
        start_time = start_time + 1
    return day_list, access_list


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
