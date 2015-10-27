import hashlib
import hmac
import json
import time
import requests
from requests.exceptions import Timeout, ConnectionError
from moneyed.classes import Money, MultiMoney

from bitcoin_exchanges.exchange_util import ExchangeABC, ExchangeError, exchange_config, create_ticker, BLOCK_ORDERS, \
    MyOrder


baseUrl = "https://www.bitstamp.net/api/"
REQ_TIMEOUT = 10  # seconds


class Bitstamp(ExchangeABC):
    name = 'bitstamp'

    def __init__(self, key, secret, clientid):
        super(Bitstamp, self).__init__()
        self.key = key
        self.secret = secret
        self.clientid = clientid

    def submit_request(self, path, params=None, private=False, timedelta=86400, retry=0):
        """
        Send request to BitStamp.

        Parameters:
            path - The portion of the url path which follows the api version. Should begin with '/.'
            params - The parameters to send with the request.
            private - Boolean value weather or not the credentials need to be passed
        """
        if not params:
            params = {}
        url = baseUrl + path + '/'
        if timedelta != 86400:
            url += '?timedelta=' + str(timedelta)

        if private:
            params['key'] = self.key
            params['nonce'] = int(time.time() * 100000)
            mess = str(params['nonce']) + self.clientid + self.key
            params['signature'] = hmac.new(self.secret, msg=mess,
                                           digestmod=hashlib.sha256).hexdigest().upper()

        headers = {'Content-type': 'application/x-www-form-urlencoded',
                   'User-Agent': 'newcpt'}

        if private:
            request = requests.post(url, data=params, headers=headers, verify=False,
                                    timeout=REQ_TIMEOUT)
        else:
            request = requests.post(url, headers=headers, verify=False,
                                    timeout=REQ_TIMEOUT)
        response = None
        try:
            response = request.text
        except request.exceptions.HTTPError as e:
            print e
            if request.status:
                print request.status
            if response:
                print response
            return None
        if response == '{"error": "Invalid nonce"}' and retry < 10:
            tosleep = round(1 - float(10 - retry) / 10, 2)
            time.sleep(tosleep)
            self.submit_request(path, params=params, private=private,
                                timedelta=timedelta, retry=retry + 1)
        elif 'error' in response:
            raise ExchangeError('bitstamp', message=response)
        return response

    @classmethod
    def api_get(cls, path):
        url = baseUrl + path + '/'
        headers = {'Content-type': 'application/x-www-form-urlencoded',
                   'Accept': 'application/json',
                   'User-Agent': 'bitcoin_exchanges'}
        try:
            req = requests.get(url, headers=headers, timeout=REQ_TIMEOUT)
            response = req.text
        except requests.exceptions.HTTPError as e:
            print e
            return None
        return response

    def cancel_order(self, oid):
        """
        Returns 'true' if order has been found and canceled.
        """
        if json.loads(self.submit_request('cancel_order', {'id': str(oid)}, True)):
            return True
        return False

    def cancel_orders(self, typ='all'):
        """
        Returns 'true' if order has been found and canceled.
        """
        orders = self.get_open_orders()
        for order in orders:
            if (typ == 'all' or typ == order.side):
                print self.submit_request('cancel_order', {'id': str(order.order_id)}, True)
        return True

    def create_order(self, amount, price, otype):
        if BLOCK_ORDERS:
            return "order blocked"
        if otype == 'ask':
            otype = 'sell'
        elif otype == 'bid':
            otype = 'buy'
        if otype != 'buy' and otype != 'sell':
            raise ExchangeError(exchange='bitstamp',
                                message="Only 'buy' and 'sell' are acceptable order types.")
        data = {'amount': round(float(amount), 2),
                'price': round(price, 2)}
        response = json.loads(self.submit_request(otype, data, True))
        if 'id' in response:
            return str(response['id'])
        raise ExchangeError('bitstamp', 'unable to create order %r' % data)

    def get_balance(self, btype='total'):
        """
        :param str btype: The balance types to include
        """
        try:
            stampbal = json.loads(self.submit_request('balance', {}, True))
            if 'btc_balance' not in stampbal or 'usd_balance' not in stampbal:
                raise ExchangeError(exchange='bitstamp',
                                    message="Bitstamp balance information unavailable")
        except ValueError as e:
            raise ExchangeError('bitstamp', '%s %s while sending to bitstamp get_balance' % (type(e), str(e)))

        if btype == 'total':
            total = MultiMoney(Money(stampbal['btc_balance']), Money(stampbal['usd_balance'], currency='USD'))
            return total
        elif btype == 'available':
            available = MultiMoney(Money(stampbal['btc_available']), Money(stampbal['usd_available'], currency='USD'))
            return available
        else:
            total = MultiMoney(Money(stampbal['btc_balance']), Money(stampbal['usd_balance'], currency='USD'))
            # TODO this isn't correct
            available = MultiMoney(Money(stampbal['btc_available']), Money(stampbal['usd_available'], currency='USD'))
            return total, available

    def get_open_orders(self):
        rawos = self.submit_request('open_orders', {}, True)
        jos = json.loads(rawos)
        orders = []
        for o in jos:
            side = 'ask' if o['type'] == 1 else 'bid'
            orders.append(MyOrder(Money(o['price'], self.fiatcurrency), Money(o['amount']), side, self.name, str(o['id'])))
        return orders

    @classmethod
    def get_order_book(cls, pair='ignored'):
        opath = 'order_book'
        try:
            jresp = cls.api_get(opath)
            response = json.loads(jresp)
        except (TypeError, ValueError):
            return None
        if response and 'bids' in response:
            return response
        elif response and 'error' in response:
            raise ExchangeError(exchange='bitstamp', message=response['error'])
        return None

    @classmethod
    def get_ticker(cls, pair='ignored'):
        try:
            rawtick = json.loads(cls.api_get('ticker'))
        except (ConnectionError, Timeout, ValueError) as e:
            raise ExchangeError('bitstamp', '%s %s while sending get_ticker to bitstamp' % (type(e), str(e)))

        return create_ticker(bid=rawtick['bid'], ask=rawtick['ask'], high=rawtick['high'], low=rawtick['low'],
                             volume=rawtick['volume'], last=rawtick['last'], timestamp=rawtick['timestamp'],
                             currency='USD')

    def get_transactions(self, timedelta):
        """
        Returns descending JSON list of transactions.
        Every transaction (dictionary) contains:

            datetime - date and time
            id - transaction id
            type - transaction type (0 - deposit; 1 - withdrawal; 2 - market trade)
            usd - USD amount
            btc - BTC amount
            fee - transaction fee
        """
        return json.loads(self.submit_request('user_transactions', {}, True, timedelta))

    def get_deposit_address(self):
        return str(json.loads(self.submit_request('bitcoin_deposit_address', {}, True)))


eclass = Bitstamp
exchange = Bitstamp(exchange_config['bitstamp']['api_creds']['key'],
                    exchange_config['bitstamp']['api_creds']['secret'],
                    exchange_config['bitstamp']['api_creds']['clientid'])
