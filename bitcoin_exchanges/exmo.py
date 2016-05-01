import hmac
import json
import time
import urllib
import httplib
import hashlib
from hashlib import sha512
import requests
from requests.exceptions import Timeout, ConnectionError
from moneyed.classes import Money, MultiMoney

from exchange_util import ExchangeABC, create_ticker, ExchangeError, exchange_config, BLOCK_ORDERS, MyOrder


BASE_URL = 'https://api.exmo.com/v1/'
REQ_TIMEOUT = 10  # seconds


class Exmo(ExchangeABC):
    name = 'exmo'
    
    def __init__(self, key, secret):
        super(Exmo, self).__init__()
        self.key = key
        self.secret = secret

    def exmo_request(self, endpoint, params=None):
        params = params or {}
        nonce = int(round(time.time()*1000))
        params["nonce"] = nonce
        params = urllib.urlencode(params)
        sig = hmac.new(self.secret, digestmod=hashlib.sha512)
        sig.update(params)
        sign = sig.hexdigest()
        
        headers = {
            'Content-type':'application/x-www-form-urlencoded',
            'Key': self.key,
            'Sign': sign
        }

        response = None
        conn = httplib.HTTPSConnection("api.exmo.com")
        conn.request("POST", "/v1/" + endpoint, params, headers)
        response = conn.getresponse()

        return json.load(response)
        conn.close()

#        while response is None:
#            try:
#                response = requests.post(url=BASE_URL + endpoint,
#                                         params=params, headers=headers,
#                                         timeout=REQ_TIMEOUT)
#                
#                if "Nonce is too small." in response:
#                    response = None
#            except (ConnectionError, Timeout) as e:
#                raise ExchangeError('exmo', '%s %s while sending to exmo%r' % (type(e), str(e), params))
#        print response.text
#        return response.text

    def base_currency(self, pair):
        if pair[0] == 'B':
            return 'BTC'
        elif pair[0] == 'D':
            return 'DASH'
        elif pair[0] == 'E':
            return 'ETH'
        elif pair[0] == 'L':
            return 'LTC'

    def quote_currency(self, pair):
        # DASH
        if pair[0] == 'D':
            if pair[5] == 'B':
                # 'DASH_BTC'
                return 'BTC'
            if pair[5] == 'U':
                # 'DASH_USD'
                return 'USD'
        elif pair[4:] == 'BTC':
            return 'BTC'
        elif pair[4:] == 'USD':
            return 'USD'
        elif pair[4:] == 'EUR':
            return 'EUR'
        elif pair[4:] == 'RUB':
            return 'RUB'

        
    @classmethod
    def get_ticker(cls, pair=None):
        try:
            rawticker = requests.get(BASE_URL + '/ticker/', timeout=REQ_TIMEOUT).json()
        except (ConnectionError, Timeout, ValueError) as e:
            raise ExchangeError('exmo', '%s %s while sending get_ticker to exmo' % (type(e), str(e)))
        ticker = rawticker[pair]
        return create_ticker(bid=ticker['buy_price'], ask=ticker['sell_price'],
                             high=ticker['high'], low=ticker['low'],
                             volume=ticker['vol'], last=ticker['last_trade'],
                             timestamp=ticker['updated'], currency=exchange.quote_currency(pair),
                             vcurrency=exchange.base_currency(pair))

    @classmethod
    def get_order_book(cls, pair, **kwargs):
        """
        Returns:
        ask_quantity - the sum of all quantity values in sell orders
        ask_amount - the sum of all total sum values in sell orders
        ask_top - minimum sell price
        bid_quantity - the sum of all quantity values in buy orders
        bid_amount - the sum of all total sum values in buy orders
        bid_top - maximum buy price
        bid - the list of buy orders where every field is: price, quantity and amount
        amount = price * quantity
        ask - the list of sell orders where every field is: price, quantity and amount
        """
        try:
            rawbook = requests.get('%s/order_book/?pair=%s' % (BASE_URL, pair),
                                timeout=REQ_TIMEOUT).json()
        except ValueError as e:
            raise ExchangeError('exmo', '%s %s while sending to exmo get_order_book' % (type(e), str(e)))
        book = rawbook[pair]
        book['asks'] = book.pop('ask')
        book['bids'] = book.pop('bid')

        return book

    def get_balance(self, btype='total'):
        data =self.exmo_request('user_info')
        available = MultiMoney()
        reserved = MultiMoney()
        for cur, amount in data['balances'].iteritems():
            if cur == 'DOGE' or cur == 'ETH':
                pass
            else:
                available += Money(amount, currency=cur)

        for cur, amount in data['reserved'].iteritems():
            if cur == 'DOGE' or cur == 'ETH':
                pass
            else:
                reserved += Money(amount, currency=cur)

        if btype == 'total':
            return available + reserved
        elif btype == 'available':
            return available
        return available + reserved, available

    def get_open_orders(self, pair=None):
        pair = pair
        exch_pair = exchange.unformat_pair(pair)
        try:
            rawos = self.exmo_request('user_open_orders')

        except ValueError as e:
            raise ExchangeError('exmo', '%s %s while sending to exmo get_open_orders' % (type(e), str(e)))
        orders = []
        if pair in rawos:
            olist = rawos[pair]
            for o in olist:
                side = 'ask' if o['type'] == 'sell' else 'bid'
                orders.append(MyOrder(Money(o['price'], exchange.quote_currency(pair)),
                                      Money(o['amount'], exchange.base_currency(pair)),
                                      side, self.name, str(o['order_id'])))
        else:
            pass

        return orders

    def create_order(self, amount, price, otype, pair):
        if BLOCK_ORDERS:
            return "order blocked"
        if otype == 'bid':
            otype = 'buy'
        elif otype == 'ask':
            otype = 'sell'
        else:
            raise Exception('unknown side %r' % otype)

        params = {
            'pair' : pair,
            'price' : price,
            'quantity' : amount,
            'type' : otype
        }

        if otype == 'sell':
            try:
                order = self.exmo_request('order_create', params)
            except ValueError as e:
                raise ExchangeError('exmo', '%s %s while sending to exmo %r' % (type(e), str(e), params))
        else:
            try:
                order = self.exmo_request('order_create', params)
            except ValueError as e:
                raise ExchangeError('exmo', '%s %s while sending to exmo %r' % (type(e), str(e), params))
            
        if 'order_id' in order and order['order_id']:
            return str(order['order_id'])
        raise ExchangeError('exmo', 'unable to create order %r response was %r' % (params, order))

    def cancel_order(self, oid):
        params = {'order_id' : oid}
        try:
            resp = self.exmo_request('order_cancel', params)
        except ValueError as e:
            raise ExchangeError('exmo', '%s %s while sending to exmo %r' % (type(e), str(e), params))

        if resp and 'result' in resp and resp['result'] == True:
            return True
        elif 'error' in resp and resp['error'] == 'Order could not be cancelled.':
            return True
        else:
            return False

    #get all open orders, then cancel each
    def cancel_orders(self, pair, **kwargs):
        try:
            olist = self.get_open_orders(pair)
        except ExchangeError as ee:
            if ee.error == "no orders":
                return True
            else:
                raise ee
        success = True
        for o in olist:
            if not self.cancel_order(o.order_id):
                success = False
        return success

    def get_deposit_address(self):
        result = self.exmo_request('deposit_address')
        return str(result['BTC'])
    # TODO: returns addresses per coin

    def get_transactions(self, pair, limit=None):
        params = {'pair': pair}
        try:
            return sef.exmo_request('user_trades')
        except ValueError as e:
            raise ExchangeError('exmo', '%s %s while sending to exmo get_transactions' % (type(e), str(e)))


eclass = Exmo
exchange = Exmo(exchange_config['exmo']['api_creds']['key'],
                    exchange_config['exmo']['api_creds']['secret'])
