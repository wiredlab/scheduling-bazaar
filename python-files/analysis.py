# standard analysis function
def standard_analysis(clients):
    results = {}
    for c in clients:
        results[c.name] = client_results(c)
    return results


def client_results(client):
    c_results = {}
    c_results['daily_sat_access'] = client.daily_busy_time()
    c_results['total_busy_time'] = client.busy_time()
    return c_results

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
    import seaborn
    import matplotlib.pyplot as plt
    spd = 86400  # seconds/day

    fig = plt.figure(1)
    if client is None and sat is not None:
        fig.suptitle('%s Access Time for All Ground Stations' % (sat))
    elif sat is None and client is not None:
        fig.suptitle('All Satellite Access Time for %s Ground Station' % (client))
    elif sat is None and client is None:
        fig.suptitle('All Satellite Access time for All Ground Stations')
    else:
        fig.suptitle('%s Access time for %s Ground Station' % (sat, client))

    s1 = plt.subplot()
    s1.plot(daily_totals, 'b-')
    s1.set_ylim(ymin=0, ymax=spd)
    plt.xlabel('Days from Epoch')
    plt.ylabel('Busy time (sec/day)')

    #s2 = plt.subplot(222)
    #s2.plot(daily_totals, 'b-')
    #s2.set_ylim(ymin=0, ymax=ymax)
    #plt.xlabel('Days from Epoch')

    plt.show()

## calc_access_time() function definition
#def calc_access_time(passtree):
#   """Calculates Access Time in seconds/day.

#   Arguments:
#   passtree - interval tree containing all intervals for access time
#   """
#   # Find total access time for tree
#   #     Including: one gs tree, one sat tree, one gs/one sat tree
#   accesstime_total = 0
#   for item in passtree:
#       accesstime_total = accesstime_total + item.data.duration


#   # Find access time per day for tree
#   if len(passtree) > 0:

#       # Including: one gs tree, one sat tree, one gs/one sat tree
#       start, end = passtree.begin(), passtree.end()

#       # get day of first pass, start at midnight
#       q = start.replace(hour=0, minute=0, second=0, microsecond=0)

#       # get day of last pass, end at midnight
#       c = end.replace(hour=0, minute=0, second=0, microsecond=0)

#       # define one day as timedelta
#       day = datetime.timedelta(days=1)

#       accesstime_days = []
#       while q <= c:
#           dayend = q + day

#           # TODO: chop bug workaround
#           try:
#               new_tree = passtree.search(q, dayend)
#               new_tree.chop(q, dayend)
#           except:
#               new_tree = passtree.search(q, dayend)
#               # accept the overhangs

#           access = 0
#           for item in new_tree:
#               access = access + item.data.duration
#           accesstime_days.append(access)
#           q = dayend

#   return accesstime_total, accesstime_days
