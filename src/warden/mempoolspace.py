from datetime import datetime
from embit import bip32, script
from embit.networks import NETWORKS
import requests
import threading
import pandas as pd
from utils import pickle_it
from connections import tor_request


# Creates a list of URLs and names for the public and private addresses
def server_names(action=None, url=None, name=None, public=True):
    # Sample list_all output:
    # [
    #   ('http://raspberrypi.local:4080/', 'RaspiBlitz Home', False),
    #   ('http://mempool.space/', 'mempool.space', True),
    #   ('http://mempoolhqx4isw62xs7abwphsq7ldayuidyx2v2oethdhhj6mlo2r6ad.onion/', 'mempool.space [onion]', True)
    # ]

    # These are already known names and urls for public mempoolspace servers
    known_names = [
        ('http://mempool.space/', 'mempool.space', True),
        ('http://mempoolhqx4isw62xs7abwphsq7ldayuidyx2v2oethdhhj6mlo2r6ad.onion/',
         'mempool.space [onion]', True),
    ]
    custom_names = pickle_it('load', 'mps_custom_names.pkl')

    # If the file does not exist, add the standard names above
    if custom_names == 'file not found':
        custom_names = known_names
        pickle_it('save', 'mps_custom_names.pkl', custom_names)

    if action == None or action == 'list_all' or action == 'list':
        return custom_names

    # get a name from url
    if action == 'get':
        for element in custom_names:
            if element[0] == url:
                return element[1]
        return "Unknown"

    if action == 'get_info':
        for element in custom_names:
            if element[0] == url:
                return element
        return "Unknown"

    # add name to url (actually it's an add or replace if exists)
    # so add = edit
    if action == 'add':
        # check if exists, if so, remove
        for st in custom_names:
            if st[0] == url:
                custom_names.remove(st)
        name = 'Unknown' if name == None else name
        custom_names.append((url, name, public))
        pickle_it('save', 'mps_custom_names.pkl', custom_names)
        return

    # Remove name from list
    if action == 'delete' or action == 'remove':
        for st in custom_names:
            try:
                if st[0] == url:
                    status = st
                    status['online'] = False
                    custom_names.remove(st)
                    custom_names.append(status)
            except Exception:
                pass
        # Save pickle

    pickle_it('save', 'mps_custom_names.pkl', custom_names)

    return custom_names


# Creates background thread to check all servers
def check_all_servers():
    mp_addresses = server_names()
    urls = [i[0] for i in mp_addresses]

    threads = []
    for url in urls:
        threads.append(threading.Thread(target=check_api_health, args=[url]))

    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()


def is_synched(url):
    endpoint = 'api/block-height/'
    max_tip = pickle_it('load', 'max_tip_height.pkl')
    if max_tip == 'file not found':
        max_tip = 100
    result = tor_request(url + endpoint + str(max_tip))
    try:
        r = result.text
    except Exception:
        return False
    bad_response = 'Block height out of range'
    if r == bad_response:
        return False
    else:
        return True


# Returns the highest block height in all servers
def get_max_height():
    # Load server list from pickle
    server_list = pickle_it('load', 'mps_server_status.pkl')

    max_tip_height = pickle_it('load', 'max_tip_height.pkl')
    if max_tip_height == 'file not found':
        max_tip_height = 0

    for server in server_list:
        try:
            tip = int(server['max_tip_height'])
        except Exception:
            tip = 0
        max_tip_height = max(max_tip_height, tip)
    # Save for later consumption
    pickle_it('save', 'max_tip_height.pkl', max_tip_height)
    return max_tip_height


# Mempoolspace API does not return the latest block height
# that is synched on the server.
# So, as an alternative, we can iterate and check where we are
def get_sync_height(url):
    message = 'Block height out of range'
    max_tip = pickle_it('load', 'max_tip_height.pkl')
    if max_tip == 'file not found':
        max_tip = get_max_height()
    # Check again - know if cannot happen
    if max_tip == 'file not found':
        raise Exception("max_tip_height.pkl not found")

    # Check if max tip height returns a message
    # if not, fully synched
    check = check_block(url, max_tip)
    if check != message:
        return max_tip
    else:
        # Could not find the tip. Let's see if halfway through the chain
        # it finds the data, then we can iterate from there
        # This process is time consuming. Needs to be optimized later.
        start = 0
        end = max_tip
        found = False
        while found == False:
            current_check = int((end + start) / 2)
            check = check_block(url, current_check)
            # Two outcomes - either not found, means we need to go lower, or found
            if check == message:
                end = current_check
            else:
                # OK, the check is ok. Let's see if we can find the next one
                check_next = check_block(url, current_check + 1)
                if check_next == message:
                    found = True
                # The next one was also found so we need to look higher
                else:
                    start = current_check + 1
        return current_check


def check_all_sync_status():
    # Load server list from pickle
    server_list = pickle_it('load', 'mps_server_status.pkl')
    for server in server_list:
        server['tip_height'] = get_sync_height(server['url'])
        # Remove previous status from this url
        for st in server_list:
            if st['url'] == server['url']:
                server_list.remove(st)
        server_list.append(server)
    pickle_it('save', 'mps_server_status.pkl', server_list)


def check_block(url, block):
    end_point = 'api/block-height/'
    try:
        result = tor_request(url + end_point + str(block))
        result = result.text
    except Exception:
        result = None
    return result


def check_api_health(url):
    # Check if API is reachable and saves the latest status in a pickle
    # formatted like the below:
    # [
    # {
    #     "last_check": "2022-06-12 13:54:16.178834",
    #     "public": true,
    #     "tip_height": 740493,
    #     "url": "https://mempool.space/"
    # },
    # {
    #     "last_check": "2022-06-12 13:54:21.894870",
    #     "public": true,
    #     "tip_height": 740493,
    #     "url": "http://mempoolhqx4isw62xs7abwphsq7ldayuidyx2v2oethdhhj6mlo2r6ad.onion/"
    # },
    # ]
    status = None
    endpoint = 'api/blocks/tip/height'
    try:
        is_public = server_names('get_info', url)[2]
    except IndexError:
        # If not found default to public as a precaution
        is_public = True

    try:
        result = tor_request(url + endpoint)
    except Exception:
        result = None
    # Response returned?
    if isinstance(result, requests.models.Response):
        # Got a 200 code OK back?
        if result.ok is True:
            # save the status to mps_server_status.pkl
            status = {
                'online': True,
                'public': is_public,
                'url': url,
                'last_check': datetime.utcnow(),
                'max_tip_height': result.json(),
                'synched': is_synched(url)
            }

            # Check which kind of address
            status['onion'] = True if '.onion' in url else False
            local_host_strings = ['localhost', '.local', '192.', '0.0.0.0']
            status['localhost'] = True if any(
                host in url for host in local_host_strings) else False
            # Check if named
            status['name'] = server_names(action='get', url=url)

            # Load pickle
            server_statuses = pickle_it('load', 'mps_server_status.pkl')
            if server_statuses == 'file not found':
                server_statuses = [status]
            else:
                # Remove previous status from this url
                for st in server_statuses:
                    if st['url'] == url:
                        # First get some attributes that are not updated in
                        # this method
                        if 'tip_height' in st:
                            status['tip_height'] = st['tip_height']
                        else:
                            status['tip_height'] = None
                        server_statuses.remove(st)
                server_statuses.append(status)

            # Save pickle
            pickle_it('save', 'mps_server_status.pkl', server_statuses)
    else:
        # No response returned
        server_statuses = pickle_it('load', 'mps_server_status.pkl')
        # Update previous status from this url to show it's offline
        for st in server_statuses:
            try:
                if st['url'] == url:
                    status = st
                    status['online'] = False
                    server_statuses.remove(st)
                    server_statuses.append(status)
            except Exception:
                pass
        # Save pickle

        pickle_it('save', 'mps_server_status.pkl', server_statuses)

    return status


def get_address_utxo(url, address):
    # Endpoint
    # GET /api/address/:address/utxo
    endpoint = 'api/address/' + address + '/utxo'
    address_info = {'address': address}
    result = tor_request(url + endpoint)
    try:
        address_json = result.json()
    except Exception:
        raise Exception("Could not parse JSON from url: {url + endpoint}")

    # Clean results and include into a dataframe
    df = pd.DataFrame().from_dict(address_json)

    address_info['df'] = df
    # Include total balance
    if df.empty is not True:
        address_info['balance'] = df['value'].sum()
    else:
        address_info['balance'] = 0

    return address_info


def xpub_derive(xpub,
                number_of_addresses,
                start_number=0,
                output_type='P2PKH'):
    # Output type: P2WPKH, P2PKH
    # Derivation Path: m/84'/0'
    hd = bip32.HDKey.from_string(xpub)
    add_list = []
    net = NETWORKS['main']
    for i in range(0, number_of_addresses):
        ad = hd.derive([start_number, i])
        if output_type == 'P2WPKH':
            add_list.append(script.p2wpkh(ad).address(net))
        elif output_type == 'P2PKH':
            add_list.append(script.p2pkh(ad).address(net))
        else:
            raise Exception("Invalid output type")
    return add_list


def xpub_balances(url, xpub, derivation_types=['P2WPKH', 'P2PKH']):
    # Scan addresses in xpubs and return a list of addresses and balances
    balance_list = []
    for derivation_type in derivation_types:
        counter = 0
        end_counter = 10
        while True:
            # Get the first address
            address = xpub_derive(xpub=xpub,
                                  number_of_addresses=1,
                                  start_number=counter,
                                  output_type=derivation_type)
            # Check balance
            balance = get_address_utxo(url, address[0])['balance']
            # Found something, include
            if balance != 0:
                # Tries at least 10 more addresses after the last balance
                # was found
                end_counter = counter + 10
                add_dict = {
                    'address': address,
                    'utxos': get_address_utxo(url, address[0]),
                    'balance': balance
                }
            # Empty address
            else:
                add_dict = {'address': address, 'utxos': None, 'balance': 0}

            counter += 1
            # Add to list
            balance_list.append(add_dict)

            # 10 sequential addresses with no balance found, break
            if counter >= end_counter:
                break

    return balance_list