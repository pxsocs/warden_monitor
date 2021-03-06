from yaspin import yaspin
import logging
import configparser
import os
import sys
import atexit
import warnings
import socket
import emoji
import sqlite3
import requests
from logging.handlers import RotatingFileHandler
from packaging import version
from ansi.colour import fg
from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_apscheduler import APScheduler
from pathlib import Path
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import EVENT_JOB_ERROR

# Make sure current libraries are found in path
current_path = os.path.abspath(os.path.dirname(__file__))
sys.path.append(current_path)

# Local imports have to be below the path append above
# otherwise they will fail to load
from ansi_management import (warning, success, error, info, clear_screen,
                             muted, yellow, blue)


def create_tor():
    from ansi_management import (warning, success, error, info, clear_screen,
                                 bold, muted, yellow, blue)
    from config import Config
    # ----------------------------------------------
    #                 Test Tor
    # ----------------------------------------------
    with yaspin(text="Testing Tor", color="cyan") as spinner:
        from connections import test_tor
        tor = test_tor()
        if tor['status']:
            logging.info(success("Tor Connected"))
            spinner.ok("✅ ")
            spinner.text = success("    Tor Connected [Success]")
            print("")
            return (tor)
        else:
            logging.error(error("Could not connect to Tor"))
            spinner.fail("💥 ")
            spinner.text = warning("    Tor NOT connected [ERROR]")
            print(error("    Could not connect to Tor."))

            print(
                info(
                    "    [i] If you have a Tor Browser installed try opening (leave it running) and try again."
                ))

            print(
                info("    [i] If you are running Linux try the command: ") +
                yellow('service tor start'))
            print(
                info(
                    "    or download Tor at: https://www.torproject.org/download/"
                ))
            print("")


# ------------------------------------
# Application Factory
def init_app():
    from ansi_management import (warning, success, error)
    from utils import (create_config)
    from config import Config
    from connections import tor_request
    warnings.filterwarnings('ignore')

    # Config of Logging
    from config import Config
    formatter = "[%(asctime)s] {%(module)s:%(funcName)s:%(lineno)d} %(levelname)s in %(module)s: %(message)s"
    logging.basicConfig(handlers=[
        RotatingFileHandler(filename=str(Config.debug_file),
                            mode='w',
                            maxBytes=120000,
                            backupCount=0)
    ],
                        level=logging.INFO,
                        format=formatter,
                        datefmt='%m/%d/%Y %I:%M:%S %p')
    logging.getLogger('apscheduler').setLevel(logging.CRITICAL)
    logging.getLogger('werkzeug').setLevel(logging.CRITICAL)
    logging.info("Starting main program...")

    # Launch app
    app = Flask(__name__)
    app.config.from_object(Config)

    app.logger = logging.getLogger()

    # Load config.ini into app
    # --------------------------------------------
    # Read Global Variables from warden.config(s)
    # Can be accessed like a dictionary like:
    # app.settings['PORTFOLIO']['RENEW_NAV']
    # --------------------------------------------
    config_file = Config.config_file
    app.warden_status = {}

    # Check for internet connection
    from connections import internet_connected
    internet_ok = internet_connected()
    if internet_ok is True:
        print(success("✅ Internet Connection"))
    else:
        print(
            error(
                "[!] WARden needs internet connection. Check your connection.")
        )
        print(warning("[!] Exiting"))
        exit()

    # Config
    config_settings = configparser.ConfigParser()
    if os.path.isfile(config_file):
        config_settings.read(config_file)
        app.warden_status['initial_setup'] = False
        print(
            success(
                "✅ Config Loaded from config.ini - edit it for customization"))
    else:
        print(
            error(
                "  Config File could not be loaded, created a new one with default values..."
            ))
        create_config(config_file)
        config_settings.read(config_file)
        app.warden_status['initial_setup'] = True

    # Get Version
    print("")
    try:
        version_file = Config.version_file
        with open(version_file, 'r') as file:
            current_version = file.read().replace('\n', '')
    except Exception:
        current_version = 'unknown'
    with app.app_context():
        app.version = current_version

    # Check for Cryptocompare API Keys
    print("")
    check_cryptocompare()
    print("")

    print(f"[i] Running WARden Monitor version: {current_version}")
    app.warden_status['running_version'] = current_version

    # CHECK FOR UPGRADE
    repo_url = 'https://api.github.com/repos/pxsocs/warden_monitor/releases'
    try:
        github_version = tor_request(repo_url).json()[0]['tag_name']
    except Exception:
        github_version = None

    app.warden_status['github_version'] = github_version

    if github_version:
        print(f"[i] Newest WARden Monitor version available: {github_version}")
        parsed_github = version.parse(github_version)
        parsed_version = version.parse(current_version)

        app.warden_status['needs_upgrade'] = False
        if parsed_github > parsed_version:
            print(warning("  [i] Upgrade Available"))
            app.warden_status['needs_upgrade'] = True
        if parsed_github == parsed_version:
            print(success("✅ You are running the latest version"))
    else:
        print(warning("[!] Could not check GitHub for updates"))

    print("")
    # Check if config.ini exists
    with app.app_context():
        app.settings = config_settings
        print(success("✅ Config Loaded"))
        print("")
    with app.app_context():
        try:
            from utils import fxsymbol
            app.fx = fxsymbol(config_settings['PORTFOLIO']['base_fx'], 'all')
        except KeyError:  # Problem with this config, reset
            print(error("  [!] Config File needs to be rebuilt"))
            print("")
            create_config(config_file)

    # TOR Server through Onion Address --
    # USE WITH CAUTION - ONION ADDRESSES CAN BE EXPOSED
    # AND GRANT ACCESS TO APPLICATION FROM ANYWHERE
    with app.app_context():
        app.tor = create_tor()

    if app.settings['SERVER'].getboolean('onion_server'):
        from stem.control import Controller
        from urllib.parse import urlparse
        app.tor_port = app.settings['SERVER'].getint('onion_port')
        app.port = app.settings['SERVER'].getint('port')
        from utils import home_path
        toraddr_file = os.path.join(home_path(), "onion.txt")
        app.save_tor_address_to = toraddr_file
        proxy_url = "socks5h://localhost:9050"
        tor_control_port = ""
        try:
            tor_control_address = urlparse(proxy_url).netloc.split(":")[0]
            if tor_control_address == "localhost":
                tor_control_address = "127.0.0.1"
            app.controller = Controller.from_port(
                address=tor_control_address,
                port=int(tor_control_port) if tor_control_port else "default",
            )
        except Exception:
            app.controller = None
        from tor import start_hidden_service
        start_hidden_service(app)

    from errors.handlers import errors
    from routes.main_routes import warden
    from sockets.sockets import sockets
    app.register_blueprint(warden)
    app.register_blueprint(errors)
    app.register_blueprint(sockets)

    # Check if home folder exists, if not create
    home = str(Path.home())
    home_path = os.path.join(home, 'warden/')
    try:
        os.makedirs(os.path.dirname(home_path))
    except Exception:
        pass

    return app


def create_background_jobs(app):
    # Start Schedulers for Backghround Tasks

    from backgroundjobs import (get_btc_price, update_nodes,
                                get_get_max_height, get_nodes_status,
                                check_tip_heights)

    # get_btc_price()

    app.scheduler = BackgroundScheduler()

    app.scheduler.add_job(get_btc_price,
                          'interval',
                          args=[app],
                          seconds=1,
                          max_instances=1)

    app.scheduler.add_job(check_tip_heights,
                          'interval',
                          args=[app],
                          seconds=1,
                          max_instances=1)

    app.scheduler.add_job(update_nodes,
                          'interval',
                          args=[app],
                          seconds=1,
                          max_instances=1)

    app.scheduler.add_job(get_nodes_status,
                          'interval',
                          args=[app],
                          seconds=1,
                          max_instances=1)

    app.scheduler.add_job(get_get_max_height,
                          'interval',
                          args=[app],
                          seconds=1,
                          max_instances=1)

    from mempoolspace import get_max_height
    with app.app_context():
        get_max_height()

    # Add listener to catch errors on background jobs
    def listener(event):
        logging.info(
            error(
                f'Job {event.job_id} raised {event.exception.__class__.__name__}'
            ))
        logging.info(error(f'Job {event.job_id} raised {event.exception}'))
        logging.info(error(f'Job {event.job_id} raised {event.traceback}'))

    # Start listener
    app.scheduler.add_listener(listener, EVENT_JOB_ERROR)

    app.scheduler.start()
    app.warden_status['scheduler_initiated'] = True
    print(success("✅ Background jobs running"))
    print("")
    return (app)


def create_loginmanager(app):
    # Database initiation
    table_error = False
    try:
        # create empty instance of LoginManager
        app.login_manager = LoginManager()
    except sqlite3.OperationalError:
        table_error = True
    #  There was an initial error on getting users
    #  probably because tables were not created yet.
    # The above create_all should have solved it so try again.
    if table_error:
        # create empty instance of LoginManager
        app.login_manager = LoginManager()
    # If login required - go to login:
    app.login_manager.login_view = "warden.login"
    # To display messages - info class (Bootstrap)
    app.login_manager.login_message_category = "secondary"
    app.login_manager.init_app(app)
    app.warden_status['loginmanager_initiated'] = True
    return (app)


def create_db(app):
    # Create empty instance of SQLAlchemy
    app.db = SQLAlchemy()
    app.db.init_app(app)

    # Import models so tables are created
    from models import User, Nodes, GlobalData
    app.db.create_all()

    # Check if there are any users on database, if not, needs initial setup
    users = User.query.all()
    if users == []:
        app.warden_status['initial_setup'] = True

    app.warden_status['db_initiated'] = True

    return (app)


def check_cryptocompare():
    from utils import pickle_it

    with yaspin(text="Testing price grab from Cryptocompare",
                color="green") as spinner:
        data = {'Response': 'Error', 'Message': None}
        try:
            api_key = pickle_it('load', 'cryptocompare_api.pkl')
            if api_key != 'file not found':
                baseURL = (
                    "https://min-api.cryptocompare.com/data/pricemultifull?fsyms=BTC"
                    + "&tsyms=USD&api_key=" + api_key)
                req = requests.get(baseURL)
                data = req.json()
                btc_price = (data['DISPLAY']['BTC']['USD']['PRICE'])
                spinner.text = (success(f"BTC price is: {btc_price}"))
                spinner.ok("✅ ")
                pickle_it('save', 'cryptocompare_api.pkl', api_key)
                return
            else:
                data = {'Response': 'Error', 'Message': 'No API Key is set'}
        except Exception as e:
            data = {'Response': 'Error', 'Message': str(e)}
            logging.error(data)

        try:
            if data['Response'] == 'Error':
                spinner.color = 'yellow'
                spinner.text = "CryptoCompare Returned an error " + data[
                    'Message']
                # ++++++++++++++++++++++++++
                #  Load Legacy
                # ++++++++++++++++++++++++++
                try:
                    # Let's try to use one of the
                    # legacy api keys stored under cryptocompare_api.keys file
                    # You can add as many as you'd like there
                    filename = 'warden/static/cryptocompare_api.keys'
                    file = open(filename, 'r')
                    for line in file:
                        legacy_key = str(line)

                        spinner.text = (
                            warning(f"Trying different API Keys..."))

                        baseURL = (
                            "https://min-api.cryptocompare.com/data/pricemultifull?fsyms=BTC"
                            + "&tsyms=USD&api_key=" + legacy_key)

                        try:
                            data = None
                            logging.debug(f"Trying API Key {legacy_key}")
                            request = requests.get(baseURL)
                            data = request.json()
                            btc_price = (
                                data['DISPLAY']['BTC']['USD']['PRICE'])
                            spinner.text = (
                                success(f"BTC price is: {btc_price}"))
                            spinner.ok("✅ ")
                            logging.debug(f"API Key {legacy_key} Success")
                            pickle_it('save', 'cryptocompare_api.pkl',
                                      legacy_key)
                            return
                        except Exception as e:
                            logging.debug(f"API Key {legacy_key} ERROR: {e}")
                            logging.debug(
                                f"API Key {legacy_key} Returned: {data}")
                            spinner.text = "Didn't work... Trying another."
                except Exception:
                    pass
                spinner.text = (error("Failed to get API Key - read below."))
                spinner.fail("[!]")
                print(
                    '    -----------------------------------------------------------------'
                )
                print(yellow("    Looks like you need to get an API Key. "))
                print(yellow("    The WARden comes with a shared key that"))
                print(yellow("    eventually gets to the call limit."))
                print(
                    '    -----------------------------------------------------------------'
                )
                print(
                    yellow(
                        '    Go to: https://www.cryptocompare.com/cryptopian/api-keys'
                    ))
                print(
                    yellow(
                        '    To get an API Key. Keys from cryptocompare are free.'
                    ))
                print(
                    yellow(
                        '    [Tip] Get a disposable email to signup and protect privacy.'
                    ))
                print(
                    yellow(
                        '    Services like https://temp-mail.org/en/ work well.'
                    ))

                print(muted("    Current API:"))
                print(f"    {api_key}")
                new_key = input('    Enter new API key (Q to quit): ')
                if new_key == 'Q' or new_key == 'q':
                    exit()
                pickle_it('save', 'cryptocompare_api.pkl', new_key)
                check_cryptocompare()
        except KeyError:
            try:
                btc_price = (data['DISPLAY']['BTC']['USD']['PRICE'])
                spinner.ok("✅ ")
                spinner.write(success(f"BTC price is: {btc_price}"))
                pickle_it('save', 'cryptocompare_api.pkl', api_key)
                return
            except Exception:
                spinner.text = (
                    warning("CryptoCompare Returned an UNKNOWN error"))
                spinner.fail("💥 ")
        return (data)


def get_local_ip():
    from utils import pickle_it
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('8.8.8.8', 1))  # connect() for UDP doesn't send packets
    local_ip_address = s.getsockname()[0]
    pickle_it('save', 'local_ip_address.pkl', local_ip_address)
    return (local_ip_address)


def goodbye():
    for n in range(0, 100):
        print("")
    print(
        fg.brightgreen(f"""
   \ \ / (_)_ _ ___ ___
    \ V /| | '_/ -_|_-<
     \_/ |_|_| \___/__/
           (_)_ _
    _  _   | | '  |         _
   | \| |_ |_|_||_| ___ _ _(_)___
   | .` | || | '  \/ -_) '_| (_-<
   |_|\_|\_,_|_|_|_\___|_| |_/__/
"""))

    print(fg.boldyellow("    If you enjoyed the app..."))
    print("")
    print(
        fg.brightgreen(
            "    tipping.me (Lightning): https://tippin.me/@alphaazeta"))
    print("")


def main(debug=False, reloader=False):

    # Make sure current libraries are found in path
    current_path = os.path.abspath(os.path.dirname(__file__))

    # CLS + Welcome
    print("")
    print("")
    print(yellow("Welcome to the WARden <> Launching Application ..."))
    print("")
    print(f"[i] Running from directory: {current_path}")
    print("")

    app = init_app()
    app.app_context().push()
    app = create_loginmanager(app)
    app.app_context().push()
    app = create_db(app)
    app.app_context().push()
    app = create_background_jobs(app)
    app.app_context().push()

    def close_running_threads(app):
        print("")
        print("")
        print(yellow("[i] Please Wait... Shutting down."))
        # Delete Debug File
        try:
            from config import Config
            os.remove(Config.debug_file)
        except FileNotFoundError:
            pass

        # Breaks background jobs
        app.scheduler.shutdown(wait=False)
        goodbye()
        os._exit(1)

    # Register the def above to run at close
    atexit.register(close_running_threads, app)

    print("")
    print(success("✅ WARden Server is Ready... Launch cool ASCII logo!"))
    print("")
    logging.info("Launched WARden Server [Success]")

    def onion_string():
        from utils import pickle_it
        if app.settings['SERVER'].getboolean('onion_server'):
            try:
                pickle_it('save', 'onion_address.pkl',
                          app.tor_service_id + '.onion')
                return (f"""
        {emoji.emojize(':onion:')} Tor Onion server running at:
        {yellow(app.tor_service_id + '.onion')}
                    """)
            except Exception:
                return (yellow("[!] Tor Onion Server Not Running"))
        else:
            return ('')

    def local_network_string():
        host = app.settings['SERVER'].get('host')
        port = str(app.settings['SERVER'].getint('port'))

        if host == '0.0.0.0':
            return (f"""
      Or through your network at address:
      {yellow('http://')}{yellow(get_local_ip())}{yellow(f':{port}/')}""")

    port = app.settings['SERVER'].getint('port')

    # Check if this port is available
    from utils import is_port_in_use
    ports = [5001, 5002, 5003, 5004, 5005, 5006, 5007, 5008, 5009, 5010]
    if is_port_in_use(port) is True:
        # Ooops. Port in use... Let's try other ports...
        for p in ports:
            if is_port_in_use(p) is False:
                print(
                    warning(
                        f"[i] Please note that port {str(port)} is in use."))
                print(
                    warning(
                        f"[i] Port was automatically changed to {str(p)} which is free."
                    ))
                # Reassign port
                port = p
                app.settings['SERVER']['port'] = str(port)
                break

    print(
        fg.brightgreen("""
        _   _           __        ___    ____     _
       | |_| |__   ___  \ \      / / \  |  _ \ __| | ___ _ __
       | __| '_ \ / _ \  \ \ /\ / / _ \ | |_) / _` |/ _ \ '_  |
       | |_| | | |  __/   \ V  V / ___ \|  _ < (_| |  __/ | | |
        \__|_| |_|\___|    \_/\_/_/   \_\_| \_\__,_|\___|_| |_|"""))

    print(f"""
                                    {yellow("Powered by NgU technology")} {emoji.emojize(':rocket:')}


               Node and Bitcoin Address Monitoring App
    -----------------------------------------------------------------
                          Application Loaded

      Open your browser and navigate to one of these addresses:
      {yellow('http://localhost:' + str(port) + '/')}
      {yellow('http://127.0.0.1:' + str(port) + '/')}
      {local_network_string()}
      {onion_string()}
    ----------------------------------------------------------------
                         CTRL + C to quit server
    ----------------------------------------------------------------""")

    # Try to launch webbrowser and open the url
    # if "debug" not in sys.argv or "reloader" not in sys.argv:
    #     try:
    #         import webbrowser
    #         webbrowser.open('http://localhost:' + str(port) + '/')
    #     except Exception:
    #         pass
    return app


app = main()
app.app_context().push()
