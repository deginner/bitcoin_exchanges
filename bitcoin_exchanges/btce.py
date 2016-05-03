import hashlib
import hmac
import json
import time
from decimal import Decimal
import requests
import urllib
from requests.exceptions import Timeout, ConnectionError
from moneyed.classes import Money, MultiMoney
from bitcoin_exchanges.exchange_util import ExchangeError, ExchangeABC,\
     create_ticker, exchange_config, nonceDB, BLOCK_ORDERS, MyOrder


publicUrl = 'https://btc-e.com/api/2/'
tradeUrl = 'https://btc-e.com/tapi/'
REQ_TIMEOUT = 10  # seconds


class BTCE(ExchangeABC):
    name = 'btce'

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

    @classmethod
    def format_pair(cls, pair):
        """
        convert unformatted pair symbol, e.g. btc_usd, 
        to formatted (standard) pair symbol, e.g. BTC_USD.

        formatted : unformatted
        'DASH_BTC' : 'dsh_btc'
        """
        if 'DSH' in pair.upper() and 'DASH' not in pair.upper():
            pair = pair.upper().replace('DSH', 'DASH')
        return pair.upper()

    @classmethod
    def unformat_pair(cls, pair):
        """
        convert formatted (standard) pair symbol, e.g. DASH_USD., 
        to unformatted pair symbol, e.g. dsh_usd.
        """
        if 'dash' in pair.lower():
            pair = pair.lower().replace('dash', 'dsh')
        return pair.lower()

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
        except (ConnectionError, Timeout) as e:
            raise ExchangeError('btce', '%s %s while sending to btce %r' % (type(e), str(e), params))
        return response

    @classmethod
    def papi(cls, pair, method):
        """
        BTC-E public api interface
        """
        url = publicUrl + pair + '/' + method + '/'
        headers = {'Content-type': 'application/x-www-form-urlencoded'}
        try:
            response = requests.get(url, headers=headers, timeout=REQ_TIMEOUT)
        except (ConnectionError, Timeout) as e:
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

    def cancel_order(self, order_id, pair=None):
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

    def cancel_orders(self, pair=None, **kwargs):
        try:
            olist = self.order_list()
        except ExchangeError as ee:
            if ee.error == "no orders":
                return True
            else:
                raise ee
        success = True
        for order_id in olist:
            # TODO check that order matches pair
            if not self.cancel_order(order_id=order_id):
                success = False
        return success

    def create_order(self, amount, price, otype, pair):
        """
        It returns the transactions history.
            parameter     description                                   it takes up the values
            pair          pair                                          btc_usd (example)
            type          The transaction type                          buy or sell
            rate          The rate to buy/sell                          numerical
            amount        The amount which is necessary to buy/sell     numerical
        """
        exch_pair = exchange.unformat_pair(pair)
        if BLOCK_ORDERS:
            return "order blocked"
        if otype == 'bid':
            otype = 'buy'
        elif otype == 'ask':
            otype = 'sell'
        else:
            raise ExchangeError(exchange='btce',
                                message="Unknown order type %r" % otype)
        rate = round(float(price), 3) if pair not in ['DASH_BTC', 'ETH_BTC', 'LTC_BTC'] else round(float(price), 5)
        params = {"method": "Trade",
                  'pair': exch_pair,
                  'type': otype,
                  'rate': rate,
                  'amount': round(float(amount), 3)
        }
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
                Money(amount=funds['usd'], currency='USD') +
                Money(amount=funds['eth'], currency='ETH') +
                Money(amount=funds['ltc'], currency='LTC') +
                Money(amount=funds['dsh'], currency='DASH'))

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
            base = self.base_currency(olist[oNum]['pair'])
            quote = self.quote_currency(olist[oNum]['pair'])
            if olist[oNum]['type'] == 'buy':
                bal += (Money(amount=olist[oNum]['amount'], currency=quote) *
                        Money(amount=olist[oNum]['rate'], currency=quote))
            elif olist[oNum]['type'] == 'sell':
                bal += Money(amount=Decimal(olist[oNum]['amount']), currency=base)
        return bal

    @classmethod
    def get_order_book(cls, pair):
        exch_pair = exchange.unformat_pair(pair)
        response = cls.papi(exch_pair, 'depth')
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

    def get_open_orders(self, pair):
        exch_pair = exchange.unformat_pair(pair)
        params = {"method": "ActiveOrders"}
        try:
            rawos = self._handle_response(self.send_btce(params))
        except ExchangeError as e:
            if e.message == 'no orders':
                return []
        orders = []
        for order_id, o in rawos.iteritems():
            # filter order list for the given pair
            if o['pair'] == exch_pair:
                side = 'ask' if o['type'] == 'sell' else 'bid'
                orders.append(MyOrder(Money(o['rate'], exchange.quote_currency(pair)), Money(o['amount'], exchange.base_currency(pair)), side, self.name,
                                str(order_id)))
            else:
                pass

        return orders

    @classmethod
    def get_ticker(cls, pair):
        exch_pair = exchange.unformat_pair(pair)
        response = cls.papi(exch_pair, 'ticker')
        ticker = json.loads(response)['ticker']
        ask = ticker.pop('buy')
        bid = ticker.pop('sell')
        timestamp = int(ticker.pop('updated'))
        volume = ticker.pop('vol_cur')
        del ticker['vol'], ticker['avg'], ticker['server_time']
        return create_ticker(ask=ask, bid=bid, timestamp=timestamp,
                             volume=volume, 
                             currency=exchange.quote_currency(pair),
                             vcurrency=exchange.base_currency(pair),
                             **ticker)

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

    def get_deposit_address(self):
        return exchange_config['btce']['address']


eclass = BTCE
exchange = BTCE(key=exchange_config['btce']['api_creds']['key'], secret=exchange_config['btce']['api_creds']['secret'])
