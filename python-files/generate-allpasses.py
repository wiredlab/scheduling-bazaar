#!/usr/bin/env python3

from itertools import product
import pickle
import sys
import time

import cProfile

from db import compute_all_passes, load_all_passes, load_satellites
from schedulingbazaar import load_tles, load_gs


print(sys.argv)

# stationsfile = 'groundstations.txt'
stationsfile = 'network-stations.json'
# satsfile = 'amateur.txt'
satsfile = 'satellites.json'


dbfile = 'allpasses.sqlite'
compute_function = 'ephem'
# dbfile = 'ephem-passes.sqlite'
# compute_function = 'orbital'
# dbfile = 'orbital-passes.sqlite'

if len(sys.argv) == 4:
    stationsfile = sys.argv[1]
    satsfile = sys.argv[2]
    dbfile = sys.argv[3]

#
# ground stations
#
stations = load_gs(stationsfile)
print(len(stations))

# only include online stations
stations[:] = [s for s in stations if s['status'] in ('Online',)]
print(len(stations))


#
# satellites
#
sats = load_satellites(satsfile)

# pyorbital chokes on INMARSAT 4-F1 because it is classified as deep-space
sats[:] = [s for s in sats if s['norad_cat_id'] not in (28628,)]
# sats = load_tles(satsfile)


start_time = '2018/6/20 00:00:00'
# duration = 8760 #a year worth of hours
duration = 24*90

line = '-- %-30s -------------'
print(line % 'Computing passes')

pr = cProfile.Profile()
pr.enable()
tree = compute_all_passes(stations,
                          sats,
                          start_time,
                          duration=duration,
                          dbfile=dbfile,
                          nprocesses=1,
                          function=compute_function)
pr.disable()
pr.print_stats(sort='time')
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
    treeload = load_all_passes(dbfile)


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
