import json
from platform import node
from flask import Blueprint, render_template, request, jsonify
from random import randrange
from utils import pickle_it
from connections import tor_request, url_parser, url_reachable
from mempoolspace import node_actions, is_url_mp_api

sockets = Blueprint("sockets", __name__)

templateData = {"title": "WARden Monitor"}

# ---------------------------
#  API Functions
# ---------------------------


@sockets.route('/mempool_socket')
def mempool_socket():
    # get a list of .pkl files in the pickle directory
    templateData['title'] = "mempool.space WebSocket"
    templateData['base_url'] = 'http://raspberrypi.local:4080/'
    return render_template('sockets/ms_socket_connect.html', **templateData)


@sockets.route("/satoshi_quotes_json", methods=['GET'])
def satoshi_quotes_json():
    url = 'https://raw.githubusercontent.com/NakamotoInstitute/nakamotoinstitute.org/0bf08c48cd21655c76e8db06da39d16036a88594/data/quotes.json'
    try:
        quotes = tor_request(url).json()
    except Exception:
        return (json.dumps(' >> Error contacting server. Retrying... '))
    quote = quotes[randrange(len(quotes))]
    return (quote)


@sockets.route("/node_list", methods=['GET'])
def node_list():
    # When asked to GET, will return the current list of nodes
    node_list = node_actions()
    js = json.dumps(node_list, default=str)
    return (js)


@sockets.route("/initial_search", methods=['POST'])
def initial_search():
    if request.method == 'POST':
        from mempoolspace import node_searcher
        node_searcher()
        return json.dumps("success")


@sockets.route("/node_action", methods=['GET', 'POST'])
def node_action():
    # When asked to GET, will return the current list of nodes
    if request.method == 'GET':
        node_list = node_actions()
        return json.dumps(node_list, default=str)

    if request.method == 'POST':
        try:
            data = json.loads(request.data)
            url = url_parser(data['node_url'])
            if 'action' in data:
                if data['action'] == 'delete':
                    node_name = data['node_name']
                    node_actions('delete', url=url)
                    return json.dumps(f"{node_name} deleted")

            if url_reachable(url) == False:
                return json.dumps("Node is not reachable. Check the URL.")
            # Check if this URL is a mempool.space API
            if is_url_mp_api(url) == False:
                return json.dumps(
                    "URL was found but the mempool.space API does not seem to be installed. Check your node apps."
                )
            # Include new node
            node_actions('add',
                         url=url,
                         name=data['node_name'],
                         public=not (data['is_private_node']))
            return json.dumps("success")
        except Exception as e:
            return json.dumps(f"Error: {e}")


# Gets a local pickle file and dumps - does not work with pandas df
# Do not include extension pkl on argument
@sockets.route("/get_pickle", methods=['GET'])
def get_pickle():
    filename = request.args.get("filename")
    serialize = request.args.get("serialize")
    if not serialize:
        serialize = True
    if not filename:
        return None
    filename += ".pkl"
    data_loader = pickle_it(action='load', filename=filename)
    if serialize is True:
        return (json.dumps(data_loader,
                           default=lambda o: '<not serializable>'))
    else:
        return (json.dumps(data_loader, default=str))


@sockets.route("/global_data", methods=['GET'])
def global_data():
    from models import load_GlobalData
    # None provided - load all data
    data_name = request.args.get("data_name")
    data = load_GlobalData(data_name)
    if data_name is None:
        list_return = []
        for element in data:
            data_return = {
                'data_name': element.data_name,
                'data_value': element.data_value,
                'last_updated': element.last_updated,
                'expires_at': element.expires_at
            }
            list_return.append(data_return)
        return (json.dumps(list_return, default=str))
    else:
        if data is None:
            return json.dumps("No data found")
        data_return = {
            'data_name': data.data_name,
            'data_value': data.data_value,
            'last_updated': data.last_updated,
            'expires_at': data.expires_at
        }
    return (json.dumps(data_return, default=str))
