# This file contains the different scheduling method definitions to be used
# when simulating.
from collections import defaultdict
import random

from intervaltree import IntervalTree


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
    """Should be exactly the same result as FirstScheduler.
    Here just as an example of using features of the passes IntervalTree class."""
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


class OwnerPreferenceScheduler(Scheduler):
    """Select passes based on list of sats sorted by priority."""
    def __init__(self, clients, satellites, priority={}, passes=None, debug=False):
        self.priority = priority
        super().__init__(clients, satellites, passes=passes, debug=debug)

    def __call__(self, passes):
        # go down list of priority sats
        # if in passes, schedule it
        # remove all overlapping passes

        # construct separate trees for individual GSs
        gstree = {gs:IntervalTree() for gs in self.priority.keys()}
        othertree = IntervalTree()
        sattree = {gs:defaultdict(list) for gs in self.priority.keys()}
        for pd in passes:
            if pd.data.gs in gstree:
                gstree[pd.data.gs].add(pd)
                # easy access to participating sats
                sattree[pd.data.gs][pd.data.norad].append(pd)
            else:
                othertree.add(pd)

        # collapse the trees by priority
        for gs, tree in gstree.items():
            for norad in self.priority[gs]:
                # remove passes which overlap with a priority sat's pass
                # Alternate is to first request these passes, then let the
                # Client reject later requests which overlap, but this would
                # burn much network overhead.
                for pd in sattree[gs][norad]:
                    # pass could have already been removed, so check first
                    if pd in tree:
                        tree.remove_overlap(pd)
                        # add back the pass in question
                        tree.add(pd)

        # TODO: have a hierarchy of Schedulers
        #       what should the strategy be for the remaining overlaps?
        #
        # Each scheduler in the list runs in order.
        # Passes remaining (not scheduled and also not removed by earlier) are
        # sent to the following scheduler.
        #   ( OwnerPreferenceScheduler(config),
        #     NextScheduler(config2),
        #     FinalScheduler(config3),
        #   )

        # TODO: idea
        #   Each of these operates as a filter to deal with overlaps.
        #   maybe use own version of IntervalTree.merge_overlaps(datafunc)

        # Schedule passes on GSs without priorities by first start
        for pd in sorted(othertree, key=lambda p: p.begin):
            self.do_request(pd)

        # Schedule passes on GS with preferences using the pruned trees
        for gs, tree in gstree.items():
            for pd in sorted(tree, key=lambda p: p.begin):
                self.do_request(pd)






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


