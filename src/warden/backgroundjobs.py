import threading
import logging
from datetime import datetime
from pricing_engine.engine import realtime_price
from mempoolspace import (node_searcher, check_api_health, get_tip_height,
                          nodes_status, get_max_height, get_sync_height)
from ansi_management import (warning, success, error, info, clear_screen,
                             muted, yellow, blue)


def get_nodes_status(app):
    with app.app_context():
        nodes_status()


def get_get_max_height(app):
    with app.app_context():
        get_max_height()


def get_btc_price(app):
    from models import update_GlobalData
    price = realtime_price('BTC')

    # Save in database for later consumption
    with app.app_context():
        update_GlobalData(data_name='btc_price',
                          data_value=price,
                          expires_in_seconds=120)

    return (price)


def update_nodes(app):
    from models import Nodes, load_Node
    # First check if any nodes are in database
    with app.app_context():
        nodes = load_Node()

        # No nodes in database, run the add known nodes function
        if nodes == []:
            print(
                " [i] No nodes found. Including the standard public nodes and searching local network..."
            )
            nodes = node_searcher()
            # Include these nodes into the database
            for node in nodes:
                # ('http://umbrel.local:3006/', 'Umbrel', False)
                node_info = {
                    'name': node[1],
                    'url': node[0],
                    'is_public': node[2]
                }
                try:
                    new_node = Nodes(**node_info)
                    app.db.session.add(new_node)
                    app.db.session.commit()
                except Exception as e:
                    print(e)

        # Update the nodes now that they are in the database
        else:
            # create threads to update each of the nodes
            threads = []
            for node in nodes:
                threads.append(
                    threading.Thread(target=check_node, args=[app, node]))

            for thread in threads:
                thread.start()
            # Join all threads
            for thread in threads:
                thread.join()


def node_indbase(node):
    from models import load_Node
    nodes = load_Node(name=node.name)
    if nodes is not None:
        return True
    return False


# Creates background thread to check all servers
def check_node(app, node):
    node = check_api_health(node)
    # Save the last time this node was refreshed with data
    node.last_check = datetime.utcnow()
    with app.app_context():
        # check if this node is still in database
        # it may have been deleted while doing the background job
        from models import load_Node
        if node_indbase(node) is True:
            node = app.db.session.merge(node)
            app.db.session.commit()


# Check all tip heights
def check_tip_heights(app):
    from models import load_Node
    # First check if any nodes are in database
    with app.app_context():
        nodes = load_Node()

    # create threads to update each of the nodes
    threads = []
    for node in nodes:
        threads.append(
            threading.Thread(target=check_tip_node, args=[app, node]))

    for thread in threads:
        thread.start()
    # Join all threads
    for thread in threads:
        thread.join()


def check_tip_node(app, node):
    with app.app_context():
        node = get_sync_height(node)
        if node_indbase(node) is True:
            node = app.db.session.merge(node)
            app.db.session.commit()
