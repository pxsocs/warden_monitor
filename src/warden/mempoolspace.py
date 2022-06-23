from datetime import datetime
from fileinput import filename
from embit import bip32, script
from embit.networks import NETWORKS
import threading
import logging
import pandas as pd
from utils import pickle_it, safe_filename
from connections import tor_request, url_reachable
from ansi_management import (warning, success, error, info, clear_screen,
                             muted, yellow, blue)
from utils import jformat
from decorators import MWT


# Creates a list of URLs and names for the public and private addresses
@MWT(timeout=1)
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
        # Now that it's included, request an update of this new node
        check_api_health(url)
        return

    # Remove name from list
    if action == 'delete' or action == 'remove':
        for st in custom_names:
            try:
                if st[0] == url:
                    custom_names.remove(st)
            except Exception:
                pass
        # Save pickle

    pickle_it('save', 'mps_custom_names.pkl', custom_names)

    return custom_names


# Creates background thread to check all servers
def check_all_servers():
    logging.info(muted("Checking all servers"))
    mp_addresses = server_names()
    urls = [i[0] for i in mp_addresses]

    threads = []

    for url in urls:
        threads.append(threading.Thread(target=check_api_health, args=[url]))

    for thread in threads:
        thread.start()
    # Join all threads
    for thread in threads:
        thread.join()

    logging.info(success("All servers threads concluded"))


# This process can be time consuming
# so we need to check in parallel with threads
@MWT(timeout=10)
def check_all_tip_heights():
    logging.info(muted("Checking all tip heights"))
    mp_addresses = server_names()
    urls = [i[0] for i in mp_addresses]
    threads = []

    for url in urls:
        threads.append(threading.Thread(target=get_sync_height, args=[url]))

    for thread in threads:
        thread.start()
    # Join all threads
    for thread in threads:
        thread.join()

    logging.info(success("All servers get_tip threads concluded"))


@MWT(timeout=15)
def is_synched(url):
    logging.info(muted("Checking if " + url + " is synched"))

    endpoint = 'api/block-height/'
    max_tip = pickle_it('load', 'max_tip_height.pkl')
    if max_tip == 'file not found':
        max_tip = 100
    result = tor_request(url + endpoint + str(max_tip))
    try:
        r = result.text
    except Exception as e:
        logging.info(warning(url + " synch check failed. Error: " + str(e)))
        return False
    bad_response = 'Block height out of range'
    if r == bad_response:
        logging.info(warning(url + " is not synched"))
        return False
    else:
        logging.info(success(url + " is synched"))
        return True


# Returns the highest block height in all servers
@MWT(timeout=30)
def get_max_height():
    max_tip_height = pickle_it('load', 'max_tip_height.pkl')
    if max_tip_height == 'file not found':
        max_tip_height = 0
    max_tip_height = 0

    # Load server list from pickle
    servers = server_names()
    for server in servers:
        end_point = 'api/blocks/tip/height'
        url = server[0]
        this_highest = tor_request(url + end_point)
        try:
            this_highest = int(this_highest.text)
        except Exception:
            this_highest = 0

        max_tip_height = max(max_tip_height, this_highest)

    # Save for later consumption
    pickle_it('save', 'max_tip_height.pkl', max_tip_height)
    return max_tip_height


# Mempoolspace API does not return the latest block height
# that is synched on the server.
# So, as an alternative, we can iterate and check where we are
def get_sync_height(url):
    logging.info(muted("Checking tip height for " + url))
    message = 'Block height out of range'
    filename = "save_status/" + safe_filename(url) + '.pkl'
    max_tip = pickle_it('load', 'max_tip_height.pkl')
    if max_tip == 'file not found':
        max_tip = get_max_height()
    # Check again - know if cannot happen
    if max_tip == 'file not found':
        raise Exception("max_tip_height.pkl not found")

    # Get this node previous state
    previous_state = pickle_it('load', filename)
    # Check if max tip height returns a message
    # if not, fully synched
    check = check_block(url, max_tip)
    if check != message:
        logging.info(muted("No need to iterate " + url))
        if previous_state != 'file not found':
            previous_state['tip_height'] = max_tip
            try:
                node_name = previous_state['name']
            except KeyError:
                node_name = 'Unknown'
        else:
            previous_state = {'tip_height': max_tip}
            node_name = f'Unknown node at {url}'
        pickle_it('save', filename, previous_state)
        logging.info(success(f"{node_name} at {max_tip}"))
        return max_tip
    else:
        # Could not find the tip. Let's see if halfway through the chain
        # it finds the data, then we can iterate from there
        # This process is time consuming. Needs to be optimized later.
        start = 0
        end = max_tip
        found = False
        current_check = 0

        # First let's step a few blocks ahead from the last one we found
        # this may be quicker
        steps_ahead = 3
        if previous_state != 'file not found':
            node_name = previous_state['name']
            last_tip = previous_state['tip_height']
            if isinstance(last_tip, int):
                for i in range(steps_ahead):
                    current_check = last_tip + i + 1
                    # No need to check after top tip
                    if current_check > max_tip:
                        break
                    logging.info(
                        muted(
                            f"Checking [steps ahead] {node_name} at {current_check}"
                        ))
                    check = check_block(url, current_check)
                    if check != message:
                        logging.info(
                            success(f"{node_name} synched at {current_check}"))
                        previous_state['tip_height'] = current_check
                        pickle_it("save", filename, previous_state)
                        return max_tip

        # Well... Wasn't a few steps ahead, let's iterate halving the range
        while found == False:
            previous_check = current_check
            current_check = int((end + start) / 2)
            try:
                previous_state[
                    'tip_height'] = f"<span class='text-warning'>Node not synched. Finding synch status<br>[currently checking block: {str(jformat(current_check, 0))}]<br>latest block tip at <status>"
                pickle_it('save', filename, previous_state)
            except TypeError:
                pass

            if previous_check == current_check:
                logging.info(
                    error(
                        f"{node_name} checking stuck at {current_check} -- breaking"
                    ))
                break
            logging.info(muted(f"{url} checking at {current_check}"))
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

        # Update the saved pkl for this server
        if url is None:
            return None

        # Load previous status, update and save
        previous_state = pickle_it('load', filename)
        previous_state['tip_height'] = current_check
        pickle_it('save', filename, previous_state)

        logging.info(success(f"{node_name} at {current_check}"))
        return current_check


@MWT(timeout=600)
def check_block(url, block):
    end_point = 'api/block-height/'
    try:
        result = tor_request(url + end_point + str(block))
        result = result.text
    except Exception:
        result = None
    return result


# Check if this url is a mempool.space API
def is_url_mp_api(url):
    end_point = endpoint = 'api/blocks/tip/height'
    requests = tor_request(url + end_point)
    try:
        if requests.status_code == 200:
            return True
        else:
            return False
    except Exception:
        return False


@MWT(timeout=2)
def check_api_health(url):
    # . Reachable
    # . ping time
    # . Last time reached
    # . Mempool API active
    # . Tip_height (Reurning null some times)
    # . Current Block Height
    # . is_tor
    # . is_localhost
    # . name
    # . progress
    # . blocks behind

    # make a safe filename for this url
    filename = "save_status/" + safe_filename(url) + '.pkl'

    if url is None:
        return None

    # Get name info for this server
    server_data = server_names('get_info', url)

    logging.info(muted("Checking server: " + server_data[1]))

    # Load previous status
    previous_state = pickle_it('load', filename)

    if previous_state == 'file not found':
        logging.info(error(server_data[1] +
                           ' has not been previously checked'))
        current_state = {
            'filename': filename,
            'name': 'loading...',
            'url': url,
            'online': 'loading...',
            'is_public': 'loading...',
            'last_check': "Never",
            'max_tip_height': "loading...",
            'tip_height': "loading...",
            'synched': "loading...",
        }
    else:
        current_state = previous_state

    # Public or Private Node?
    try:
        current_state['is_public'] = server_data[2]
    except IndexError:
        # If not found default to public as a precaution
        current_state['is_public'] = True

    # Save Name
    current_state['name'] = server_data[1]

    # Check if online
    current_state['online'] = url_reachable(url)

    # Check if API is working
    current_state['mps_api_reachable'] = is_url_mp_api(url)

    if current_state['mps_api_reachable'] == True:
        current_state['last_check'] = datetime.utcnow()

    current_state['max_tip_height'] = get_max_height()

    # Check if synched
    current_state['synched'] = is_synched(url)

    # Other data
    current_state['onion'] = True if '.onion' in url else False

    local_host_strings = ['localhost', '.local', '192.', '0.0.0.0']
    current_state['localhost'] = True if any(
        host in url for host in local_host_strings) else False

    # Save pickle
    pickle_it('save', filename, current_state)

    logging.info(
        success(server_data[1] + ' checked. Last check: ' +
                str(current_state['last_check'])))

    return current_state


# Which server has the latest updated data?
# returns server data:
# {
#     "filename": "save_status/httpmempoolspace.pkl",
#     "name": "mempool.space",
#     "url": "http://mempool.space/",
#     "online": true,
#     "is_public": true,
#     "last_check": "2022-06-21 15:29:39.714141",
#     "max_tip_height": 741741,
#     "tip_height": 741741,
#     "synched": true,
#     "mps_api_reachable": true,
#     "onion": false,
#     "localhost": false
#   },
def most_updated_server():
    servers = server_names()
    last_update = datetime.min
    most_updated = None
    for server in servers:
        filename = "save_status/" + safe_filename(server[0]) + '.pkl'
        server_info = pickle_it('load', filename)
        last_check = server_info['last_check']
        if last_check > last_update:
            most_updated = server_info
            last_check = last_update

    pickle_it('save', 'most_updated.pkl', most_updated)
    return most_updated


# Get Block Header and return when was it found
@MWT(timeout=30)
def get_last_block_info(url=None):
    # if no url is provided, use the first on list
    if url == None:
        logging.info(muted("checking last block - using default url "))
        url = 'https://mempool.space/'
        logging.info(url)

    logging.info(muted("Checking last block info for: " + url))

    max_tip = pickle_it('load', 'max_tip_height.pkl')
    if max_tip == 'file not found':
        max_tip = get_max_height()
    # Check again - this cannot happen
    if max_tip == 'file not found':
        raise Exception("max_tip_height.pkl not found")

    # Get Hash
    end_point = 'api/block-height/' + str(max_tip)
    hash = tor_request(url + end_point)
    hash = hash.text

    if hash == 'Block height out of range':
        logging.info(
            error("Block height out of range -- could not get latest time"))
        return None

    # Know get the latest data
    end_point = 'api/block/' + hash
    block_info = tor_request(url + end_point)
    try:
        block_info = block_info.json()
        pickle_it('save', 'last_block_info.pkl', block_info)
    except Exception:
        return None

    return (block_info)


def get_node_full_data():
    node_list = server_names()
    full_list = []
    for server in node_list:
        url = server[0]
        filename = "save_status/" + safe_filename(url) + '.pkl'
        server_file = pickle_it('load', filename)
        if server_file != 'file not found':
            full_list.append(server_file)
    return full_list


# get a set of statistics from the nodes
def nodes_status():
    stats = {}
    # Load node info
    full_data = get_node_full_data()
    max_height = get_max_height()
    stats['check_time'] = datetime.utcnow()
    stats['total_nodes'] = len(full_data)
    stats['online'] = sum(x.get('online') == True for x in full_data)
    stats['is_public'] = sum(x.get('is_public') == True for x in full_data)
    stats['synched'] = sum(x.get('synched') == True for x in full_data)
    stats['onion'] = sum(x.get('onion') == True for x in full_data)
    stats['localhost'] = sum(x.get('localhost') == True for x in full_data)
    stats['at_tip'] = sum(x.get('tip_height') == max_height for x in full_data)
    pickle_it('save', 'nodes_status.pkl', stats)
    return (stats)


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