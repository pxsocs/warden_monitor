import logging
import configparser
import os
import json
import pickle
import glob

from config import Config

import mhp as mrh


# Returns the current application path
def current_path():
    application_path = os.path.dirname(os.path.abspath(__file__))
    return (application_path)


# Returns the home path
def home_path():
    from pathlib import Path
    home = str(Path.home())
    return (home)


def create_config(config_file):
    logging.warning(
        "Config File not found. Getting default values and saving.")
    # Get the default config and save into config.ini
    default_file = Config.default_config_file

    default_config = configparser.ConfigParser()
    default_config.read(default_file)

    with open(config_file, 'w') as file:
        default_config.write(file)

    return (default_config)


def update_config(config, config_file=Config.config_file):
    with open(config_file, 'w') as file:
        config.write(file)


def load_config(config_file=Config.config_file):
    # Load Config
    CONFIG = configparser.ConfigParser()
    CONFIG.read(config_file)
    return (CONFIG)


# Function to load and save data into pickles
def pickle_it(action='load', filename=None, data=None):
    if filename is not None:
        filename = 'warden_monitor/' + filename
        filename = os.path.join(home_path(), filename)
    else:
        filename = 'warden_monitor/'
        filename = os.path.join(home_path(), filename)

    # list all pkl files at directory
    if action == 'list':
        files = os.listdir(filename)
        ret_list = [x for x in files if x.endswith('.pkl')]
        return (ret_list)

    if action == 'delete':
        try:
            os.remove(filename)
            return ('deleted')
        except Exception:
            return ('failed')

    if action == 'load':
        try:
            if os.path.getsize(filename) > 0:
                with open(filename, 'rb') as handle:
                    ld = pickle.load(handle)
                    return (ld)
            else:
                os.remove(filename)
                return ("file not found")

        except Exception as e:
            return ("file not found")
    else:
        with open(filename, 'wb') as handle:
            pickle.dump(data, handle, protocol=pickle.HIGHEST_PROTOCOL)
            return ("saved")


# Function to load and save data into json
def json_it(action='load', filename=None, data=None):
    filename = 'warden_monitor/' + filename
    filename = os.path.join(home_path(), filename)
    if action == 'delete':
        try:
            os.remove(filename)
            return ('deleted')
        except Exception:
            return ('failed')

    if action == 'load':
        try:
            if os.path.getsize(filename) > 0:
                with open(filename, 'r') as handle:
                    ld = json.load(handle)
                    return (ld)
            else:
                os.remove(filename)
                return ("file not found")

        except Exception as e:
            return ("file not found")
    else:
        # Serializing json
        json_object = json.dumps(data, indent=4)

        # Writing to sample.json
        with open(filename, "w") as handle:
            handle.write(json_object)
            return ("saved")


def fxsymbol(fx, output='symbol'):
    # Gets an FX 3 letter symbol and returns the HTML symbol
    # Sample outputs are:
    # "EUR": {
    # "symbol": "",
    # "name": "Euro",
    # "symbol_native": "",
    # "decimal_digits": 2,
    # "rounding": 0,
    # "code": "EUR",
    # "name_plural": "euros"
    filename = os.path.join(current_path(), 'static/json_files/currency.json')
    with open(filename) as fx_json:
        fx_list = json.load(fx_json)
    try:
        out = fx_list[fx][output]
    except Exception:
        if output == 'all':
            return (fx_list[fx])
        out = fx
    return (out)


def determine_docker_host_ip_address():
    cmd = "ip route show"
    import subprocess
    process = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()
    return str(output).split(' ')[2]


def runningInDocker():
    try:
        with open('/proc/self/cgroup', 'r') as procfile:
            for line in procfile:
                fields = line.strip().split('/')
                if 'docker' in fields:
                    return True

        return False

    except Exception:
        return False


# Serialize only objects that are json compatible
# This will exclude classes and methods
def safe_serialize(obj):

    def default(o):
        return f"{type(o).__qualname__}"

    return json.dumps(obj, default=default)


#  Check if a port at localhost is in use
def is_port_in_use(port: int) -> bool:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


def safe_filename(s):
    return ("".join([
        c for c in s if c.isalpha() or c.isdigit() or c == '_' or c == '-'
    ]).rstrip())