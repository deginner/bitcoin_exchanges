import hashlib
import hmac
import json
import time
from decimal import Decimal
import requests
import urllib

from moneyed.classes import Money, MultiMoney

from bitcoin_exchanges.exchange_util import ExchangeError, ExchangeABC, create_ticker, exchange_config, nonceDB


REQ_TIMEOUT = 10  # seconds

publicUrl = 'https://btc-e.com/api/2/btc_usd/'
tradeUrl = 'https://btc-e.com/tapi/'


class BTCE(ExchangeABC):
    name = 'btce'
    fiatcurrency = 'USD'

    def __init__(self, key, secret):
        super(BTCE, self).__init__()
        # btc-e nonce is capped at 4294967294
        # This only leaves room for seconds, on the traditional epoch timescale.
        # To get around this, we use tenths of a second, but drop the first digit.
        # This would break on Mon, 20 Apr 2015 02:25:29 GMT, without further adjustment,
        # so we subtract 3000000000. This gives us until Mon, 21 Oct 2024 07:45:29 GMT
        self.nonceDB = nonceDB
        self.create_nonce(int(time.time() * 10) - 13000000000)
        # XXX Or we can start at nonce 1 and increment from there?
        # If we do that this year (2014) then we should be fine until
        # 2150, unless btc-e changes its API before that :)
        self.key = key
        self.secret = secret

    def send_btce(self, params=None, sign=True, retry=0):
        """
        Send request to BTCE.

        Parameters:
            path - The portion of the to use.
            params - The parameters to send with the request.
            sign - Flag indicating whether or not request needs to be signed. Default is True.
        """
        if not params:
            params = {}
        url = tradeUrl

        params['nonce'] = self.next_nonce()
        post_string = urllib.urlencode(params)

        # Hash the params string to produce the Sign header value
        hash_parm = hmac.new(self.secret, digestmod=hashlib.sha512)
        hash_parm.update(post_string)
        headers = {"Content-type": "application/x-www-form-urlencoded",
                   "Key": self.key,
                   "Sign": hash_parm.hexdigest()}

        try:
            response = requests.post(url=url, data=params, headers=headers, timeout=REQ_TIMEOUT).text
            if "invalid nonce parameter" in response and retry < 3:
                return self.send_btce(params=params, sign=sign, retry=retry + 1)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            raise ExchangeError('btce', '%s %s while sending to btce %r' % (type(e), str(e), params))
        return response

    def papi(self, method):
        """
        BTC-E public api interface
        """
        url = publicUrl + method + '/'
        headers = {'Content-type': 'application/x-www-form-urlencoded'}
        try:
            response = requests.get(url, headers=headers, timeout=REQ_TIMEOUT)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            raise ExchangeError('btce', '%s %s while sending %r to %s' % (type(e), e, method, url))
        return response.text

    def _handle_response(self, resp):
        try:
            response = json.loads(resp)
        except (TypeError, ValueError):
            raise ExchangeError(exchange='btce',
                                message="response was not valid json: %s" % str(resp))
        if response and 'success' in response and response['success'] == 1:
            return response['return']
        elif response and 'error' in response:
            raise ExchangeError(exchange='btce', message=response['error'])
        else:
            raise ExchangeError(exchange='btce',
                                message="response not successful but also not erroneous... %s" % str(response))

    def cancel_order(self, order_id):
        """
        Cancellation of the order
            parameter    description     it takes up the values
            order_id     Order id        numerical
        """
        params = {"method": "CancelOrder", 'order_id': order_id}
        resp = self._handle_response(self.send_btce(params))
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
        if otype == 'bid':
            otype = 'buy'
        elif otype == 'ask':
            otype = 'sell'
        else:
            raise ExchangeError(exchange='btce',
                                message="Unknown order type %r" % otype)
        params = {"method": "Trade", 'pair': 'btc_usd', 'type': otype,
                  'rate': float(price),
                  'amount': round(float(amount), 2)}
        resp = self._handle_response(self.send_btce(params))
        if 'order_id' in resp:
            return str(resp['order_id'])
        raise ExchangeError('btce', 'unable to create %s %r at %r order' % (otype, amount, price))

    def get_balance(self, btype='total'):
        available = self.get_total_balance()
        if btype == 'available':
            return available
        onorder = self.get_balance_in_open_orders()
        total = available + onorder
        if btype == 'total':
            return total
        else:
            return total, available

    def get_total_balance(self):
        info = self.get_info()
        funds = info['funds']
        return (MultiMoney() + Money(amount=funds['btc']) +
                Money(amount=funds['usd'], currency='USD'))

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

    def get_depth(self):
        response = self.papi('depth')
        return json.loads(response)

    def get_info(self):
        """
        It returns the information about
        the user's current balance, API key privileges,
        the number of transactions, the
        number of open orders and the server time.
        """
        params = {"method": "getInfo"}
        return self._handle_response(self.send_btce(params))

    def get_open_orders(self):
        params = {"method": "ActiveOrders"}
        try:
            return self._handle_response(self.send_btce(params))
        except ExchangeError as e:
            if e.message == 'no orders':
                return {}

    get_order_book = get_depth

    def get_ticker(self, pair='ignored'):
        response = self.papi('ticker')
        ticker = json.loads(response)['ticker']
        ask = ticker.pop('buy')
        bid = ticker.pop('sell')
        timestamp = int(ticker.pop('updated'))
        volume = ticker.pop('vol_cur')
        del ticker['vol'], ticker['avg'], ticker['server_time']
        return create_ticker(ask=ask, bid=bid, timestamp=timestamp, volume=volume, **ticker)

    def get_trades(self, since=None):
        # It returns your open orders/the orders history.
        params = {"method": "TradeHistory"}
        if since is not None:
            params['since'] = since
        return self._handle_response(self.send_btce(params))

    def get_transactions(self, **kwargs):
        """Return the transactions history.
        :param **kwargs:
        """
        params = {"method": "TransHistory", 'count': 999999999999999}
        return self._handle_response(self.send_btce(params))

    def order_list(self):  # XXX btc-e mentions this has been deprecated.
        """
        It returns your open orders/the orders history.
        """
        params = {"method": "OrderList", 'count': 999999999999999}
        return self._handle_response(self.send_btce(params))

    def trade_history(self):
        """
        It returns the transactions history.
        """
        params = {"method": "TradeHistory", 'count': 999999999999999}
        return self._handle_response(self.send_btce(params))


exchange = BTCE(key=exchange_config['btce']['api_creds']['key'], secret=exchange_config['btce']['api_creds']['secret'])
