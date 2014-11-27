import base64
import copy
import hashlib
import hmac
import json
import requests
import urllib
from requests.exceptions import Timeout, ConnectionError
from moneyed import MultiMoney, Money

from exchange_util import exchange_config, ExchangeABC, ExchangeError, create_ticker, BLOCK_ORDERS, MyOrder

import time


baseUrl = 'https://api.kraken.com'
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

    def submit_private_request(self, method, params=None, retry=0):
        """Submit request to Kraken"""
        if not params:
            params = {}
        path = '/0/private/%s' % method

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
            response = json.loads(requests.post(baseUrl + path, data=data, headers=headers,
                                                timeout=REQ_TIMEOUT).text)
        except (ConnectionError, Timeout, ValueError) as e:
            raise ExchangeError('kraken', '%s %s while sending %r to %s' % (type(e), e, params, path))
        if "Invalid nonce" in response and retry < 3:
            return self.submit_private_request(method, params=params, retry=retry + 1)
        else:
            return response

    @classmethod
    def submit_public_request(cls, method, params=None):
        path = '/0/public/%s' % method
        data = urllib.urlencode(params)
        try:
            return json.loads(requests.get(baseUrl + path + "?" + data, timeout=REQ_TIMEOUT).text)
        except (ConnectionError, Timeout, ValueError) as e:
            raise ExchangeError('btce', '%s %s while sending %r to %s' % (type(e), e, params, path))

    @classmethod
    def get_time(cls):
        return cls.submit_public_request('Time')

    @classmethod
    def get_info(cls):
        return cls.submit_public_request('Assets')

    @classmethod
    def get_pairs(cls):
        return cls.submit_public_request('AssetPairs')

    @classmethod
    def get_ticker(cls, pair='XXBTZEUR'):
        pair = adjust_pair(pair)
        fullticker = cls.submit_public_request('Ticker', {'pair': pair})
        ticker = fullticker['result'][pair]
        return create_ticker(ask=ticker['a'][0], bid=ticker['b'][0], timestamp=time.time(), volume=ticker['v'][1],
                             last=ticker['c'][0], high=ticker['h'][1], low=ticker['l'][1], currency='EUR')

    @classmethod
    def get_ohlc(cls, pair):
        return cls.submit_public_request(method='OHLC', params={'pair': pair})

    @classmethod
    def get_order_book(cls, pair='XXBTZEUR'):
        pair = adjust_pair(pair)
        book = cls.submit_public_request('Depth', {'pair': pair})
        return book['result'][pair]

    @classmethod
    def get_trades(cls, pair):
        return cls.submit_public_request('Trades', {'pair': pair})

    @classmethod
    def get_spread(cls, pair='XXBTZEUR'):
        return cls.submit_public_request('Spread', {'pair': pair})

    # private methods
    def cancel_order(self, oid):
        resp = self.submit_private_request('CancelOrder', {'txid': oid})
        if resp and 'result' in resp and 'count' in resp['result'] and resp['result']['count'] > 0:
            return True
        return False

    def cancel_orders(self, **kwargs):
        orders = self.get_open_orders()
        success = True
        for o in orders:
            resp = self.cancel_order(o.order_id)
            if not resp:
                success = False
        return success

    def create_order(self, amount, price, otype, pair='XXBTZEUR', **kwargs):
        if BLOCK_ORDERS:
            return "order blocked"
        otype = 'buy' if otype == 'bid' else 'sell'
        if not isinstance(amount, str):
            amount = str(amount)
        if not isinstance(price, str):
            price = str(price)
        options = {'type': otype, 'volume': amount, 'price': price, 'pair': pair, 'ordertype': 'limit'}
        options.update(kwargs)
        resp = self.submit_private_request('AddOrder', options)
        if 'error' in resp and len(resp['error']) > 0:
            raise ExchangeError('kraken', 'unable to create order %r for reason %r' % (options, resp['error']))
        elif 'result' in resp and 'txid' in resp['result'] and len(resp['result']['txid']) > 0:
            return str(resp['result']['txid'][0])

    def get_closed_orders(self):
        return self.submit_private_request('ClosedOrders', {'trades': 'True'})

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
        for o in oorders:
            if o.side == 'bid':
                available -= o.price * o.amount.amount
            else:
                available -= o.amount

        if btype == 'available':
            return available
        else:
            return total, available

    def get_balance_by_asset(self):
        return self.submit_private_request('Balance')

    def get_total_balance(self):
        return self.submit_private_request('Balance')

    def get_open_orders(self):
        oorders = self.submit_private_request('OpenOrders', {'trades': 'True'})
        orders = []
        if 'result' in oorders and 'open' in oorders['result']:
            rawos = oorders['result']['open']
            for id, o in rawos.iteritems():
                side = 'ask' if o['descr']['type'] == 'sell' else 'bid'
                amount = Money(o['vol']) - Money(o['vol_exec'])
                orders.append(MyOrder(Money(o['descr']['price'], self.fiatcurrency), amount, side, self.name, str(id)))
        return orders

    def get_trades_hstory(self):
        return self.submit_private_request('TradesHistory', {'trades': 'True'})

    get_transactions = get_trades_hstory

    def get_open_positions(self, list_of_txids=None, docalcs=True):
        """
        :param list list_of_txids:
        :param bool docalcs: include, or not, profit/loss calculations
        """
        return self.submit_private_request('OpenPositions',
                                   {'docalcs': str(docalcs), 'txid': list_of_txids})

    def query_orders(self, list_of_txids=None):
        list_of_txids = list_of_txids or []
        return self.submit_private_request('QueryOrders', {'trades': 'True', 'txid': list_of_txids})

    def query_trades(self, list_of_txids=None):
        """
        :param list list_of_txids:
        """
        list_of_txids = list_of_txids or []
        return self.submit_private_request('QueryTrades', {'trades': 'True', 'txid': list_of_txids})

    def get_deposit_methods(self):
        return self.submit_private_request('DepositMethods', {'asset': 'BTC'})

    def get_deposit_address(self):
        addys = self.submit_private_request('DepositAddresses', {'asset': 'BTC', 'method': 'Bitcoin'})
        if len(addys['error']) > 0:
            raise ExchangeError('kraken', addys['error'])
        for addy in addys['result']:
            if int(addy['expiretm']) < time.time() + 1440:
                return str(addy['address'])
        raise ExchangeError('kraken', "unable to get deposit address")

eclass = Kraken
exchange = Kraken(key=exchange_config['kraken']['api_creds']['key'],
                  secret=exchange_config['kraken']['api_creds']['secret'])
