# standard analysis function
def standard_analysis(clients):
    results = {}
    for c in clients:
        results[c.name] = # another function for calling all analyses?
    return results


def standard_plots(results):
    """Generate a canonical (large) figure which shows the normal plots
    that are of interest
    """


def daily_busy_time(name=None, clients=None, sats=None):
    #find the time range over which we should loop our days.
    firstday = min([c.begin() for c in clients])
    lastday = max([c.end() for c in clients])

    firstday = firstday.replace(hours=0, minutes=0, seconds=0, microseconds=0)
    lastday = lastday.replace(hours=0, minutes=0, seconds=0, microseconds=0)
    oneday = timedelta(days=1)

    days = []
    times = []
    day = firstday
    while day < lastday:
        #handle name=None? or force a value?
        c = clients[name]
        times.append(c.busy_time(day, day + oneday))
        # only create the days element if the prev line doesn't barf
        days.append(day)  #for our x-axis
        day += oneday
    return (days, times)




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

