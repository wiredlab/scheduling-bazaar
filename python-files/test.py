

import pickle
import time

from schedulingbazaar import *


sats = load_tles('amateur.txt')
stations = load_gs('groundstations.txt')

start_time = '2017/6/8 00:00:00'
duration = 8760 #a year worth of hours
# duration = 3

line = '-- %-20s -------------'
print(line % 'Computing passes')
tree = compute_all_passes(stations, sats, start_time, duration=duration,
                          dbfile='allpasses.db')

time.sleep(1)

print(line % 'Saving as pickle')
pickle.dump(tree, open('allpasses.pkl','wb'))


print(line % 'Verifying')
tree2 = load_all_passes('allpasses.db')


print(line % 'Difference should be empty')
print(tree.difference(tree2))
del tree2


