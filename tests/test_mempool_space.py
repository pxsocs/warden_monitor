from audioop import add
import unittest
import configparser
import json

# Include main app path for importing
import sys

sys.path.append('../src/warden')

# App specific imports
from connections import url_parser
from config import Config
from mempoolspace import (mp_urls, check_api_health, get_address_utxo,
                          xpub_derive, xpub_balances)
from utils import pickle_it


class TestMPS(unittest.TestCase):
    print("Starting Mempool Space tests...")

    # This runs before all tests
    @classmethod
    def setUpClass(cls):
        print("Loading Config...")
        config_file = Config.config_file
        cls.config = configparser.ConfigParser()
        cls.config.read(config_file)

    # This runs after all tests
    @classmethod
    def tearDownClass(cls):
        pass

    # Tests if mempool space address is reachable
    def test_is_mempool_space_reachable(self):
        print("Testing connectivity to API...")
        at_least_one_public = False
        at_least_one_private = False
        # Get list of addresses from mempoolspace.py
        mp_addresses = mp_urls()
        print("The list of addresses found is:")
        print(mp_addresses)

        # Check if a public instance of mempool space is allowed to be used
        use_public = self.config.getboolean('MAIN', 'mspace_allow_public')
        print("")
        print("Use public instance of mempool space: " + str(use_public))

        # Test public instance
        if use_public is True:
            print(
                "Testing if public instance of mempool space is reachable...")
            for public_url in mp_addresses['public']:
                print(f"Testing {public_url}")
                result = check_api_health(public_url, public=True)
                if result == True:
                    print("[OK] Connection to " + public_url +
                          " was successful")
                    at_least_one_public = True
                else:
                    print("[X] Connection to " + public_url +
                          " was not successful")

            # Test private instance
            print(
                "Testing if personal instances of mempool space is reachable..."
            )
            for personal_url in mp_addresses['private']:
                print(f"Testing {personal_url}")
                result = check_api_health(personal_url, public=False)
                # got code ok back?
                if result == True:
                    print("[OK] Connection to " + personal_url +
                          " was successful")
                    at_least_one_private = True
                else:
                    print("[X] Connection to " + personal_url +
                          " was not successful")

            # Got at least one connection
            self.assertEqual(at_least_one_public, True)
            self.assertEqual(at_least_one_private, True)
            print(
                "At least one public and one private connections were successful"
            )
            print("Latest Status:")
            server_status = pickle_it('load', 'mps_server_status.pkl')
            print(
                json.dumps(server_status,
                           indent=4,
                           sort_keys=True,
                           default=str))

    def test_add_remove_url(self):
        url = 'mempoolspace_tester_url.com'
        # Clean url
        url = url_parser(url)
        # Include url in config
        mp_urls(action='add', url=url, public=True)
        # check that it is inside config
        config_file = Config.config_file
        config = configparser.ConfigParser()
        config.read(config_file)
        path_items = config.items("MAIN")
        found = False
        for key, path in path_items:
            if url in path:
                print("Address " + url + " was added to config")
                found = True
                break
        if found == False:
            # Raise an issue
            raise Exception('Address was not added to config')

        # Remove url from config
        mp_urls(action='remove', url=url)
        found = False
        config_file = Config.config_file
        config = configparser.ConfigParser()
        config.read(config_file)
        path_items = config.items("MAIN")
        for key, path in path_items:
            if url in path:
                print(path)
                found = True
        if found == True:
            # Raise an issue
            raise Exception('Address was not removed from config')

    def test_get_address(self):
        # Random Test address
        # https://mempool.space/api/address/1wiz18xYmhRX6xStj2b9t1rwWX4GKUgpv/txs
        # https://mempool.space/api/address/1wiz18xYmhRX6xStj2b9t1rwWX4GKUgpv/txs
        address = '1wiz18xYmhRX6xStj2b9t1rwWX4GKUgpv'
        print("Gathering address info for: " + address)
        url = 'https://mempool.space/'
        address_info = get_address_utxo(url, address)
        print(address_info)

    def test_xpub_derivation(self):
        # Sample xpub with balances
        xpub = "xpub6C9vKwUFiBLbQKS6mhEAtEYhS24sVz8MkvMjxQSECTZVCnFmy675zojLthvXVuQf15RT6ggmt7PTgLBV2tLHHdJenoEkNWe5VPBETncxf2q"
        n_of_add = 5
        print("Deriving " + str(n_of_add) + " addresses from " + xpub)
        lst = xpub_derive(xpub=xpub,
                          number_of_addresses=n_of_add,
                          start_number=0,
                          output_type='P2WPKH')
        print(lst)
        print("Deriving " + str(n_of_add) + " addresses from " + xpub)
        lst = xpub_derive(xpub=xpub,
                          number_of_addresses=n_of_add,
                          start_number=0,
                          output_type='P2PKH')
        print(lst)

    def test_get_xpub_balances(self):
        # Sample xpub with balances
        xpub = "xpub6C9vKwUFiBLbQKS6mhEAtEYhS24sVz8MkvMjxQSECTZVCnFmy675zojLthvXVuQf15RT6ggmt7PTgLBV2tLHHdJenoEkNWe5VPBETncxf2q"
        url = 'https://mempool.space/'
        balances = xpub_balances(url, xpub)
        print("Balances and addresses for xpub: " + xpub)
        print(balances)


if __name__ == '__main__':
    print("Running tests... Please wait...")

    unittest.main()
