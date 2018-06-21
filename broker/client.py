

from collections import defaultdict
from datetime import timedelta

from intervaltree import Interval, IntervalTree
from iso8601 import parse_date





class BaseClient:
    """Base class to represent a SatNOGS client.  Subclasses implement the
    various ways a client accepts Requests or independently generates Offers.

    calendar - an IntervalTree of accepted/scheduled requests
    """
    def __init__(self, name, lat=None, lon=None, alt=None):
        if isinstance(name, dict):
            self.name = name['name']
            self.lat = name['lat']
            self.lon = name['lon']
            self.alt = name['alt']
            self.data = name
        else:
            self.name = name
            self.lat = float(lat)
            self.lon = float(lon)
            self.alt = float(alt)

        self.calendar = IntervalTree()

    def __str__(self):
        """Return a better string than __repr__() for humans to read."""
        return ('%s (%s lat=%.2f, lon=%.2f, alt=%.2f)'
                % (self.__class__.__name__,
                   self.name, self.lat, self.lon, self.alt))

    def request(self, r):
        """Takes a Request object (dict) for a potential Job.

        Returns an Offer object.

        Must be implemented in a subclass.
        """
        raise NotImplemented('Cannot directly use the BaseClient class.')

    def calendar_value(self, start=None, end=None):
        """Returns a dict of the total potential bounties offered for the
        scheduled jobs during the requested range.  Default to the entire
        range.
        """
        calendar_range = self._choprange(start, end)
        value = defaultdict(float)
        for i in calendar_range:
            bounties = i.data['bounty']
            for unit in bounties:
                value[unit['currency']] += unit['amount']
        return value

    def calendar_begin(self):
        """Returns start time of first job in calendar."""
        return self.calendar.begin()

    def calendar_end(self):
        """Returns end time of last job in calendar."""
        return self.calendar.end()

    def _choprange(self, start=None, end=None):
        """Helper to return a sub IntervalTree chopped to the given range.
        """
        # IntervalTree doesn't behave well when searching zero-length tress
        if len(self.calendar) == 0:
            return self.calendar
        b = self.calendar.begin()
        e = self.calendar.end()
        if start is not None:
            if isinstance(start, Interval):
                b = start.begin
                e = start.end
            else:
                b = start

            if end is not None:
                e = end
        # get trimmed intervals in requested range
        # .search() returns a set()
        iv = IntervalTree(self.calendar.search(b, e))
        # the following should work, but chop() is having issues with chopping
        # too much (all the way to zero!)
        # iv.chop(b, e)  # <--- whuzzup??
        # cheat and expand the chop interval by a microsecond on each side
        # iv.chop(b - timedelta(seconds=1), e + timedelta(seconds=1))
        # ^^^ still doesn't work.
        # TODO: fix iv.chop()
        # Just return the searched interval and not trim the ends
        return iv

    def busy_time(self, start=None, end=None):
        """Returns the total time in seconds of scheduled jobs during the
        given range.  Defaults to the entire range.
        """
        total = timedelta(0)
        iv = self._choprange(start, end)
        for r in iv:
            s = parse_date(r.data['job']['start'])
            e = parse_date(r.data['job']['end'])
            diff = e - s
            total += diff
        return total.total_seconds()

    def daily_busy_time(self, start=None, end=None):
        """Returns the total time in seconds of scheduled jobs per day
        during the given range. Defaults to the entire range.
        """
        start = self.calendar_begin()
        end = self.calendar_end()
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = end.replace(hour=0, minute=0, second=0, microsecond=0)
        oneday = timedelta(days=1)
        busy_time_days = []
        while start <= end:  # we want the thru the end of this day
            dayend = start + oneday
            sec = self.busy_time(start, dayend)
            busy_time_days.append(sec)
            start = dayend
        return busy_time_days


class AllClient(BaseClient):
    """Represents a SatNOGS client which implements the SatNOGS-Broker
    interface.

    This one always accepts all jobs unconditionally.  It represents the
    maximum performance Client that can receive horizon-to-horizon and with an
    arbitrary number of simultaneous receivers.
    """
    def request(self, r):
        job = r['job']
        bounty = r['bounty']

        start = parse_date(job['start'])
        end = parse_date(job['end'])

        ri = Interval(start, end, r)

        self.calendar.add(ri)
        offer = {'status': 'accept',
                 'job': job,
                 'fee': bounty}
        return offer


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

    #
    # send request to client, get an offer in response
    # (no checking against satellite visibility, only checks times
    # for overlaps)
    offer = client.request(r)
    assert offer['status'] == 'accept'  # verify expected response
    print('Offer:', offer)

    #
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
    print('Offer2:', offer2)

    #
    # third offer with start/end times that do not overlap
    # client accepts this one
    j3 = j.copy()
    j3['start'] = '2017-07-13T20:45:00Z'
    j3['end'] = '2017-07-13T20:51:30Z'
    r3 = r.copy()
    r3['job'] = j3

    offer3 = client.request(r3)
    assert offer['status'] == 'accept'
    print('Offer3:', offer3)

    # ask client for the total value of all its scheduled jobs
    print('\nTotal scheduled value:')
    print(client.calendar_value())

    # ask client for the total duration of scheduled jobs
    print('\nTotal job duration:')
    print(client.busy_time())
