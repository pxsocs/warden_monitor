import json
from flask import Blueprint, current_app, render_template, request
from flask_sock import Sock
from random import randrange
from utils import pickle_it
from connections import tor_request, url_parser, url_reachable
from mempoolspace import server_names, is_url_mp_api, get_node_full_data

sockets = Blueprint("sockets", __name__)
sock = Sock(app=current_app)

templateData = {
    "title": "WARden Monitor",
    "FX": current_app.settings['PORTFOLIO']['base_fx'],
    "current_app": current_app,
}

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


@sockets.route("/node_action", methods=['GET', 'POST'])
def node_action():
    # When asked to GET, will return the current list of nodes
    if request.method == 'GET':
        node_list = server_names()
        # if an argument is passed, return full node data from files
        if request.args.get('full_node_data') is not None:
            full_list = get_node_full_data()
            return (json.dumps(full_list, indent=4, default=str))
        # Return only names
        return (json.dumps(node_list))
    if request.method == 'POST':
        try:
            data = json.loads(request.data)
            url = url_parser(data['node_url'])
            if 'action' in data:
                if data['action'] == 'delete':
                    node_name = data['node_name']
                    server_names('delete', url)
                    return json.dumps(f"{node_name} deleted")

            url = url_parser(data['node_url'])
            # Check if this URL is reachable
            is_reachable = url_reachable(url)
            if is_reachable == False:
                return json.dumps("Node is not reachable. Check the URL.")
            # Check if this URL is a mempool.space API
            if is_url_mp_api(url) == False:
                return json.dumps(
                    "URL was found but the mempool.space API does not seem to be installed. Check your node apps."
                )
            server_names('add',
                         url=url,
                         name=data['node_name'],
                         public=not (data['is_private_node']))
            return json.dumps("success")
        except Exception as e:
            return (f"Error: {e}")


@sockets.route('/socket_connect')
def socket_connect():
    # get a list of .pkl files in the pickle directory
    templateData['title'] = "WebSocket Connection"
    templateData['pkl_files'] = pickle_it(action='list')
    return render_template('sockets/socket_connect.html', **templateData)


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


# ---------------------------
#  Web Socket Functions
# ---------------------------


@sock.route('/pickle')
def return_pickle(ws):
    while True:
        pkl = ws.receive()
        try:
            response = pickle_it('load', pkl)
            response = json.dumps(response,
                                  indent=4,
                                  sort_keys=True,
                                  default=str)
        except Exception as e:
            response = str(e)
        ws.send(response)


@sock.route('/echo')
def echo(ws):
    while True:
        data = ws.receive()
        ws.send(data)
