#!/usr/bin/env python3

"""
Utility to get observations from a SatNOGS Network server.

Collects the paginated objects into a single JSON mapping keyed by observation id
and stores in a file.
"""

import gzip
import json
import requests

import pprint
print = pprint.pprint

# just for developing script
# import requests_cache
# requests_cache.install_cache(expire_after=60*60)

OBSERVATIONS_API = 'https://network.satnogs.org/api/observations'
OBSERVATIONS_JSON = 'observations.json.gz'

MAX_EXTRA_PAGES = 50

client = requests.session()
def get(url):
    print(url)
    return client.get(url)


if OBSERVATIONS_JSON.endswith('.gz'):
    with gzip.open(OBSERVATIONS_JSON) as f:
        data = json.load(f)
        # json.dump() coerces to string keys
        # convert keys back to integers
        observations = {}
        for k,v in data.items():
            observations[int(k)] = v
else:
    with open(OBSERVATIONS_JSON) as f:
        data = json.load(f)
        # json.dump() coerces to string keys
        # convert keys back to integers
        observations = {}
        for k,v in data.items():
            observations[int(k)] = v


def update(o, observations):
    o_id = int(o['id'])
    was_updated = False
    if o_id not in observations:
        print('%i new' % o_id)
        observations[o_id] = o
        was_updated = True

    elif o.get('detail'):
        print('%i was deleted' % o_id)
        del obs[o_id]

    elif o != observations[o_id]:
        # get symmetric difference
        # ignore user-updated keys: 'station_*'
        #
        # converting to a 'k: v' string is a hack around ignorance...
        orig = tuple(['%s: %s' % (k,v) for k,v in observations[o_id].items() if not k.startswith('station')])
        new = tuple(['%s: %s' % (k,v) for k,v in o.items() if not k.startswith('station')])
        orig = set(orig)
        new = set(new)
        diff = orig ^ new

        if len(diff) > 0:
            print('%i different data' % o_id)
            print(diff)
            observations[o_id] = o
            was_updated = True

    return was_updated


r = get(OBSERVATIONS_API)
updated = [update(o, observations) for o in r.json()]
any_updated = any(updated)

nextpage = r.links.get('next')
extra_pages = MAX_EXTRA_PAGES

while (extra_pages > 0) and nextpage:
    r = get(nextpage['url'])
    updated = [update(o, observations) for o in r.json()]
    # print(updated)

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


# try to fetch old obs with no vetting
for o_id, o in sorted(obs.items(), reverse=True):
    break
    if o['vetted_status'] == 'unknown':
        r = get(OBSERVATIONS_API + '/' + str(o_id))
        d = r.json()
        if d != o:
            if d.get('detail'):
                print('%i was deleted' % o_id)
                del obs[o_id]
            else:
                print('%i updated' % o_id)
                obs[o_id] = d


if OBSERVATIONS_JSON.endswith('.gz'):
    with gzip.open(OBSERVATIONS_JSON, 'wt') as fp:
        json.dump(obs, fp, sort_keys=True, indent=2)
else:
    with open(OBSERVATIONS_JSON, 'w') as fp:
        json.dump(obs, fp, sort_keys=True, indent=2)
