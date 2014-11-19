from bitcoin_exchanges.exchange_util import ExchangeError
import requests
from requests.exceptions import Timeout, ConnectionError


baseURL = "https://shapeshift.io/"


def send_shapeshift(path, values=None, pog='get'):
    """Send message to URL and return response contents
    Raises ExchangeError"""
    url = baseURL + path
    if pog == 'post':
        try:
            resp = requests.post(url, values).json()
        except (ConnectionError, Timeout, ValueError) as e:
            raise ExchangeError('shapeshift', '%s %s while sending %r' % (type(e), str(e), values))
    else:
        try:
            resp = requests.get(url).json()
        except (ConnectionError, Timeout, ValueError) as e:
            raise ExchangeError('shapeshift', '%s %s while sending %r' % (type(e), str(e), values))
    return resp


def rate(pair='ltc_btc'):
    return send_shapeshift('rate/%s' % pair)


def deposit_limit(pair='ltc_btc'):
    return send_shapeshift('limit/%s' % pair)


def recent_transactions(maxt=10):
    return send_shapeshift('recenttx/%s' % maxt)


def get_order_status(address):
    return send_shapeshift('txStat/%s' % address)


def get_time_remaining(address):
    return send_shapeshift('timeremaining/%s' % address)


def get_quote(address, pair='ltc_btc', amount=None):
    values = {'withdrawal': address, 'pair': pair}
    path = 'shift/'
    if amount is not None:
        values['amount'] = amount
        path = 'sendamount/'
    return send_shapeshift(path, values, pog='post')
