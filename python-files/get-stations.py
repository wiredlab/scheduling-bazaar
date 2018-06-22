#!/usr/bin/env python3

"""
Utility to get the station information from a SatNOGS Network server.

Collects the paginated objects into a single JSON list and stores in a file.
"""

import json
import requests


NETWORK = 'https://network.satnogs.org/api/stations'
STATIONS_JSON = 'network-stations.json'


stations = []
r = requests.get(NETWORK)

stations.extend(r.json())
nextpage = r.links.get('next')

while nextpage:
    r = requests.get(url=nextpage['url'])
    stations.extend(r.json())
    nextpage = r.links.get('next')

stations = sorted(stations, key=lambda s: s['id'])

with open(STATIONS_JSON, 'w') as fp:
    json.dump(stations, fp)

