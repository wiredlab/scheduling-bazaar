# Import necessary libraries
import ephem
import math
from datetime import timedelta


# get_passes() function definition
def new_get_passes(observer, tle, start_time, num_passes=None, duration=None):
    """Config obs and sat, Return pass data for all passes in given interval.

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

    obs_name, obs_lat, obs_lon, obs_alt = observer
    tle_line0, tle_line1, tle_line2 = tle

    # Set up location of observer
    ground_station = ephem.Observer()
    ground_station.name = obs_name                # name string
    ground_station.lon = obs_lon                  # in degrees (+E)
    ground_station.lat = obs_lat                  # in degrees (+N)
    ground_station.elevation = obs_alt            # in meters
    ground_station.date = ephem.date(start_time)  # in UTC

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
            pass_duration = timedelta(days=set_time-rise_time)  # timedelta

            pass_data = {
                'start': rise_time.datetime().ctime(),
                'end': set_time.datetime().ctime(),
                'duration': str(pass_duration),
                'rise_az': (rise_az*deg_per_rad),
                'set_az': (set_az*deg_per_rad)
            }

            if set_time > rise_time:  # only update if set time > rise time
                ground_station.date = set_time  # new obs time = prev set time
                contacts.append(pass_data)

            # increase by 1 min and look for next pass
            ground_station.date = ground_station.date + ephem.minute
    except ValueError:
        # No (more) visible passes
        pass
    return contacts
