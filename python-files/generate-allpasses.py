#!/usr/bin/env python3

from itertools import product
import pickle
import sys
import time

from schedulingbazaar import (load_tles,
                              load_gs,
                              compute_all_passes,
                              load_all_passes)


sats = load_tles('amateur.txt')
stations = load_gs('groundstations.txt')

start_time = '2017/6/8 00:00:00'
# duration = 8760 #a year worth of hours
duration = 3

line = '-- %-30s -------------'
print(line % 'Computing passes')
tree = compute_all_passes(stations[:3],
                          sats[:3],
                          start_time,
                          duration=duration,
                          dbfile='somepasses.db')

# give the filesystem some time to finish closing the database file
time.sleep(1)

print(line % 'Save/load as pickle')
pickle.dump(tree, open('somepasses.pkl', 'wb'))
time.sleep(1)
treepkl = pickle.load(open('somepasses.pkl', 'rb'))

print(line % 'Load from db')
treeload = load_all_passes('somepasses.db')


print(line % 'All diffs should be empty')
trees = (tree, treepkl, treeload)
nfail = 0
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
