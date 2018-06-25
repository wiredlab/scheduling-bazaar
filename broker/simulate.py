#!/usr/bin/env python3

# simulate used for comparing different scheduling methods
def simulate():
    """Simulates client and network interaction using
    given scheduling method.
    """

    from datetime import datetime, timezone
    import sys
    sys.path.append('../python-files')  # noqa

    # from ../python-files/
    import db
    import schedulers

    # from ./
    import client

    # get passes
    passes = db.getpasses(
        'allpasses.sqlite',
        gs='KB9JHU')

    #################################################################
    #
    # Core implementation of a specific set of Client policies and
    # Network strategies
    #
    #################################################################
    # load a dict of GSs
    stations = db.load_stations()

    # create a set of clients
    clients = {}
    for gs in stations:
        # c = client.AllClient(gsname, lat, lon, alt)
        c = client.YesClient(gs)
        clients[c.name] = c

    schedulers.random_scheduler(passes=passes, clients=clients, debug=False)

    return clients


clients = simulate()
# Extract a specific client from the group of Clients and look at some info
c = clients['KB9JHU']
print('Client:', c)

print('calendar_value():')
for currency, amount in c.calendar_value().items():
    print('%11s: %f' % (currency, amount))
print('busy_time():', c.busy_time())

import analysis
results = analysis.standard_analysis(clients)

print()
