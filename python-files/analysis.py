# plot_access_time() function definition
def plot_busy_time(daily_totals, client=None, sat=None):
    """Plots Busy Time in seconds/day.

    Arguments:
    daily_totals - list of daily sec/day
    client - Name of gs used for passes (default None)
    sat - Name of sat used for passes (default None)

    If both client and sat specified, one client/sat combo
    If client not specified, means one sat all client
    If sat not specified, means one client all sats
    If neither, use generic "client" and "sat"
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
