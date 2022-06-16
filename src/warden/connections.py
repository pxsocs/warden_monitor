import urllib
import requests
import logging
from time import time
import socket
from datetime import datetime
from utils import load_config, pickle_it
import concurrent.futures
from concurrent.futures import wait, ALL_COMPLETED


# Checks for internet conection [7]
# Saved to: internet_connected.pkl
# Returns: True / False
def internet_connected(host="8.8.8.8", port=53, timeout=3):
    """
    Host: 8.8.8.8 (google-public-dns-a.google.com)
    OpenPort: 53/tcp
    Service: domain (DNS/TCP)
    """
    connected = False
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        connected = True
    except socket.error as ex:
        connected = False
    pickle_it('save', 'diags_internet_connected.pkl', connected)
    return (connected)


def test_tor():
    response = {}
    session = requests.session()
    try:
        time_before = time()  # Save Ping time to compare
        r = session.get("https://api.myip.com")
        time_after = time()
        pre_proxy_ping = time_after - time_before
        pre_proxy = r.json()
    except Exception as e:
        pre_proxy = pre_proxy_ping = "Connection Error: " + str(e)

    PORTS = ['9050', '9150']

    # Activate TOR proxies
    for PORT in PORTS:
        session.proxies = {
            "http": "socks5h://localhost:" + PORT,
            "https": "socks5h://localhost:" + PORT,
        }
        try:
            failed = False
            time_before = time()  # Save Ping time to compare
            r = session.get("https://api.myip.com")
            time_after = time()
            post_proxy_ping = time_after - time_before
            post_proxy_ratio = post_proxy_ping / pre_proxy_ping
            post_proxy = r.json()

            if pre_proxy["ip"] != post_proxy["ip"]:
                response = {
                    "pre_proxy": pre_proxy,
                    "post_proxy": post_proxy,
                    "post_proxy_ping":
                    "{0:.2f} seconds".format(post_proxy_ping),
                    "pre_proxy_ping": "{0:.2f} seconds".format(pre_proxy_ping),
                    "difference": "{0:.2f}".format(post_proxy_ratio),
                    "status": True,
                    "port": PORT,
                    "last_refresh":
                    datetime.now().strftime('%d-%b-%Y %H:%M:%S')
                }
                pickle_it('save', 'tor.pkl', response)
                return response
        except Exception as e:
            failed = True
            post_proxy_ping = post_proxy = "Failed checking TOR status. Error: " + str(
                e)

        if not failed:
            break

    response = {
        "pre_proxy": pre_proxy,
        "post_proxy": post_proxy,
        "post_proxy_ping": post_proxy_ping,
        "pre_proxy_ping": pre_proxy_ping,
        "difference": "-",
        "status": False,
        "port": "failed",
        "last_refresh": None,
    }

    pickle_it('save', 'tor.pkl', response)
    session.close()
    return response


def tor_request(url, tor_only=False, method="get", headers=None):
    # Tor requests takes arguments:
    # url:       url to get or post
    # tor_only:  request will only be executed if tor is available
    # method:    'get or' 'post'
    # Store TOR Status here to avoid having to check on all http requests

    if not 'http' in url:
        url = 'http://' + url
    TOR = pickle_it('load', 'tor.pkl')
    if TOR == 'file not found':
        try:
            TOR = test_tor()
        except Exception:
            TOR = {
                "status": False,
                "port": "failed",
                "last_refresh": None,
            }

    # Do not use Tor for Local Network requests
    if '.local' in url or '127.0.0.1' in url or 'localhost' in url:
        try:
            if method == "get":
                request = requests.get(url, timeout=20)
            if method == "post":
                request = requests.post(url, timeout=20)
            return (request)

        except requests.exceptions.ConnectionError:
            return "ConnectionError"

    if TOR["status"] is True:
        try:
            # Activate TOR proxies
            session = requests.session()
            session.proxies = {
                "http": "socks5h://localhost:" + TOR['port'],
                "https": "socks5h://localhost:" + TOR['port'],
            }
            if method == "get":
                if headers:
                    request = session.get(url, timeout=20, headers=headers)
                else:
                    request = session.get(url, timeout=20)
            if method == "post":
                request = session.post(url, timeout=20)

            session.close()
        except (
                requests.exceptions.ConnectionError,
                requests.exceptions.ReadTimeout,
        ):
            return "ConnectionError"
    else:
        if tor_only:
            return "Tor not available"
        try:
            if method == "get":
                request = requests.get(url, timeout=10)
            if method == "post":
                request = requests.post(url, timeout=10)

        except requests.exceptions.ConnectionError:
            return "ConnectionError"

    return request


def url_parser(url):
    # Parse it
    from urllib.parse import urlparse
    parse_object = urlparse(url)
    scheme = 'http' if parse_object.scheme == '' else parse_object.scheme
    if parse_object.netloc != '':
        url = scheme + '://' + parse_object.netloc + '/'
    if not url.startswith('http'):
        url = 'http://' + url
    if url[-1] != '/':
        url += '/'

    return (url)
