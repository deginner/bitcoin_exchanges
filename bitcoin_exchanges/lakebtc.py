import base64
import hashlib
import hmac
import json
import requests
from requests.exceptions import Timeout, ConnectionError

from moneyed.classes import Money, MultiMoney
import time

from exchange_util import ExchangeABC, create_ticker, ExchangeError, exchange_config, BLOCK_ORDERS, MyOrder


BASE_URL = 'https://www.lakebtc.com/api_v1/'
REQ_TIMEOUT = 10  # seconds


class Lakebtc(ExchangeABC):
    name = 'lakebtc'
    fiatcurrency = 'CNY'

    def __init__(self, key, secret):
        super(Lakebtc, self).__init__()
        self.key = key
        self.secret = secret

    def lakebtc_encode(self, params):
        mess = "tonce=%d&accesskey=%s&requestmethod=post&id=%d&method=%s&params=%s" % \
               (params['tonce'], self.key, 1, params['method'], ",".join(params['params']))
        result = hmac.new(self.secret, mess, hashlib.sha1).hexdigest()
        return result

    def lakebtc_request(self, method, params=None):
        if params is None:
            params = {'params': []}
        params['method'] = method
        params['tonce'] = int(time.time() * 1000000)
        params['requestmethod'] = 'post'
        params['id'] = 1

        auth_string = 'Basic %s' % base64.b64encode("%s:%s" % (self.key, self.lakebtc_encode(params)))
        headers = {'Authorization': auth_string, 'Json-Rpc-Tonce': params['tonce']}
        try:
            response = requests.post(url=BASE_URL,
                                     data=json.dumps(params),
                                     headers=headers,
                                     timeout=REQ_TIMEOUT)
        except (ConnectionError, Timeout, ValueError) as e:
            raise ExchangeError('lakebtc', '%s %s while sending %r' % (type(e), str(e), params))
        if response.status_code == 200:
            return response.json()
        else:
            raise ExchangeError('lakebtc', '%s %s while sending %r' % (response.status_code, response.text, params))

    def cancel_order(self, order_id, symbol='btc_cny'):
        params = {'params': [order_id]}
        resp = self.lakebtc_request('cancelOrder', params)
        if resp and 'result' in resp:
            return resp['result']
        return False

    def cancel_orders(self, symbol='btc_cny', **kwargs):
        oorders = self.get_open_orders(symbol)
        canceled = True
        for o in oorders:
            result = self.cancel_order(str(o['id']), symbol)
            if not result:
                canceled = False
        return canceled

    def create_order(self, amount, price, otype, symbol='btc_cny'):
        if BLOCK_ORDERS:
            return "order blocked"
        if otype == 'bid':
            otype = 'buyOrder'
        elif otype == 'ask':
            otype = 'sellOrder'
        else:
            raise Exception('unknown side %r' % otype)

        params = {
            'params': ["{:0.2f}".format(float(price)), "{:0.3f}".format(float(amount)), self.fiatcurrency]
        }
        data = self.lakebtc_request(otype, params)
        if 'id' in data:
            return str(data['id'])
        raise ExchangeError('lakebtc', 'unable to create order %r response was %r' % (params, data))

    def get_balance(self, btype='total'):
        data = self.lakebtc_request('getAccountInfo')
        balance = MultiMoney()
        for cur, amount in data['balance'].iteritems():
            balance += Money(data['balance'][cur], currency=cur)
        if btype == 'total':
            return balance
        available = balance - self._get_unavailable_balance()
        if btype == 'available':
            return available
        return balance, available

    def _get_unavailable_balance(self):
        orders = self.get_open_orders()
        unavailable = MultiMoney()
        for o in orders:
            if o.side == 'ask':
                unavailable += o.amount
            else:
                unavailable += o.price * o.amount.amount
        return unavailable

    def get_open_orders(self, symbol='btc_usd'):
        rawos = self.lakebtc_request('getOrders')
        orders = []
        for o in rawos:
            side = 'ask' if o['category'] == 'sell' else 'bid'
            orders.append(MyOrder(Money(o['ppc'], self.fiatcurrency), Money(o['amount']), side,
                          self.name, str(o['id'])))
        return orders

    @classmethod
    def get_order_book(cls, pair='btc_cny', **kwargs):
        try:
            return requests.get(BASE_URL + 'bcorderbook_cny', timeout=REQ_TIMEOUT).json()
        except (ConnectionError, Timeout, ValueError) as e:
            raise ExchangeError('lakebtc', '%s %s while sending get_order_book' % (type(e), str(e)))

    @classmethod
    def get_ticker(cls, pair='btc_cny'):
        try:
            rawtick = requests.get(BASE_URL + 'ticker', timeout=REQ_TIMEOUT).json()
        except (ConnectionError, Timeout, ValueError) as e:
            raise ExchangeError('lakebtc', '%s %s while sending get_ticker to lakebtc' % (type(e), str(e)))

        return create_ticker(bid=rawtick['CNY']['bid'], ask=rawtick['CNY']['ask'],
                             high=rawtick['CNY']['high'], low=rawtick['CNY']['low'],
                             volume=rawtick['CNY']['volume'], last=rawtick['CNY']['last'],
                             timestamp=time.time(), currency='CNY')

    def get_transactions(self, limit=None, status=1, current_page=1, page_length=200, symbol='btc_cny', timestamp=None):
        """

        :param limit:
        :param status:
        :param current_page:
        :param page_length:
        :param symbol:
        :param timestamp: The timestamp to begin searching at. Default is 24 hours ago.
        :return:
        """
        if timestamp is None:
            timestamp = time.time() - 86400  # 24 hours
        params = {'params': [str(timestamp)]}
        resp = self.lakebtc_request('getTrades', params)
        if resp and isinstance(resp, list):
            return resp
        raise ExchangeError('lakebtc', 'unable to get transactions. response was %r' % resp)

    def get_deposit_address(self):
        data = self.lakebtc_request('getAccountInfo')
        return str(data['profile']['btc_deposit_addres'])


eclass = Lakebtc
exchange = Lakebtc(exchange_config['lakebtc']['api_creds']['key'],
                   exchange_config['lakebtc']['api_creds']['secret'])
