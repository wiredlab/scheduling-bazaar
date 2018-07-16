#!/usr/bin/env python3

from itertools import product
import pickle
import sys
import time

import cProfile

from satbazaar import db



###########################################################
#
# Configuration

stationsfile = None
satsfile = 'satellites.json'

# dbfile = 'allpasses.sqlite'
dbfile = 'passes_2018-07-11.sqlite'

compute_function = db.compute_passes_ephem
# compute_function = db.compute_passes_orbital

start_time = '2018/7/11 00:00:00'
# duration = 8760 #a year worth of hours
duration = 24*90

num_processes = 4

# TODO: convert to argparse or other better CLI args system
print(sys.argv)
if len(sys.argv) == 4:
    stationsfile = sys.argv[1]
    satsfile = sys.argv[2]
    dbfile = sys.argv[3]

#
# ground stations
#
stations = db.load_stations(stationsfile)
print(len(stations), 'stations')

# exclude inactive stations
stations = {name:gs for name,gs in stations.items()
            if gs['status'] not in ('Offline',)}
print(len(stations), 'filtered stations')


#
# satellites
#
sats = db.load_satellites(satsfile)


#
# end configuration variables and filters
#
###########################################################


# pyorbital chokes on INMARSAT 4-F1 because it is classified as deep-space
if compute_function == db.compute_passes_orbital:
    sats = {s for s in sats if s['norad_cat_id'] not in (28628,)}

print(len(sats), 'satellites')



line = '-- %-30s -------------'
print(line % 'Computing passes')

#pr = cProfile.Profile()
#pr.enable()
tree = db.compute_all_passes(
                          iter(stations.values()),
                          iter(sats.values()),
                          start_time,
                          duration=duration,
                          dbfile=dbfile,
                          num_processes=num_processes,
                          compute_function=compute_function)
#pr.disable()
#pr.print_stats(sort='time')
# give the filesystem some time to finish closing the database file
time.sleep(1)

#testing save/load between pickle and sqlite3
nfail = 0
if False:
    print(line % 'Save/load as pickle')
    pickle.dump(tree, open('testpasses.pkl', 'wb'))
    time.sleep(1)
    treepkl = pickle.load(open('testpasses.pkl', 'rb'))

    print(line % 'Load from db')
    treeload = db.load_all_passes(dbfile)


    print(line % 'All diffs should be empty')
    trees = (tree, treepkl, treeload)
    for a,b in product(trees, trees):
        diff = a.difference(b)
        print(diff)
        if len(diff) != 0:
            nfail += 1

    if nfail == 0:
        print(line % 'All good!')
    else:
        print(line % 'FAILURES DETECTED')

sys.exit(nfail)
