from datetime import datetime
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


def get_address(url, address):
    # Endpoint
    # GET /api/address/:address/txs
    # Will return only 25 txs - for more use:
    # :last_seen_txid
    endpoint = 'api/address/' + address + '/txs'
    address_info = {'address': address}
    result = tor_request(url + endpoint)
    try:
        address_json = result.json()
    except Exception:
        raise Exception("Could not parse JSON from url: {url + endpoint}")

    # Clean results and include into a dataframe
    df = pd.DataFrame().from_dict(address_json)

    # Vin and Vouts are lists stored in the df - vin and vout
    # will cycle through list and get each vin and vout
    def get_vin_total(row):
        vin_total = 0
        for element in row['vin']:
            print(element)
            vin_total += element['prevout']['value']
        return vin_total

    def get_vout_total(row):
        vout_total = 0
        for element in row['vout']:
            print(element)
            vout_total += element['value']
        return vout_total

    df['vin_total'] = df.apply(get_vin_total, axis=1)
    df['vout_total'] = df.apply(get_vout_total, axis=1)
    df['v_net'] = df['vin_total'] - df['vout_total']

    address_info['df'] = df

    # Include totals
    address_info['vin_total'] = df['vin_total'].sum()
    address_info['vout_total'] = df['vout_total'].sum()
    address_info['balance'] = df['v_net'].sum()

    return address_info
