#!/usr/bin/env python3

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

    random_scheduler(passes=passes, clients=clients, debug=True)

    return clients


clients = simulate()
# Extract a specific client from the group of Clients and look at some info
c = clients['Valparaiso University']
print('Client:', c)

print('calendar_value():')
for currency, amount in c.calendar_value().items():
    print('%11s: %f' % (currency, amount))
print('busy_time():', c.busy_time())


print()