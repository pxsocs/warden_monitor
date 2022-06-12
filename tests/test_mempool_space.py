import unittest
import requests
import configparser

# Include main app path for importing
import sys

sys.path.append('../src/warden')

# App specific imports
from config import Config
from mempoolspace import get_addresses


class TestMPS(unittest.TestCase):
    print("Starting Mempool Space tests...")

    # This runs before all tests
    @classmethod
    def setUpClass(cls):
        config_file = Config.config_file
        cls.config = configparser.ConfigParser()
        cls.config.read(config_file)

    # This runs after all tests
    @classmethod
    def tearDownClass(cls):
        pass

    # Tests if mempool space address is reachable
    def is_mempool_space_reachable(self):
        # Get list of addresses from mempoolspace.py
        mp_addresses = get_addresses()
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
                result = requests.get(public_url)
                print("Request resulted in: " + str(result))
                # got response back?
                self.assertIsInstance(result, requests.models.Response)
                # got code ok back?
                self.assertEqual(result.ok, True)

            # Test private instance
            print(
                "Testing if personal instances of mempool space is reachable..."
            )
            for personal_url in mp_addresses['private']:
                print(f"Testing {personal_url}")
                result = requests.get(personal_url)
                print("Request resulted in: " + str(result))
                # got response back?
                self.assertIsInstance(result, requests.models.Response)
                # got code ok back?
                self.assertEqual(result.ok, True)

    def test_get_address(self):
        # Random Test address
        address = '1wiz18xYmhRX6xStj2b9t1rwWX4GKUgpv'
        print("Gathering address info for: " + address)

        # got response back?
        # self.assertIsInstance(result, requests.models.Response)
        # Got code ok back?
        # self.assertEqual(result.ok, True)
