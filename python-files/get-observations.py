#!/usr/bin/env python3

"""
Utility to get observations from a SatNOGS Network server.

Collects the paginated objects into a single JSON mapping keyed by observation id
and stores in a file.
"""

import json
import requests

# uncomment this when testing the script and not getting new data
# import requests_cache
# requests_cache.install_cache(expire_after=60*60*3)

OBSERVATIONS_API = 'https://network.satnogs.org/api/observations'
OBSERVATIONS_JSON = 'observations.json'

MAX_EXTRA_PAGES = 10

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
            observations[int(k)] = v
except IOError:
    observations = {}


def update(o, observations):
    o_id = int(o['id'])
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
extra_pages = MAX_EXTRA_PAGES

while (extra_pages > 0) and nextpage:
    r = get(nextpage['url'])
    updated = [update(o, observations) for o in r.json()]
    print(updated)

    nextpage = r.links.get('next')

    # heuristic to capture recent updates to observations
    # keep fetching pages of observations until we see
    # MAX_EXTRA_PAGES in a row with no updates
    if not any(updated):
        extra_pages -= 1
    else:
        extra_pages = MAX_EXTRA_PAGES
    print(extra_pages)


# filter out the bad data
obs = {k:v for k,v in observations.items() if isinstance(v, dict)}

with open(OBSERVATIONS_JSON, 'w') as fp:
    json.dump(obs, fp, sort_keys=True, indent=2)
