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


try:
    with open(OBSERVATIONS_JSON) as f:
        data = json.load(f)
        # json.dump() coerces to string keys
        # convert keys back to integers
        observations = {}
        for k,v in data.items():
            print(k)
            observations[int(k)] = v
        # observations = {v['id']:v for k,v in data.items()}
except IOError:
    observations = {}



def update(o, observations):
    o_id = o['id']
    print(o_id)
    if o_id not in observations:
        observations[o_id] = o
        was_new = True
    else:
        observations.update(o)
        was_new = False
    return was_new


r = get(OBSERVATIONS_API)
updated = [update(o, observations) for o in r.json()]
any_updated = any(updated)

nextpage = r.links.get('next')
while any_updated and nextpage:
    r = get(nextpage['url'])
    updated = [update(o, observations) for o in r.json()]
    print(updated)
    any_updated = any(updated)
    if any_updated:
        nextpage = r.links.get('next')

with open(OBSERVATIONS_JSON, 'w') as fp:
    json.dump(observations, fp, sort_keys=True, indent=2)
