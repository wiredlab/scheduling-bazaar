#!/usr/bin/env python

# simulate used for comparing different scheduling methods
def simulate():
    """Simulates client and network interaction using
    given scheduling method.
    """

    from datetime import datetime, timezone
    import random
    import sys
    sys.path.append('../python-files')  # noqa

    # from ../python-files/
    import db
    import schedulers
    from schedulingbazaar import load_gs, load_tles

    # from ./
    import client

    # get passes
    passes = db.getpasses(
        'allpasses.db',
        gs='Valparaiso University')

    #################################################################
    #
    # Core implementation of a specific set of Client policies and
    # Network strategies
    #
    #################################################################
    # load a dict of GSs
    stationlist = load_gs('../python-files/groundstations.txt')
    stations = {s[0]: s for s in stationlist}

    # create a set of clients
    clients = {}
    for gsname, gsdata in stations.items():
        name, lat, lon, alt = gsdata
        # c = client.AllClient(gsname, lat, lon, alt)
        c = client.YesClient(gsname, lat, lon, alt)
        clients[name] = c


def pass2request(pd):
    """Take a pass (as returned from db.getpasses() and construct a request
    dict for the Network to send to a Client.

    The bounty is SNC (SatNOGS Credits) with an amount set to the pass duration
    in seconds.

    When transmitted over a network, this is then converted to JSON.
    """
    d = pd.data
    job = {'id': random.randrange(2**16),  # fake an ID number
           'start': d.start.isoformat(' '),
           'end': d.end.isoformat(' '),
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