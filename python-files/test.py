#!/usr/bin/env python3

from itertools import product
import pickle
import random
import time

from schedulingbazaar import load_gs, load_tles
from db import compute_all_passes, load_all_passes, getpasses




def test_saveload():
    stations = load_gs('groundstations.txt')
    print(len(stations))
    sats = load_tles('amateur.txt')
    print(len(sats))

    start_time = '2017/6/8 00:00:00'
    # duration = 8760 #a year worth of hours
    duration = 24*3

    NSTATIONS = 4
    NSATS     = 4

    line = '-- %-20s -------------'
    print(line % 'Computing passes')
    tree = compute_all_passes(random.sample(stations, NSTATIONS),
                            random.sample(sats, NSATS),
                            start_time,
                            duration=duration,
                            dbfile='somepasses.db')

    print('Found %i passes' % len(tree))

    # give the filesystem some time to finish closing the database file
    time.sleep(1)

    print(line % 'Saving as pickle')
    pickle.dump(tree, open('somepasses.pkl','wb'))

    treepkl = pickle.load(open('somepasses.pkl', 'rb'))


    print(line % 'Verifying')
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


if __name__ == '__main__':
    test_saveload()
# print()
# t = [i for i in tree]
# tp= [i for i in treepkl]
# tl = [i for i in treeload]
# print(t[0])
# print()
# print(tl[0])

