import json
from flask import Blueprint, current_app, render_template
from flask_sock import Sock
from utils import pickle_it

sockets = Blueprint("sockets", __name__)
sock = Sock(app=current_app)

templateData = {
    "title": "WARden Monitor",
    "FX": current_app.settings['PORTFOLIO']['base_fx'],
    "current_app": current_app,
}


@sockets.route('/socket_connect')
def index():
    # get a list of .pkl files in the pickle directory
    templateData['title'] = "WebSocket Connection"
    templateData['pkl_files'] = pickle_it(action='list')
    return render_template('sockets/socket_connect.html', **templateData)


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