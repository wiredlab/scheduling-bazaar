# get_passes() function
# This function will take in a 3 element list of observer data containing [name,latitude,longitude,altitude],
# a 3 element list of satellite TLE data, a start time formatted as an ephem date, and a desired number of passes to find
# EX: vu = ['Valparaiso University', '41.4639', '-87.0439', 245.089]
#     tle = ['ISS', '1 25544U 98067A   17144.56334412  .00016717  00000-0  10270-3 0  9002', '2 25544  51.6383 156.0737 0005162 190.1606 169.9443 15.53944016 18074']
#     start_time = '2017/5/30 12:00:00'
#     num_passes = 20
# This function will return a list called pass_data with number of elements = num_passes.
# Each element in pass_data is a 5-element list containing:
#    rise_time (ephem date), set_time (ephem date), pass_duration (as fraction of a day), rise_az (in deg), set_az (in deg)
# for each pass.

# Import necessary libraries
import ephem
import math
from datetime import datetime

# get_passes() function definition
def get_passes(observer,tle,start_time,num_passes):
    """lkjhgkjhgjkghkjhg"""

    obs_name, obs_lat, obs_lon, obs_alt = observer
    tle_line0, tle_line1, tle_line2 = tle
    start = ephem.date(start_time)

    # Set up location of observer
    ground_station = ephem.Observer()
    ground_station.name = obs_name                                           # name string
    ground_station.lon = obs_lon                                             # in degrees (+E)
    ground_station.lat = obs_lat                                             # in degrees (+N)
    ground_station.elevation = obs_alt                                       # in meters
    ground_station.date = start                                              # in UTC (begin looking for next sat passes at this time)

    # Read in most recent satellite TLE data
    sat = ephem.readtle(tle_line0, tle_line1,tle_line2)

    # Find all passes during duration
    i = 0
    pass_data = {}
    for i in range(num_passes):
        sat.compute(ground_station)                                          # compute all body attributes for sat
        # next pass command yields array with [0]=rise time, [1]=rise azimuth, [2]=max alt time, [3]=max alt, [4]=set time, [5]=set azimuth
        info = ground_station.next_pass(sat)
        rise_time, rise_az, max_alt_time, max_alt, set_time, set_az = info
        deg_per_rad = 180.0/math.pi                                          # use to display azimuth in degrees
        pass_duration = (set_time-rise_time)                                 # (set time - rise time) --> fraction of a day

        if set_time > rise_time:                                             # only update if the set time is greater than the rise time
            ground_station.date = set_time                                   # new observer date & time = previous set time

        pass_data[i] = [rise_time, set_time, pass_duration, (rise_az*deg_per_rad), (set_az*deg_per_rad)]

        ground_station.date = ground_station.date + ephem.minute             # increase time by 1 min and look for next pass
    return pass_data                                                         # return list of 5-element pass predictions