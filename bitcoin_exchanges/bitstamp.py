import hashlib
import hmac
import json
import time
import requests
from moneyed.classes import Money, MultiMoney
from bitcoin_exchanges.exchange_util import ExchangeABC, ExchangeError, exchange_config, create_ticker


baseUrl = "https://www.bitstamp.net/api/"
REQ_TIMEOUT = 10  # seconds


def api_get(path):
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


class Bitstamp(ExchangeABC):
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
            print order
            if (typ == 'all' or
                    (typ == 'ask' and order['type'] == 1) or
                    (typ == 'bid' and order['type'] == 0)):
                print self.submit_request('cancel_order', {'id': str(order['id'])}, True)
        return True

    def create_order(self, amount, price, otype):
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
        print response
        return response

    def get_balance(self, btype='total'):
        """
        :param str btype: The balance types to include
        """
        try:
            stampBal = json.loads(self.submit_request('balance', {}, True))
            if 'btc_balance' not in stampBal or 'usd_balance' not in stampBal:
                raise ExchangeError(exchange='bitstamp',
                                    message="Bitstamp balance information unavailable")
        except ValueError as e:
            raise ExchangeError('bitfinex', '%s %s while sending to bitfinex get_open_orders' % (type(e), str(e)))

        if btype == 'total':
            total = MultiMoney(Money(stampBal['btc_balance']), Money(stampBal['usd_balance'], currency='USD'))
            return total
        elif btype == 'available':
            # TODO this isn't correct
            available = MultiMoney(Money(stampBal['btc_balance']), Money(stampBal['usd_balance'], currency='USD'))
            return available
        else:
            total = MultiMoney(Money(stampBal['btc_balance']), Money(stampBal['usd_balance'], currency='USD'))
            # TODO this isn't correct
            available = MultiMoney(Money(stampBal['btc_balance']), Money(stampBal['usd_balance'], currency='USD'))
            return total, available

    def get_open_orders(self):
        """
        Returns JSON list of open orders. Each order is represented as dictionary:
            id - order id
            datetime - date and time
            type - buy or sell (0 - buy; 1 - sell)
            price - price
            amount - amount
        """
        rawos = self.submit_request('open_orders', {}, True)
        return json.loads(rawos)

    def get_order_book(self, pair='ignored'):
        opath = 'order_book'
        try:
            jresp = api_get(opath)
            response = json.loads(jresp)
        except (TypeError, ValueError):
            return None
        if response and 'bids' in response:
            return response
        elif response and 'error' in response:
            raise ExchangeError(exchange='bitstamp', message=response['error'])
        return None

    def get_ticker(self, pair='ignored'):
        try:
            rawtick = json.loads(api_get('ticker'))
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, ValueError) as e:
            raise ExchangeError('bitfinex', '%s %s while sending get_ticker to bitfinex' % (type(e), str(e)))

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


exchange = Bitstamp(exchange_config['bitstamp']['api_creds']['key'],
                    exchange_config['bitstamp']['api_creds']['secret'],
                    exchange_config['bitstamp']['api_creds']['clientid'])
