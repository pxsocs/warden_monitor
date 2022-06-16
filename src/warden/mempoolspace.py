from datetime import datetime
from embit import bip32, script
from embit.networks import NETWORKS
import requests
import pandas as pd
from utils import load_config, pickle_it, update_config
from connections import tor_request, url_parser


def mp_urls(action=None, url=None, public=True):
    config = load_config()
    path_items = config.items("MAIN")
    # Including new address -- action = add
    if action == 'add':
        if url is None:
            raise Exception("URL Required")
        url = url_parser(url)
        counter = 0
        mask = 'mspace_public_address_' if public == True else 'mspace_private_address_'
        for key, path in path_items:
            if url == path:
                raise Exception("Address already exists")
            if mask in key:
                # find the latest index of mspace_public
                try:
                    this_count = int(key.strip(mask))
                except Exception:
                    this_count = 0
                counter = max(counter, this_count)
        counter += 1
        config['MAIN'][mask + str(counter)] = url_parser(url)
        update_config(config=config)

    # Remove an address from config
    if action == 'remove':
        if url is None:
            raise Exception("URL Required")
        url = url_parser(url)
        for key, path in path_items:
            if url == path:
                config.remove_option('MAIN', key)
                update_config(config=config)
                return

    # Get addresses from config and returns a dictionary with public
    # and private addresses
    private_list = []
    public_list = []
    for key, path in path_items:
        if 'mspace_public' in key:
            public_list.append(path)
        if 'mspace_personal' in key:
            private_list.append(path)
    return {'public': public_list, 'private': private_list}


def check_all_servers():
    mp_addresses = mp_urls()
    for public_url in mp_addresses['public']:
        check_api_health(public_url, public=True)
    for personal_url in mp_addresses['private']:
        check_api_health(personal_url, public=False)


def check_api_health(url, public):
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

    endpoint = 'api/blocks/tip/height'
    result = tor_request(url + endpoint)
    api_reachable = False
    # Response returned?
    if isinstance(result, requests.models.Response):
        # Got a 200 code OK back?
        if result.ok is True:
            api_reachable = True
            # save the status to mps_server_status.pkl
            status = {
                'public': public,
                'url': url,
                'last_check': datetime.utcnow(),
                'tip_height': result.json()
            }
            # Load pickle
            server_statuses = pickle_it('load', 'mps_server_status.pkl')
            if server_statuses == 'file not found':
                server_statuses = [status]
            else:
                # Remove previous status from this url
                for st in server_statuses:
                    if st['url'] == url:
                        server_statuses.remove(st)
                server_statuses.append(status)

            # Save pickle
            pickle_it('save', 'mps_server_status.pkl', server_statuses)
    return api_reachable


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