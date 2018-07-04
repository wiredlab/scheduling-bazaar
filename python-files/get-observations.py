#!/usr/bin/env python3

"""
Utility to get observations from a SatNOGS Network server.

Collects the paginated objects into a single JSON list and stores in a file.
"""

import json
import requests


OBSERVATIONS_API = 'https://network.satnogs.org/api/observations'
OBSERVATIONS_JSON = 'observations.json'


def get(url):
    print(url)
    return requests.get(url)

observations = []
r = get(OBSERVATIONS_API)
# r = requests.get(OBSERVATIONS_API)

observations.extend(r.json())
nextpage = r.links.get('next')

while nextpage:
    # r = requests.get(nextpage['url'])
    r = get(nextpage['url'])
    observations.extend(r.json())
    nextpage = r.links.get('next')

observations = sorted(observations, key=lambda s: s['id'])

with open(OBSERVATIONS_JSON, 'w') as fp:
    json.dump(observations, fp, sort_keys=True, indent=2)

