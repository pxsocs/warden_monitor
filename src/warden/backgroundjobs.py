from pricing_engine.engine import realtime_price
from utils import pickle_it


def get_btc_price():
    price = realtime_price('BTC')
    pickle_it('save', 'btc_price.pkl', price)
    return (price)
