#!/usr/bin/env python3

from datetime import datetime, timezone
import random
import pickle
import sys
sys.path.append('../python-files')  # noqa


# from ../python-files/
import db
from schedulingbazaar import load_gs, load_tles

# from ./
import client


def pass2request(pd):
    """Take a pass (as returned from db.getpasses() and construct a request
    dict for the Network to send to a Client.

    The bounty is SNC (SatNOGS Credits) with an amount set to the pass duration
    in seconds.

    When transmitted over a network, this is then converted to JSON.
    """
    d = pd.data
    job = {'id': random.randrange(2**16),  # fake an ID number
           'start': d.start.isoformat(),
           'end': d.end.isoformat(),
           'ground_station': d.gs,
           'tle0': satellites[d.sat]['tle0'],
           'tle1': satellites[d.sat]['tle1'],
           'tle2': satellites[d.sat]['tle2'],
           'frequency': -1,
           'mode': 'null',
           'transmitter': 'asdfasdasdfadsf',
           }
    duration = (d.end - d.start).total_seconds()
    bounty = [{'currency': 'SNC', 'amount': duration}]

    request = {'job': job,
               'bounty': bounty,
               }
    return request


# load a dict of GSs
stationlist = load_gs('../python-files/groundstations.txt')
stations = {s[0]: s for s in stationlist}


# load a dict of satellites
satelliteslist = load_tles('../python-files/amateur.txt')
satellites = {}
for s in satelliteslist:
    sat = {'name': s[0].strip(),
           'tle0': s[0],
           'tle1': s[1],
           'tle2': s[2],
           }
    satellites[sat['name']] = sat


# get a bunch of passes and schedule them on our set of GSs
passes = db.getpasses(
    'allpasses.sqlite')
# passes = db.getpasses(
#     '/home/dan/ed/satnogs/scheduling-bazaar/python-files/allpasses.db',
#   . sat='ISS (ZARYA)')
# passes = db.getpasses(
#     '/home/dan/ed/satnogs/scheduling-bazaar/python-files/allpasses.db')
print(len(passes))


#################################################################
#
# Core implementation of a specific set of Client policies and
# Network strategies
#
#################################################################
# create a set of clients
clients = {}
for gsname, gsdata in stations.items():
    name, lat, lon, alt = gsdata
    # c = client.AllClient(gsname, lat, lon, alt)
    c = client.YesClient(gsname, lat, lon, alt)
    clients[name] = c


#################################################################
# Everything scheduler.
#
# Schedule all possible passes with all Clients.
#
# If these are all AllClients, the total busy_time() for all clients will be
# simply the summation of all pass durations in seconds.
passes = random.sample(passes, len(passes))
for n, pd in enumerate(passes):
    # create a request
    r = pass2request(pd)
    # print(r)
    offer = clients[pd.data.gs].request(r)
    if (n % 100) == 0:
        if offer['status'] == 'accept':
            print('*', end='', flush=True)
        else:
            print('.', end='', flush=True)
print()
#
# Done with scheduling.
#
# Everything else following will use 'clients' to extract info
# about the scheduled jobs.  The accept/reject data could also be
# stored for later analysis also (it's not currently, just printed)
#
#################################################################


# save results
pickle.dump(clients, open('results.pkl', 'wb'))





# Extract a specific client from the group of Clients and look at some info
c = clients['Valparaiso University']
print('Client:', c)

print('calendar_value():')
for currency, amount in c.calendar_value().items():
    print('%11s: %f' % (currency, amount))
print('busy_time():', c.busy_time())


print()
print('Get info from a sub interval')

# 2017-06-08 13:18:26.618168+00:00
# 2018-06-06 19:55:50.772713+00:00
start = datetime(2017, 7, 1, tzinfo=timezone.utc)
end = datetime(2017, 8, 1, tzinfo=timezone.utc)
print('Start:', start)
print('End  :', end)

print('calendar_value():')
for currency, amount in c.calendar_value(start, end).items():
    print('%11s: %f' % (currency, amount))
print('busy_time():', c.busy_time(start, end))

# daily busy time
print('Daily Busy Time:', len(c.daily_busy_time()))
