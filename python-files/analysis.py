# calc_access_time() function definition
def calc_access_time(passtree):
    """Calculates Access Time in seconds/day.

    Arguments:
    passtree - interval tree containing all intervals for access time
    """
    # Find total access time for tree
    #     Including: one gs tree, one sat tree, one gs/one sat tree
    accesstime_total = 0
    for item in passtree:
        accesstime_total = accesstime_total + item.data.duration


    # Find access time per day for tree

    # Including: one gs tree, one sat tree, one gs/one sat tree
    start, end = passtree.begin(), passtree.end()

    # get day of first pass, start at midnight
    q = start.replace(hour=0, minute=0, second=0, microsecond=0)

    # get day of last pass, end at midnight
    c = end.replace(hour=0, minute=0, second=0, microsecond=0)

    # define one day as timedelta
    day = datetime.timedelta(days=1)

    accesstime_days = []
    while q <= c:
        dayend = q + day

        # TODO: chop bug workaround
        try:
            new_tree = passtree.search(q, dayend)
            new_tree.chop(q, dayend)
        except:
            new_tree = passtree.search(q, dayend)
            # accept the overhangs

        access = 0
        for item in new_tree:
            access = access + item.data.duration
        accesstime_days.append(access)
        q = dayend

    return accesstime_total, accesstime_days
