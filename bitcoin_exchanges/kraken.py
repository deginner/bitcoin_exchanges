import base64
import copy
import hashlib
import hmac
import json
import requests
import urllib
from moneyed import MultiMoney, Money

from exchange_util import exchange_config, ExchangeABC, ExchangeError, create_ticker

import time

REQ_TIMEOUT = 10  # seconds


def adjust_pair(pair):
    """
    The pair can be specified either in the "kraken" format
    (e.g. XXBTZUSD) or in the "bitfinex" format (e.g. btcusd).

    :return: a pair formated according to what kraken expects.
    """
    if pair[0] != 'X':
        half1 = pair[:3].upper()
        if half1 == 'BTC':
            half1 = 'XBT'
        pair = 'X%sZ%s' % (half1, pair[3:].upper())
    return pair


class Kraken(ExchangeABC):
    name = 'kraken'
    fiatcurrency = 'EUR'

    def __init__(self, key, secret):
        super(Kraken, self).__init__()
        self.key = key
        self.secret = secret

    def submit_request(self, method, params=None, pop='private', retry=0):
        """Submit request to Kraken"""
        if not params:
            params = {}
        path = '/0/%s/%s' % (pop, method)
        url = 'https://api.kraken.com'

        if pop == 'private':
            params['nonce'] = int(time.time() * 1000)
            data = urllib.urlencode(params)
            message = path + hashlib.sha256(str(params['nonce']) + data).digest()
            sign = base64.b64encode(hmac.new(base64.b64decode(self.secret),
                                             message, hashlib.sha512).digest())
            headers = {
                'API-Key': self.key,
                'API-Sign': sign
            }
            try:
                response = json.loads(requests.post(url + path, data=data, headers=headers, timeout=REQ_TIMEOUT).text)
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, ValueError) as e:
                raise ExchangeError('kraken', '%s %s while sending %r to %s' % (type(e), e, params, path))
            if "Invalid nonce" in response and retry < 3:
                return self.submit_request(method, params=params, pop=pop, retry=retry + 1)
            else:
                return response
        else:
            data = urllib.urlencode(params)
            try:
                return json.loads(requests.get(url + path + "?" + data, timeout=REQ_TIMEOUT).text)
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, ValueError) as e:
                raise ExchangeError('btce', '%s %s while sending %r to %s' % (type(e), e, params, path))

    def get_time(self):
        return self.submit_request('Time', pop='public')

    def get_info(self):
        return self.submit_request('Assets', pop='public')

    def get_pairs(self):
        return self.submit_request('AssetPairs', pop='public')

    def get_ticker(self, pair='XXBTZEUR'):
        pair = adjust_pair(pair)
        fullticker = self.submit_request('Ticker', {'pair': pair}, pop='public')
        ticker = fullticker['result'][pair]
        return create_ticker(ask=ticker['a'][0], bid=ticker['b'][0], timestamp=time.time(), volume=ticker['v'][1],
                             last=ticker['c'][0], high=ticker['h'][1], low=ticker['l'][1], currency='EUR')

    def get_ohlc(self, pair):
        return self.submit_request(method='OHLC', params={'pair': pair}, pop='public')

    def get_order_book(self, pair='XXBTZEUR'):
        pair = adjust_pair(pair)
        book = self.submit_request('Depth', {'pair': pair}, pop='public')
        return book['result'][pair]

    get_depth = get_order_book

    def get_trades(self, pair):
        return self.submit_request('Trades', {'pair': pair}, pop='public')

    def get_spread(self, pair='XXBTZEUR'):
        return self.submit_request('Spread', {'pair': pair}, pop='public')

    # private methods
    def cancel_order(self, oid):
        resp = self.submit_request('CancelOrder', {'txid': oid})
        if resp and 'result' in resp and 'count' in resp['result'] and resp['result']['count'] > 0:
            return True
        return False

    def cancel_orders(self, **kwargs):
        orders = self.get_open_orders()
        success = True
        for o in orders['open']:
            resp = self.cancel_order(o)
            if not resp:
                success = False
        return success

    def create_order(self, amount, price, otype, pair='XXBTZEUR', **kwargs):
        otype = 'buy' if otype == 'bid' else 'sell'
        if not isinstance(amount, str):
            amount = str(amount)
        if not isinstance(price, str):
            price = str(price)
        options = {'type': otype, 'volume': amount, 'price': price, 'pair': pair, 'ordertype': 'limit'}
        options.update(kwargs)
        resp = self.submit_request('AddOrder', options)
        if 'error' in resp and len(resp['error']) > 0:
            raise ExchangeError('kraken', 'unable to create order %r for reason %r' % (options, resp['error']))
        elif 'result' in resp and 'txid' in resp['result'] and len(resp['result']['txid']) > 0:
            return str(resp['result']['txid'][0])

    def get_closed_orders(self):
        return self.submit_request('ClosedOrders', {'trades': 'True'})

    def get_balance(self, btype='total'):
        tbal = self.get_total_balance()
        if 'result' in tbal:
            total = MultiMoney()
            for cur in tbal['result']:
                if cur == 'XXBT':
                    total += Money(amount=tbal['result']['XXBT'])
                elif cur == 'ZEUR':
                    total += (Money(amount=tbal['result']['ZEUR'], currency='EUR'))
                elif cur == 'ZUSD':
                    total += (Money(amount=tbal['result']['ZUSD'], currency='USD'))
        else:
            total = MultiMoney(Money(), Money(currency='USD'))

        if btype == 'total':
            return total

        available = copy.copy(total)
        oorders = self.get_open_orders()
        if oorders and 'open' in oorders:
            for oid in oorders['open']:
                order = oorders['open'][oid]
                if order['descr']['type'] == 'buy':
                    vol = Money(amount=order['vol'], currency='EUR')
                    volexec = Money(amount=order['vol_exec'], currency='EUR')
                    available -= (vol - volexec)
                else:
                    vol = Money(amount=order['vol']) / Money(order['descr']['price'])
                    volexec = Money(amount=order['vol_exec']) / Money(order['descr']['price'])
                    available -= (vol - volexec)

        if btype == 'available':
            return available
        else:
            return total, available

    def get_balance_by_asset(self):
        return self.submit_request('Balance')

    def get_total_balance(self):
        return self.submit_request('Balance')

    def get_open_orders(self):
        oorders = self.submit_request('OpenOrders', {'trades': 'True'})
        if 'result' in oorders:
            return oorders['result']

    def get_trades_hstory(self):
        return self.submit_request('TradesHistory', {'trades': 'True'})

    get_transactions = get_trades_hstory

    def get_open_positions(self, list_of_txids=None, docalcs=True):
        """
        :param list list_of_txids:
        :param bool docalcs: include, or not, profit/loss calculations
        """
        return self.submit_request('OpenPositions',
                                   {'docalcs': str(docalcs), 'txid': list_of_txids})

    def query_orders(self, list_of_txids=None):
        list_of_txids = list_of_txids or []
        return self.submit_request('QueryOrders', {'trades': 'True', 'txid': list_of_txids})

    def query_trades(self, list_of_txids=None):
        """
        :param list list_of_txids:
        """
        list_of_txids = list_of_txids or []
        return self.submit_request('QueryTrades', {'trades': 'True', 'txid': list_of_txids})


exchange = Kraken(key=exchange_config['kraken']['api_keys']['key'],
                  secret=exchange_config['kraken']['api_keys']['secret'])
