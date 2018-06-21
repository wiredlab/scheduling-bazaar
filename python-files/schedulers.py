# This file contains the different scheduling method definitions to be used
# when simulating.
import random

from schedulingbazaar import load_tles


def random_scheduler(passes, clients, debug=False):
    """Randomly schedules passes on the given clients (which are already
    instantiated with the desired client type).

    passes - candidate passes for scheduling.
    clients - dict of ground stations to use.
    debug - Boolean, defualt False. Will print out status markers for each
            pass when True.
    """

    passes = random.sample(passes, len(passes))
    for pd in passes:
        # create a request
        r = pass2request(pd)
        import json
        print(json.dumps(r))
        offer = clients[pd.data.gs].request(r)
        if debug is True:
            if offer['status'] == 'accept':
                print('*', end='', flush=True)
            else:
                print('.', end='', flush=True)
    return clients


# def max_gs_el(passes, clients, debug=False):


# def max_sat_el(passes, clients, debug=False):


def pass2request(pd):
    """Take a pass (as returned from db.getpasses() and construct a request
    dict for the Network to send to a Client.

    The bounty is SNC (SatNOGS Credits) with an amount set to the pass duration
    in seconds.

    When transmitted over a network, this is then converted to JSON.
    """
    satellites = load_sat_dict()
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
               'status': 'initial',
               }
    return request


# load a dict of satellites
def load_sat_dict():
    satelliteslist = load_tles('../python-files/amateur.txt')
    satellites = {}
    for s in satelliteslist:
        sat = {'name': s[0].strip(),
               'tle0': s[0],
               'tle1': s[1],
               'tle2': s[2],
               }
        satellites[sat['name']] = sat
    return satellites
