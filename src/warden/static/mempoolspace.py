from distutils.command.config import config
from utils import load_config

config = load_config()


def get_addresses():
    # Get addresses from config and returns a dictionary with public
    # and private addresses
    path_items = config.items("MAIN")
    private_list = []
    public_list = []
    for key, path in path_items:
        if 'mspace_public' in key:
            public_list.append(path)
        if 'mspace_personal' in key:
            private_list.append(path)
    return {'public': public_list, 'private': private_list}