# This file contains the different scheduling method definitions to be used
# when simulating.
import random



class Scheduler:
    """Base class for schedulers.  Inherit and implement __call__."""
    def __init__(self, clients, satellites, passes=None, debug=False):
        """Store dicts of clients and satellites for use later.
        Do the scheduling if passes is given.
        """
        self.clients = clients
        self.satellites = satellites
        self.passes = passes
        self.debug = debug
        if passes is not None:
            self(passes)

    def __call__(self, passes):
        raise NotImplementedError

    def do_request(self, pd):
        """Helper to take a PassTuple and make a request to the relevant client."""
        r = pass2request(pd, self.satellites)
        offer = self.clients[pd.data.gs].request(r)
        if self.debug:
            if offer['status'] == 'accept':
                print('*', end='', flush=True)
            else:
                print('.', end='', flush=True)
        return offer


class RandomScheduler(Scheduler):
    """Make requests in random order."""
    def __call__(self, passes):
        passes = random.sample(passes, len(passes))
        for pd in passes:
            self.do_request(pd)
        return self.clients


class FirstScheduler(Scheduler):
    """Make requests in order of start time."""
    def __call__(self, passes):
        for pd in sorted(passes, key=lambda p: p.begin):
            self.do_request(pd)


class LastScheduler(Scheduler):
    """Make requests by end time, starting with the last pass."""
    def __call__(self, passes):
        for pd in sorted(passes, key=lambda p: p.end, reverse=True):
            self.do_request(pd)


class DurationScheduler(Scheduler):
    """Order requests by duration of passes."""
    def __call__(self, passes):
        for pd in sorted(passes, key=lambda p: (p.end - p.begin), reverse=True):
            self.do_request(pd)


class EndStartScheduler(Scheduler):
    """Should be same result as FirstScheduler."""
    def __call__(self, passes):
        now = passes.begin()
        last = passes.end()
        while now < last:
            tree = passes.search(now, last, strict=True)
            s = sorted(tree, key=lambda i: i.begin)
            if len(s) == 0:
                break
            pd = s[0]
            self.do_request(pd)
            now = pd.end




def pass2request(pd, satellites):
    """Take a pass (as returned from db.getpasses() and construct a request
    dict for the Network to send to a Client.

    The bounty is SNC (SatNOGS Credits) with an amount set to the pass duration
    in seconds.

    When transmitted over a network, this is then converted to JSON.
    """

    d = pd.data
    job = {'id': random.randrange(2**16),  # fake an ID number
           'start': d.start.isoformat(),
           'end': d.end.isoformat(),
           'ground_station': d.gs,
           'tle0': satellites[d.norad]['tle'][0],
           'tle1': satellites[d.norad]['tle'][1],
           'tle2': satellites[d.norad]['tle'][2],
           'frequency': -1,
           'mode': 'null',
           'transmitter': 'asdfasdasdfadsf',
           }
    duration = (d.end - d.start).total_seconds()
    bounty = [{'currency': 'SNC', 'amount': duration}]

    request = {'job': job,
               'bounty': bounty,
               'status': 'initial',
               }
    return request


