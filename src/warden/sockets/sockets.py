import json
from flask import Blueprint, current_app, render_template, request
from flask_sock import Sock
from random import randrange
from utils import pickle_it
from connections import tor_request

sockets = Blueprint("sockets", __name__)
sock = Sock(app=current_app)

templateData = {
    "title": "WARden Monitor",
    "FX": current_app.settings['PORTFOLIO']['base_fx'],
    "current_app": current_app,
}


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

