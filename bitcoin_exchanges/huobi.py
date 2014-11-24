import hashlib
import json
import time
import requests
from requests.exceptions import Timeout, ConnectionError

from moneyed.classes import Money, MultiMoney

from exchange_util import ExchangeABC, create_ticker, ExchangeError, exchange_config, BLOCK_ORDERS


BASE_URL = 'https://api.huobi.com/apiv2.php'
REQ_TIMEOUT = 10  # seconds


class Huobi(ExchangeABC):
    name = 'huobi'
    fiatcurrency = 'USD'

    def __init__(self, key, secret):
        super(Huobi, self).__init__()
        self.key = key
        self.secret = secret

    def huobi_encode(self, params):
        postData = ''
        params['secret_key'] = self.secret
        for k in sorted(params.keys()):
            postData += '%s=%s&' % (k, params[k])
        return hashlib.md5(postData[0:-1]).hexdigest().lower()

    def huobi_request(self, endpoint, params=None):
        params = params or {}
        params['method'] = endpoint
        params['access_key'] = self.key
        params['created'] = int(time.time())
        params['sign'] = self.huobi_encode(params)
        if 'secret_key' in params:
            del params['secret_key']

        headers = {'contentType': 'application/x-www-form-urlencoded'}
        try:
            response = requests.post(url=BASE_URL,
                                     data=params,
                                     headers=headers,
                                     timeout=REQ_TIMEOUT)
        except (ConnectionError, Timeout) as e:
            raise ExchangeError('huobi', '%s error while sending %r' % (str(e), params))
        if response.status_code != 200:
            raise ExchangeError('huobi', '%s while sending %r' % (str(response['error_code']), params))
        try:
            resp = json.loads(response.text)
        except ValueError as e:
            raise ExchangeError('huobi', '%s error while sending %r, '
                                         'response is: %s' % (type(e), params, response.text))
        if 'result' in resp and resp['result'] == 'fail':
            if resp['code'] in error_codes:
                raise ExchangeError('huobi', '%s while sending %r' % (str(error_codes[resp['code']]), params))
            else:
                raise ExchangeError('huobi', '%s while sending %r' % (str(resp), params))
        return resp

    def cancel_order(self, order_id):
        params = {'coin_type': 1, 'id': order_id}
        resp = self.huobi_request('cancel_order', params)
        if resp and 'result' in resp and 'uccess' in resp['result']:
            return True
        return False

    def cancel_orders(self, **kwargs):
        oorders = self.get_open_orders()
        canceled = True
        for o in oorders:
            result = self.cancel_order(o['id'])
            if not result:
                canceled = False
        return canceled

    def create_order(self, amount, price, otype):
        if BLOCK_ORDERS:
            return "order blocked"
        if otype == 'bid':
            otype = 'buy'
        elif otype == 'ask':
            otype = 'sell'
        else:
            raise Exception('unknown side %r' % otype)

        # avoid round numbers to prevent hashing/auth issues
        price = float(price)
        amount = float(amount)
        if round(price) == price:
            if otype == 'buy':
                price -= 0.01
            else:
                price += 0.01
        if round(amount) == amount:
            amount += 0.001

        params = {
            'coin_type': 1,
            'price': round(price, 2),
            'amount': round(amount, 4),
        }
        data = self.huobi_request(otype, params)
        if 'result' in data and 'uccess' in data['result']:
            return str(data['id'])
        raise ExchangeError('huobi', 'unable to create order %r response was %r' % (params, data))

    def get_balance(self, btype='total'):
        data = self.huobi_request('get_account_info')
        avail = MultiMoney(Money(data['available_btc_display']), Money(data['available_cny_display'], 'CNY'))
        frozen = MultiMoney(Money(data['frozen_btc_display']), Money(data['frozen_cny_display'], 'CNY'))
        if btype == 'total':
            return avail + frozen
        elif btype == 'available':
            return avail
        return avail + frozen, avail

    def get_open_orders(self):
        params = {'coin_type': 1}
        return self.huobi_request('get_orders', params)

    @classmethod
    def get_order_book(cls, pair='btc_usd', **kwargs):
        try:
            return requests.get('https://market.huobi.com/staticmarket/depth_btc_json.js', timeout=REQ_TIMEOUT).json()
        except ValueError as e:
            raise ExchangeError('huobi', '%s %s while sending get_order_book' % (type(e), str(e)))

    @classmethod
    def get_ticker(cls, pair='btc_usd'):
        try:
            rawtick = requests.get('https://market.huobi.com/staticmarket/ticker_btc_json.js',
                                   timeout=REQ_TIMEOUT).json()
        except (ConnectionError, Timeout, ValueError) as e:
            raise ExchangeError('huobi', '%s %s while sending get_ticker to huobi' % (type(e), str(e)))

        return create_ticker(bid=rawtick['ticker']['buy'], ask=rawtick['ticker']['sell'],
                             high=rawtick['ticker']['high'], low=rawtick['ticker']['low'],
                             volume=rawtick['ticker']['vol'], last=rawtick['ticker']['last'],
                             timestamp=time.time(), currency='CNY')

    def get_transactions(self, limit=None):
        # huobi appears not to support get_transactions
        return []

    def get_deposit_address(self):
        return exchange_config['huobi']['address']


error_codes = {
    1: 'Server Error',
    2: 'There is not enough yuan',
    3: 'Transaction has started, can not be started again',
    4: 'Transaction has ended',
    10: 'There is not enough bitcoins',
    11: 'Not enough LTC',
    18: 'Incorrect payment password',
    26: 'The order does not exist',
    41: 'The order has ended, can not be modified',
    42: 'The order has been canceled, can not be modified',
    44: 'Transaction price is too low',
    45: 'Transaction prices are too high',
    46: 'The minimum order size is 0.001',
    47: 'Too many requests',
    55: '10% higher than market price is not allowed',
    56: '10% lower than market price is not allowed',
    64: 'Invalid request',
    65: 'Invalid method',
    66: 'Access key validation fails',
    67: 'Private key authentication fails',
    68: 'Invalid price',
    69: 'Invalid amount',
    70: 'Invalid submission time',
    71: 'Request overflow',
    87: 'The number of transactions is less than 0.1 BTC, please do not bid the price higher than the price of the 1%',
    88: 'The number of transactions is less than 0.1 BTC, please do not sell below the market price of a 1%',
    89: 'Buying price cannot exceed 1% of market price when transaction amount is less than 0.1 BTC.',
    90: 'Selling price cannot be lower 1% of market price when transaction amount is less than 0.1 BTC.',
    91: 'Invalid type',
    92: 'Buy price cannot be higher 10% than market price.',
    93: 'Sell price cannot be lower 10% than market price.',
    97: 'Please enter payment password.',
    103: 'annoying, undocumented, and happens all of the time on create_order',
    107: 'Order is exist.',
}


eclass = Huobi
exchange = Huobi(exchange_config['huobi']['api_creds']['key'],
                 exchange_config['huobi']['api_creds']['secret'])
