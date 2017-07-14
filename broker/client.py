

from collections import defaultdict
from collections import namedtuple

from intervaltree import Interval, IntervalTree
from iso8601 import parse_date


# NOTE:
# the namedtuple stuff and the two converters are not likely to stay
#
JobTuple = namedtuple('JobTuple', ['id', 'start', 'end', 'ground_station',
                                   'tle0', 'tle1', 'tle2', 'frequency',
                                   'mode', 'transmitter'])

RequestTuple = namedtuple('RequestTuple',
                          ['id', 'start', 'end', 'ground_station',
                           'tle0', 'tle1', 'tle2', 'frequency',
                           'mode', 'transmitter'])


def dict2tuple(tupletemplate, d):
    return tupletemplate(**d)


def tuple2dict(t):
    return t._asdict()


class BaseClient:
    """Base class to represent a SatNOGS client.  Subclasses implement the
    various ways a client accepts Requests or independently generates Offers.

    calendar - an IntervalTree of accepted/scheduled requests
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
    already scheduled job.  It does no other sanity checking of the request
    data.
    """
    def request(self, r):
        job = r['job']
        bounty = r['bounty']

        start = parse_date(job['start'])
        end = parse_date(job['end'])

        ri = Interval(start, end, r)

        overlaps = self.calendar.search(ri)

        if len(overlaps) == 0:
            self.calendar.add(ri)
            offer = {'status': 'accept',
                     'job': job,
                     'fee': bounty}
        else:
            offer = {'status': 'reject',
                     'reason': 'time overlap',
                     'extra': [o.data for o in overlaps]}
        return offer


# testing the implementation
if __name__ == '__main__':
    # build job
    # taken directly from https://network.satnogs.org/api/jobs
    j = {'id': 9247,
         'start': '2017-07-12T20:42:06Z',
         'end': '2017-07-12T20:51:30Z',
         'ground_station': 12,
         'tle0': 'XW-2D',
         'tle1': '1 40907U 15049J   17192.53573606  .00000798  00000-0  46540-4 0  9991',  # noqa
         'tle2': '2 40907  97.4515 197.2956 0016027 124.7938 235.4805 15.14668467 99926',  # noqa
         'frequency': 145855000,
         'mode': 'CW',
         'transmitter': 'V76m6YW7nVsTrgCboMVHEb'
         }

    b = [{'currency': 'SNC', 'amount': 10.0}]

    # a complete request for a job
    r = {'job': j,
         'bounty': b,
         }

    # Create a client
    client = YesClient('VU-1', 41.4639, -87.0439, 245)


    # send request to client, get an offer in response
    # (no checking against satellite visibility, only checks times
    # for overlaps)
    offer = client.request(r)
    assert offer['status'] == 'accept'  # verify expected response
    print(offer)


    # create a second offer
    # sets start to a time inside of the last one
    # client should reject because it overlaps with a scheduled job
    j2 = j.copy()  # make new dict with same info
    j2['start'] = '2017-07-12T20:45:00Z'  # just replace one value
    r2 = r.copy()
    r2['job'] = j2

    # send request
    offer2 = client.request(r2)
    assert offer2['status'] == 'reject'
    print(offer2)


    # third offer with start/end times that do not overlap
    # client accepts this one
    j3 = j.copy()
    j3['start'] = '2017-07-13T20:45:00Z'
    j3['end'] = '2017-07-13T20:51:30Z'
    r3 = r.copy()
    r3['job'] = j3

    offer3 = client.request(r3)
    assert offer['status'] == 'accept'
    print(offer3)

    # ask client for the total value of all its scheduled jobs
    print('Total scheduled value:')
    print(client.calendar_value())
