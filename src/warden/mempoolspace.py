from datetime import datetime
from flask import current_app, has_app_context
from embit import bip32, script
from embit.networks import NETWORKS
import threading
import logging
import pandas as pd
from connections import tor_request, url_reachable, url_parser
from ansi_management import (warning, success, error, info, clear_screen,
                             muted, yellow, blue)
from utils import jformat


# Method used to search for nodes - used at first config to
# check for typical nodes and if they are available
# to then include them in database
def node_searcher():
    known_names = [
        ('http://mempool.space/', 'mempool.space', True),
        ('http://mempoolhqx4isw62xs7abwphsq7ldayuidyx2v2oethdhhj6mlo2r6ad.onion/',
         'mempool.space [onion]', True),
        ('http://raspberrypi.local:4080/', 'RaspiBlitz', False),
        ('http://umbrel.local:3006/', 'Umbrel', False),
    ]

    print(" [i] Search for nodes...")

    found_nodes = []

    def check_node(server):
        url = server[0]
        print(" [i] Checking for node at " + url)
        if url_reachable(url) is True:
            print(" [i] Node at " + url + " is reachable")
            api_reached, _ = is_url_mp_api(url)
            if api_reached is True:
                print(" [i] Node at " + url + " has a mempool.space API")
                found_nodes.append(server)
                print(success(" [OK] Found node at " + url))
                return True
        else:
            return False

    threads = []

    for server in known_names:
        threads.append(threading.Thread(target=check_node, args=[server]))

    for thread in threads:
        thread.start()

    # Join all threads
    for thread in threads:
        thread.join()

    if found_nodes == []:
        # At a minimum will return one public node
        # there's actually no reason for this not to be found
        # unless the app is offline or there's a connection issue
        # with all the nodes (should not happen)
        print(
            yellow(
                " [i] No nodes found, using only Mempool.space - you can add a node later"
            ))
        found_nodes = [('http://mempool.space/', 'mempool.space', True)]
    else:
        print(success(" [i] Found " + str(len(found_nodes)) + " nodes"))
        print("")

    return found_nodes


# Creates a list of URLs and names for the public and private addresses
def node_actions(action=None, url=None, name=None, public=True):
    # Sample list_all output:
    # [
    #   ('http://raspberrypi.local:4080/', 'RaspiBlitz Home', False),
    #   ('http://mempool.space/', 'mempool.space', True),
    #   ('http://mempoolhqx4isw62xs7abwphsq7ldayuidyx2v2oethdhhj6mlo2r6ad.onion/', 'mempool.space [onion]', True)
    # ]

    from models import Nodes

    # add name to url (actually it's an add or replace if exists)
    # so add = edit
    if action == 'add':
        # check if exists, if so, load to edit, if not create new
        from models import load_Node
        node = load_Node(url=url)
        if node is None:
            node = Nodes()
        node.url = url_parser(url)
        node.name = name
        node.is_public = public
        node = check_api_health(node)
        current_app.db.session.add(node)
        current_app.db.session.commit()
        return node

    # Remove name from list
    if action == 'delete' or action == 'remove':
        node = Nodes.query.filter_by(url=url).first()
        current_app.db.session.delete(node)
        current_app.db.session.commit()

    if action == 'get':
        if url is not None:
            node = Nodes.query.filter_by(url=url).first()
        if name is not None:
            node = Nodes.query.filter_by(name=name).first()
        return node

    # No action, just list all
    nodes = Nodes.query.all()
    return nodes


# Returns the highest block height in all servers
def get_max_height():
    from models import load_Node, Nodes
    from sqlalchemy import func
    url = None
    max_tip_height = current_app.db.session.query(
        func.max(Nodes.blockchain_tip_height)).first()[0]
    node = Nodes.query.filter_by(node_tip_height=max_tip_height).first()
    if node is not None:
        url = node.url

    # If even after looking for nodes, still couldn't find a max height,
    # use mempool.space url to check
    if max_tip_height == 0:
        url = 'https://mempool.space/api/blocks/tip/height'
        try:
            max_tip_height = tor_request(url).text
            max_tip_height = int(max_tip_height)
        except Exception as e:
            max_tip_height = 'unknown'

    # Save for later consumption
    from models import update_GlobalData
    update_GlobalData('max_blockchain_tip_height', max_tip_height)
    # Get the full block details for later consumption
    if url is not None:
        top_block_details = get_last_block_info(url, max_tip_height)
        if top_block_details is not None:
            update_GlobalData('top_block_details', top_block_details)

    return max_tip_height


# Mempoolspace API does not return the latest block height
# that is synched on the server.
# So, as an alternative, we can iterate and check where we are
def get_sync_height(node):
    url = node.url
    logging.info(muted("Checking tip height for " + node.name))
    # Message returned by API when block is not found at node
    message = 'Block height out of range'

    # Get the max tip height
    from models import load_GlobalData
    max_tip = load_GlobalData(data_name='max_blockchain_tip_height',
                              value=True)
    logging.info(
        muted("Checking tip height for " + node.name + " - max tip: " +
              str(max_tip)))

    # Check if max tip height returns a message
    # if not, fully synched
    check = check_block(url, max_tip)
    if ((check != message) and (check is not None)):
        logging.info(muted("No need to iterate " + node.name))
        logging.info(success(f"{node.name} synched at {max_tip}"))
        if max_tip != 0:
            node.node_tip_height = max_tip
        return node
    else:
        # Maybe it fell behind by one block?
        # Can happen on Onion and/or slow connections
        check_previous = max_tip - 1
        check = check_block(url, check_previous)
        if check != message and max_tip != 0:
            node.node_tip_height = check_previous
            return node

        logging.info(
            blue(f"{node.name} is not fully synched - will need to iterate"))
        # Could not find the tip. Let's see if halfway through the chain
        # it finds the data, then we can iterate from there
        # This process is time consuming. Needs to be optimized later.

        # First let's step a few blocks ahead from the last one we found
        # this may be quicker
        steps_ahead = 3
        if isinstance(node.node_tip_height, int):
            if node.node_tip_height > 0:
                last_tip = node.node_tip_height
                if isinstance(last_tip, int):
                    for i in range(steps_ahead):
                        current_check = last_tip + i + 1
                        # No need to check after top tip
                        if current_check >= max_tip:
                            break
                        logging.info(
                            muted(
                                f"Checking [steps ahead] {node.name} at {current_check}"
                            ))
                        check = check_block(url, current_check)
                        if check != message:
                            logging.info(
                                success(
                                    f"[step ahead success] {node.name} synched at {current_check}"
                                ))
                            node.node_tip_height = current_check
                            return node
        logging.info(
            error(f"[step ahead failed - proceed to halfing] {node.name}"))

        # Well... Wasn't a few steps ahead, let's iterate halving the range
        found_tip = False
        current_check = 0
        start = 0
        end = max_tip
        if max_tip == 0:
            return node
        while found_tip is False:
            logging.info(blue(f"Checking {node.name} starting halving..."))
            previous_check = current_check
            current_check = int((end + start) / 2)
            logging.info(blue(f"Checking {node.name} at {current_check}"))
            if current_check == 0:
                current_check = 'unknown'
                break
            try:
                node.node_tip_height = f"<span class='text-warning'>Node not synched. Finding synch status<br>[currently checking block: {str(jformat(current_check, 0))}]<br>latest block tip at <status>"
            except TypeError:
                pass

            if previous_check == current_check:
                logging.info(
                    error(
                        f"{node.name} checking stuck at {current_check} -- breaking"
                    ))
                break
            logging.info(muted(f"{node.name} checking at {current_check}"))
            check = check_block(url, current_check)
            # Two outcomes - either not found, means we need to go lower, or found
            if check == message:
                end = current_check
            else:
                # OK, the check is ok. Let's see if we can find the next one
                check_next = check_block(url, current_check + 1)
                if check_next == message:
                    found_tip = True
                # The next one was also found so we need to look higher
                else:
                    start = current_check + 1

        # Load previous status, update and save
        if current_check > 0:
            node.node_tip_height = current_check
            logging.info(
                success(
                    f"{node.name} [halfing iter] synched at {current_check}"))
        return node


# Get Block Header and return when was it found
def get_last_block_info(url, height):
    # Get Hash
    end_point = 'api/block-height/' + str(height)
    hash = tor_request(url + end_point)
    try:
        hash = hash.text
    except AttributeError:
        return None
    if hash == 'Block height out of range':
        logging.info(
            error("Block height out of range -- could not get latest time"))
        return None
    # Know get the latest data
    end_point = 'api/block/' + hash
    block_info = tor_request(url + end_point)
    try:
        block_info = block_info.json()
    except Exception:
        return None
    return (block_info)


def check_block(url, block):
    end_point = 'api/block-height/'
    try:
        result = tor_request(url + end_point + str(block))
        result = result.text
    except Exception:
        result = None
    return result


# Check if this url is a mempool.space API
# returns true if reachable + request time
# zero = no response or error
def is_url_mp_api(url):
    end_point = 'api/blocks/tip/height'
    requests = tor_request(url + end_point)
    try:
        if requests.status_code == 200:
            return (True, requests.elapsed)
        else:
            return (False, 0)
    except Exception:
        return (False, 0)


# Get the highest tip height from a certain url
# this is not the synch tip height but rather
# the block with most proof of work - that can be
# ahead of the synch tip height
def get_tip_height(url):
    endpoint = 'api/blocks/tip/height'
    result = tor_request(url + endpoint)
    try:
        result = result.text
        result = int(result)
        return result
    except Exception:
        return None


def check_api_health(node):
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

    logging.info(muted("Checking server: " + node.name))
    url = node.url

    # Store ping time and return that it's reacheable
    reachable, ping = is_url_mp_api(url)
    node.mps_api_reachable = reachable
    node.ping_time = ping

    # mps API not found, let's see if at least the node
    # is alive but it's a problem with API
    if reachable is False:
        node.is_reachable = url_reachable(url)
    else:
        node.is_reachable = True

    # Node is online and reachable with a MPS API working
    # store the last time it was online
    if node.is_reachable is True:
        node.last_online = datetime.utcnow()
        tip = get_tip_height(node.url)
        if tip is not None:
            node.blockchain_tip_height = tip

    # Other data
    node.onion = True if '.onion' in url else False

    local_host_strings = ['localhost', '.local', '192.', '0.0.0.0']
    node.is_localhost = True if any(host in url
                                    for host in local_host_strings) else False

    # Save the node information to the database
    return node


# get a set of statistics from the nodes
def nodes_status():
    from models import load_Node
    stats = {}
    # Load node info
    full_data = load_Node()
    stats['check_time'] = datetime.utcnow()
    stats['total_nodes'] = len(full_data)
    stats['online'] = sum(x.mps_api_reachable == True for x in full_data)
    stats['is_public'] = sum(x.is_public == True for x in full_data)
    stats['at_tip'] = sum(x.is_at_tip() == True for x in full_data)
    stats['is_onion'] = sum(x.is_onion() == True for x in full_data)
    stats['is_localhost'] = sum(x.is_localhost == True for x in full_data)
    # # Save for later consumption
    from models import update_GlobalData
    update_GlobalData(data_name='node_stats', data_value=stats)
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