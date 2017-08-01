# This file contains the different scheduling method definitions to be used
# when simulating.


def random_scheduler(passes, clients, debug=False):
    """Randomly schedules passes on the given clients (which are already
    instantiated with the desired client type).

    passes - candidate passes for scheduling.
    clients - dict of ground stations to use.
    debug - Boolean, defualt False. Will print out status markers for each
            pass when True.
    """

    passes = random.sample(passes, len(passes))
    for pd in passes:
        # create a request
        r = pass2request(pd)
        offer = clients[pd.data.gs].request(r)
        if debug is True:
            if offer['status'] == 'accept':
                print('*', end='', flush=True)
            else:
                print('.', end='', flush=True)
    return clients


# def max_gs_el(passes, clients, debug=False):


# def max_sat_el(passes, clients, debug=False):
