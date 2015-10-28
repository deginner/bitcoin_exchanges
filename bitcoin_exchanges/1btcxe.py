import hashlib
import hmac
import json
import time
from decimal import Decimal
import requests
import urllib
from requests.exceptions import Timeout, ConnectionError
from moneyed.classes import Money, MultiMoney
from bitcoin_exchanges.exchange_util import ExchangeError, ExchangeABC, create_ticker, exchange_config, BLOCK_ORDERS, MyOrder #nonceDB, \
    


url = 'https://1btcxe.com/api/'
REQ_TIMEOUT = 10  # seconds


class OneBTCXE(ExchangeABC):
    name = '1btcxe'
    fiatcurrency = 'USD'

    def __init__(self, key, secret):
        super(OneBTCXE, self).__init__()
        # self.uid = uid
        self.key = key
        self.secret = secret

    def send_request(self, path, params=None, retry=0):
        """
        Send request to 1BTCXE.

        Parameters:
            path - The portion of the to use.
            params - The parameters to send with the request.
            sign - Flag indicating whether or not request needs to be signed. Default is True.
        """
        if not params:
            params = {}

        urlpath = url + path
        headers = {"Content-type": "application/x-www-form-urlencoded"}
        params['api_key'] = self.key
        params['nonce'] = int(time.time() * 1000)
        # post_string = urllib.urlencode(params)

        # Hash the params string to produce the Sign header value
        message = bytes(str(params['nonce']) + self.key).encode('utf-8')
        print message
        secret = bytes(self.secret).encode('utf-8')

        params['signature'] = hmac.new(secret, message, digestmod=hashlib.sha256).hexdigest()
        # hash_parm.update(post_string)
        print params
        print urlpath

        try:
            response = requests.post(url=urlpath, data=params, headers=headers, timeout=REQ_TIMEOUT).text
            print response
            # if "invalid nonce parameter" in response and retry < 3:
            #     return self.send_request(path=path, params=params, retry=retry + 1)
        except (ConnectionError, Timeout) as e:
            raise ExchangeError('1btcxe', '%s %s while sending to 1btcxe %r' % (type(e), str(e), params))
        return response

    @classmethod
    def send_public_request(cls, path, params=None, retry=0):
        if not params:
            params = {}

        urlpath = url + path
        headers = {"Content-type": "application/x-www-form-urlencoded"}
        try:
            response = requests.get(url=urlpath, data=params, headers=headers, timeout=REQ_TIMEOUT).text
        except (ConnectionError, Timeout) as e:
            raise ExchangeError('1btcxe', '%s %s while sending to 1btcxe %r' % (type(e), str(e), params))
        return response

    def _handle_response(self, resp):
        try:
            response = json.loads(resp)
        except (TypeError, ValueError):
            raise ExchangeError(exchange='1btcxe',
                                message="response was not valid json: %s" % str(resp))
        if response and 'success' in response and response['success'] == 1:
            return response['return']
        elif response and 'error' in response:
            raise ExchangeError(exchange='1btcxe', message=response['error'])
        else:
            raise ExchangeError(exchange='1btcxe',
                                message="response not successful but also not erroneous... %s" % str(response))

    def cancel_order(self, order_id):
        """
        Cancellation of the order
            parameter    description     it takes up the values
            order_id     Order id        numerical
        """
        path = 'orders/cancel'
        params = 'order_id' # not sure about this, 1btcxe uses 'id' rather than 'order_id'
        resp = self._handle_response(self.send_request(path, params))
        if 'order_id' in resp:
            return True
        else:
            return False

    def cancel_orders(self, **kwargs):
        try:
            olist = self.order_list()
        except ExchangeError as ee:
            if ee.error == "no orders":
                return True
            else:
                raise ee
        success = True
        for order_id in olist:
            if not self.cancel_order(order_id=order_id):
                success = False
        return success

    def create_order(self, amount, price, otype='buy'):
        """
        It returns the transactions history.
            parameter     description                                   it takes up the values
            pair          pair                                          btc_usd (example)
            type          The transaction type                          buy or sell
            rate          The rate to buy/sell                          numerical
            amount        The amount which is necessary to buy/sell     numerical
        """
        if BLOCK_ORDERS:
            return "order blocked"
        if otype == 'bid':
            otype = 'buy'
        elif otype == 'ask':
            otype = 'sell'
        else:
            raise ExchangeError(exchange='1btcxe',
                                message="Unknown order type %r" % otype)
        path = 'orders/new'
        params = {'currency': 'usd', 'side': otype,
                  'rate': float(price), 
                  'amount': round(float(amount), 2)} 
        # params need to be revised
        # per 1btcxe spec: 'amount' is amount  of BTC to buy or sell.
        # limit_price, stop_price are specified in docs, 'rate' is not
        resp = self._handle_response(self.send_request(path, params))
        if 'order_id' in resp:
            return str(resp['order_id'])
        raise ExchangeError('1btcxe', 'unable to create %s %r at %r order' % (otype, amount, price))

    def get_balance(self, btype='total'):
        bals = self.send_request('balances-and-info')
        print bals
        return bals
        # available = self.get_total_balance()
        # if btype == 'available':
        #     return available
        # onorder = self.get_balance_in_open_orders()
        # total = available + onorder
        # if btype == 'total':
        #     return total
        # else:
        #     return total, available

    def get_total_balance(self):
        info = self.get_info()
        funds = info['funds']
        return (MultiMoney() + Money(amount=funds['btc']) +
                Money(amount=funds['usd'], currency='USD'))
        # double check this, 'funds' is not a response from 'balances-and-info' endpoint

    def get_balance_in_open_orders(self):
        bal = MultiMoney()
        try:
            olist = self.order_list()
        except ExchangeError as ee:
            if ee.error == "no orders":
                return bal
            else:
                raise ee
        for oNum in olist:
            if olist[oNum]['pair'] == 'btc_usd':
                if olist[oNum]['type'] == 'buy':
                    bal += (Money(amount=olist[oNum]['amount'], currency='USD') *
                            Money(amount=olist[oNum]['rate'], currency='USD'))
                elif olist[oNum]['type'] == 'sell':
                    bal += Money(amount=Decimal(olist[oNum]['amount']))
        return bal


    @classmethod
    def get_order_book(cls, pair='ignored'):
        response = cls.send_public_request('order-book')
        return json.loads(response)

    def get_info(self):
        """
        It returns the information about
        the user's current balance, API key privileges,
        the number of transactions, the
        number of open orders and the server time.
        """
        path = 'balances-and-info'
        return self._handle_response(self.send_request(path))

    def get_open_orders(self):
        path = 'open-orders'
        try:
            rawos = self._handle_response(self.send_request(path))
        except ExchangeError as e:
            if e.message == 'no orders':
                return []
        orders = []
        for order_id, o in rawos.iteritems():
            side = 'ask' if o['type'] == 'sell' else 'bid'
            orders.append(MyOrder(Money(o['rate'], self.fiatcurrency), Money(o['amount']), side, self.name,
                                str(order_id)))
        return orders

    @classmethod
    def get_ticker(cls, pair='ignored'):
        response = cls.send_public_request('stats')
        stats = json.loads(response)['stats']
        return create_ticker(bid=stats['bid'], ask=stats['ask'], high=stats['max'], low=stats['min'],
                             volume=stats['total_btc_traded'], last=stats['last_price'], timestamp=time.time(),
                             currency='USD')

    def get_trades(self, since=None):
        # It returns your open orders/the orders history.
        # What is difference between get_trades and trade_history ?
        params = {"method": "TradeHistory"}

        if since is not None:
            params['since'] = since
        return self._handle_response(self.send_request(params))
        # this will fail

    def get_transactions(self, **kwargs):
        """Return the transactions history.
        :param **kwargs:
        """
        params = {"method": "TransHistory", 'count': 999999999999999}
        return self._handle_response(self.send_request(params))
        # this will fail

    def order_list(self, currency=None):  
        """
        Get your current open orders, grouped by order side (bid or ask).
        """
        path = 'open-orders'
        if currency is not None:
            params['currency'] = currency

        return self._handle_response(self.send_request(path, params))

    def trade_history(self, params=None):
        """
        Get a list of your transactions, 
        ordered by date, in descending order.
        :param     description                           type
        :currency   filter by currency                    str
        :limit      the amount of transactions to return  int
        :side       filter by 'buy' or 'sell'             str
        """
        path = 'user-transactions'
        params = {'currency' : None, 'limit' : 999999999999999, 'side': None}
        return self._handle_response(self.send_request(path, params))

    def get_deposit_address(self):
        return exchange_config['1btcxe']['address']


eclass = OneBTCXE
#
exchange = OneBTCXE(exchange_config['1btcxe']['api_creds']['key'], 
                    exchange_config['1btcxe']['api_creds']['secret'])
print exchange.get_balance()
# book = eclass.get_order_book()
# print book['order-book']['ask']

# uid=71548567,
