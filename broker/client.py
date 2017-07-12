

from collections import defaultdict
from collections import namedtuple
from datetime import datetime, timezone

from intervaltree import Interval, IntervalTree


# NOTE:
# the namedtuple stuff and the two converters are not likely to stay
#
JobTuple = namedtuple('JobTuple', ['id', 'start', 'end', 'ground_station',
                                   'tle0', 'tle1', 'tle2', 'frequency',
                                   'mode', 'transmitter'])

RequestTuple = namedtuple('RequestTuple', ['id', 'start', 'end', 'ground_station',
                                   'tle0', 'tle1', 'tle2', 'frequency',
                                   'mode', 'transmitter'])

def dict2tuple(tupletemplate, d):
    return tupletemplate(**d)


def tuple2dict(t):
    return t._asdict()



def rfc3339_to_dt(s):
    d = datetime.strptime(s, '%Y-%m-%dT%H:%M:%SZ')
    d = d.replace(tzinfo=timezone.utc)
    return d


class BaseClient:
    """Base class to represent a SatNOGS client.  Subclasses implement the
    various ways a client accepts Requests or independently generates Offers.
    """
    def __init__(self, name, lat, lon, alt):
        self.name = name
        self.lat = lat
        self.lon = lon
        self.alt = alt
        self.calendar = IntervalTree()

    def request(self, r):
        """Takes a Request object (dict) for a potential Job.

        Returns an Offer object.

        Must be implemented in a subclass.
        """
        raise NotImplemented('Cannot directly use the BaseClient class.')

    def calendar_value(self):
        """Returns a dict of the total potential bounties offered for the
        scheduled jobs.
        """
        value = defaultdict(float)
        for i in self.calendar:
            bounties = i.data['bounty']
            for unit in bounties:
                value[unit['currency']] += unit['amount']
        return value


class YesClient(BaseClient):
    """Represents a SatNOGS client which implements the SatNOGS-Broker
    interface.

    This one always accepts a requested job if it doesn't overlap with an
    already scheduled job.
    """
    def request(self, r):
        job = r['job']
        bounty = r['bounty']

        start = rfc3339_to_dt(job['start'])
        end = rfc3339_to_dt(job['end'])

        ri = Interval(start, end, r)

        overlaps = self.calendar.search(ri)

        if len(overlaps) == 0:
            self.calendar.add(ri)
            return {'status': 'accept'}
        else:
            return {'status': 'reject',
                    'reason': 'time overlap',
                    'extra': [o.data for o in overlaps]}


# testing the implementation
if __name__ == '__main__':
    j = {'id': 9247,
         'start': '2017-07-12T20:42:06Z',
         'end': '2017-07-12T20:51:30Z',
         'ground_station': 12,
         'tle0': 'XW-2D',
         'tle1': '1 40907U 15049J   17192.53573606  .00000798  00000-0  46540-4 0  9991',
         'tle2': '2 40907  97.4515 197.2956 0016027 124.7938 235.4805 15.14668467 99926',
         'frequency': 145855000,
         'mode': 'CW',
         'transmitter': 'V76m6YW7nVsTrgCboMVHEb'
        }

    b = [{'currency': 'SNC', 'amount': 10.0}]

    r = {'job': j,
         'bounty': b,
         }

    client = YesClient('VU-1', 41.4639, -87.0439, 245)
    offer = client.request(r)
    print(offer)

    j2 = j.copy()
    j2['start'] = '2017-07-12T20:45:00Z'
    r2 = r.copy()
    r2['job'] = j2

    offer2 = client.request(r2)
    print(offer2)

    j3 = j.copy()
    j3['start'] = '2017-07-13T20:45:00Z'
    j3['end'] = '2017-07-13T20:51:30Z'
    r3 = r.copy()
    r3['job'] = j3

    offer3 = client.request(r3)
    print(offer3)

    print()
    print(client.calendar_value())
