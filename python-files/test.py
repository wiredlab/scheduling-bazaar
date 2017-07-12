

import pickle
import time

from schedulingbazaar import *


sats = load_tles('amateur.txt')
stations = load_gs('groundstations.txt')

start_time = '2017/6/8 00:00:00'
# duration = 8760 #a year worth of hours
duration = 3

line = '-- %-20s -------------'
print(line % 'Computing passes')
tree = compute_all_passes(stations[:3], sats[:3], start_time, duration=duration,
                          dbfile='somepasses.db')

# give the filesystem some time to finish closing the database file
time.sleep(1)

print(line % 'Saving as pickle')
pickle.dump(tree, open('somepasses.pkl','wb'))

treepkl = pickle.load(open('somepasses.pkl', 'rb'))


print(line % 'Verifying')
treeload = load_all_passes('somepasses.db')


print(line % 'Difference should be empty')
print(tree.difference(treeload))


