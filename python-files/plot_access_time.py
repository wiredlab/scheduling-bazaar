import ephem

import matplotlib.pyplot as plt


def plot_access_time(start, gs, tle):
    """Plots Access Time in seconds/day.

    Arguments:
    start -- string formatted 'yyyy/mm/dd HH:MM:SS'
    gs -- 4 element list containing desired [name,lat,lon,alt]
    tle -- 3 element list containing desired tle [line0,line1,line2]
    """
    year = 365
    start_time = ephem.date(start)
    access_list = []
    day_list = []

    for days in range(year):
        num_passes = None
        duration = 24.0
        gs_passes = {}
        noradID = tle[2][2:7]

        gs_passes[noradID] = new_get_passes(gs, tle, start_time, num_passes=num_passes, duration=duration)

        access_time = 0
        for sat, passes in gs_passes.items():
            for obs in passes:
                access_time = access_time + obs['duration']
        access_list.append(access_time)
        day_list.append(days)
        start_time = start_time + 1

    plt.figure(1)

    plt.subplot(221)
    plt.plot(day_list, access_list, 'b.')
    plt.title('%s Access time for %s GS' % (noradID, gs[0]))
    plt.xlabel('Days from %s' % (start))
    plt.ylabel('Access time (sec/day)')

    plt.subplot(222)
    plt.plot(day_list, access_list, 'b-')
    plt.title('%s Access time for %s GS' % (noradID, gs[0]))
    plt.xlabel('Days from %s' % (start))
    plt.ylabel('Access time (sec/day)')

    plt.show()
