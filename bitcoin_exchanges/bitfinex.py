import hmac
import json
import time
import requests
from requests.exceptions import Timeout, ConnectionError
from hashlib import sha384
from base64 import b64encode

from moneyed.classes import Money, MultiMoney

from exchange_util import ExchangeABC, create_ticker, ExchangeError, exchange_config, BLOCK_ORDERS, MyOrder


BASE_URL = 'https://api.bitfinex.com'
REQ_TIMEOUT = 10  # seconds


class Bitfinex(ExchangeABC):
    name = 'bitfinex'

    def __init__(self, key, secret):
        super(Bitfinex, self).__init__()
        self.key = key
        self.secret = secret

    def bitfinex_encode(self, msg):
        msg['nonce'] = str(int(time.time() * 1e6))
        msg = b64encode(json.dumps(msg))
        signature = hmac.new(self.secret, msg, sha384).hexdigest()
        return {
            'X-BFX-APIKEY': self.key,
            'X-BFX-PAYLOAD': msg,
            'X-BFX-SIGNATURE': signature
        }

    def bitfinex_request(self, endpoint, params=None):
        params = params or {}
        params['request'] = endpoint
        response = None
        while response is None:
            try:
                response = requests.post(url=BASE_URL + params['request'],
                                         headers=self.bitfinex_encode(params),
                                         timeout=REQ_TIMEOUT)
                if "Nonce is too small." in response:
                    response = None
            except (ConnectionError, Timeout) as e:
                raise ExchangeError('bitfinex', '%s %s while sending to bitfinex %r' % (type(e), str(e), params))
        return response

    @classmethod
    def format_pair(cls, pair):
        """
        formatted : unformatted
        'BTC_USD': 'btcusd'
        'LTC_USD': 'ltcusd'
        'LTC_BTC': 'ltcbtc'
        'ETH_USD': 'ethusd'
        'ETH_BTC': 'ethbtc'
        """
        if pair[0] == 'l':
            base = 'LTC'
            if pair[2:] == 'btc':
                quote = 'BTC'
            else:
                quote = 'USD'
        elif pair[0] == 'e':
            base = 'ETH'
            if pair[2:] == 'btc':
                quote = 'BTC'
            else:
                quote = 'USD'
        elif pair[0] == 'b':
            base = 'BTC'
            quote = 'USD'
        return base + '_' + quote

    @classmethod
    def unformat_pair(cls, pair):
        exch_pair = pair[:3].lower() + pair[4:].lower()
        return exch_pair

    def base_currency(self, pair):
        bcurr = pair[:3]
        return bcurr

    def quote_currency(self, pair):
        qcurr = pair[4:]
        return qcurr

    def cancel_order(self, order_id, pair=None):
        params = {'order_id': int(order_id)}
        try:
            resp = self.bitfinex_request('/v1/order/cancel', params).json()
        except ValueError as e:
            raise ExchangeError('bitfinex', '%s %s while sending to bitfinex %r' % (type(e), str(e), params))
        print resp
        if resp and 'id' in resp and resp['id'] == params['order_id']:
            return True
        elif 'message' in resp and resp['message'] == 'Order could not be cancelled.':
            return True
        else:
            return False

    def cancel_orders(self, pair=None, **kwargs):
        resp = self.bitfinex_request('/v1/order/cancel/all')
        # example respose:
        # {"result":"4 orders successfully cancelled"}
        if "orders successfully cancelled" in resp.text:
            return True
        else:
            return False

    def create_order(self, amount, price, otype, pair, typ='exchange limit', bfxexch='all'):
        if BLOCK_ORDERS:
            return "order blocked"
        if otype == 'bid':
            otype = 'buy'
        elif otype == 'ask':
            otype = 'sell'
        else:
            raise Exception('unknown side %r' % otype)
        exch_pair = exchange.unformat_pair(pair)
        params = {
            'side': otype,
            'symbol': exch_pair,
            'amount': "{:0.4f}".format(amount),
            'price': "{:0.4f}".format(price),
            'exchange': bfxexch,
            'type': typ
        }
        try:
            order = self.bitfinex_request('/v1/order/new', params).json()
        except ValueError as e:
            raise ExchangeError('bitfinex', '%s %s while sending to bitfinex %r' % (type(e), str(e), params))

        if 'is_live' in order and order['is_live']:
            return str(order['order_id'])
        raise ExchangeError('bitfinex', 'unable to create order %r response was %r' % (params, order))

    @classmethod
    def format_book_item(cls, item):
        return super(Bitfinex, cls).format_book_item((item['price'], item['amount']))

    @classmethod
    def unformat_book_item(cls, item):
        return {'price': str(item[0]), 'amount': str(item[1])}

    def get_balance(self, btype='total'):
        try:
            data = self.bitfinex_request('/v1/balances').json()
        except ValueError as e:
            raise ExchangeError('bitfinex', '%s %s while sending to bitfinex get_balance' % (type(e), str(e)))
        if 'message' in data:
            raise ExchangeError(exchange='bitfinex', message=data['message'])
        relevant = filter(lambda x: x['currency'] in ('usd', 'btc', 'ltc'), data)

        if btype == 'total':
            total = MultiMoney(*map(lambda x: Money(x['amount'], x['currency'].upper()), relevant))
            return total
        elif btype == 'available':
            available = MultiMoney(*map(lambda x: Money(x['available'], x['currency'].upper()), relevant))
            return available
        else:
            total = MultiMoney(*map(lambda x: Money(x['amount'], x['currency'].upper()), relevant))
            available = MultiMoney(*map(lambda x: Money(x['available'], x['currency'].upper()), relevant))
            return total, available

    def get_open_orders(self, pair):
        exch_pair = exchange.unformat_pair(pair)
        try:
            rawos = self.bitfinex_request('/v1/orders').json()
        except ValueError as e:
            raise ExchangeError('bitfinex', '%s %s while sending to bitfinex get_open_orders' % (type(e), str(e)))
        orders = []
        for o in rawos:
            if o['symbol'] == exch_pair:
                side = 'ask' if o['side'] == 'sell' else 'bid'
                orders.append(MyOrder(Money(o['price'], exchange.quote_currency(pair)), Money(o['remaining_amount'], exchange.base_currency(pair)), side,
                                  self.name, str(o['id'])))
            else:
                pass
        return orders

    @classmethod
    def get_order_book(cls, pair=None, **kwargs):
        exch_pair = exchange.unformat_pair(pair)
        try:
            return requests.get('%s/v1/book/%s' % (BASE_URL, exch_pair),
                                timeout=REQ_TIMEOUT).json()
        except ValueError as e:
            raise ExchangeError('bitfinex', '%s %s while sending to bitfinex get_order_book' % (type(e), str(e)))

    @classmethod
    def get_ticker(cls, pair=None):
        exch_pair = exchange.unformat_pair(pair)
        try:
            rawtick = requests.get(BASE_URL + '/v1/pubticker/%s' % exch_pair, timeout=REQ_TIMEOUT).json()
        except (ConnectionError, Timeout, ValueError) as e:
            raise ExchangeError('bitfinex', '%s %s while sending get_ticker to bitfinex' % (type(e), str(e)))

        return create_ticker(bid=rawtick['bid'], ask=rawtick['ask'], high=rawtick['high'], low=rawtick['low'],
                             volume=rawtick['volume'], last=rawtick['last_price'], timestamp=rawtick['timestamp'],
                             currency=exchange.quote_currency(pair), vcurrency=exchange.base_currency(pair))

    def get_transactions(self, pair, limit=None):
        exch_pair = exchange.unformat_pair(pair)
        params = {'symbol': exch_pair}
        try:
            return self.bitfinex_request('/v1/mytrades', params).json()
        except ValueError as e:
            raise ExchangeError('bitfinex', '%s %s while sending to bitfinex get_transactions' % (type(e), str(e)))

    def get_active_positions(self):
        try:
            return self.bitfinex_request('/v1/positions').json()
        except ValueError as e:
            raise ExchangeError('bitfinex', '%s %s while sending to bitfinex get_active_positions' % (type(e), str(e)))

    def get_order_status(self, order_id):
        params = {'order_id': int(order_id)}
        try:
            return self.bitfinex_request('/v1/order/status', params).json()
        except ValueError as e:
            raise ExchangeError('bitfinex', '%s %s while sending to bitfinex get_order_status for %s' % (
                type(e), str(e), str(order_id)))

    def get_deposit_address(self):
        """
        # TODO implement for multicurrency

        request parmas
        Key         Type      Description
        method	    [string]  Method of deposit (accepted:
                                  'bitcoin', 'litecoin', 'ethereum'.)
        wallet_name [string]  Your wallet needs to already exist.
                              Wallet to deposit in (accepted:
                                  'trading', 'exchange', 'deposit')
        renew	    [integer] (optional) Default is 0.
                              If set to 1, will return a new unused deposit address

        response
        result	    [string]   'success' or 'error
        method	    [string]
        currency    [string]
        address	    [string]	The deposit address (or error message if result = 'error')
        """
        try:
            result = self.bitfinex_request('/v1/deposit/new', {'currency': 'BTC', 'method': 'bitcoin',
                                                             'wallet_name': 'exchange'}).json()
            if result['result'] == 'success' and 'address' in result:
                return str(result['address'])
            else:
                raise ExchangeError('bitfinex', result)
        except ValueError as e:
            raise ExchangeError('bitfinex', '%s %s while sending get_deposit_address' % (type(e), str(e)))

    def account_info(self):
        try:
            data = self.bitfinex_request('/v1/account_infos').json()
        except ValueError as e:
            raise ExchangeError('bitfinex', '%s %s while sending to bitfinex get_open_orders' % (type(e), str(e)))
        return data

eclass = Bitfinex
exchange = Bitfinex(exchange_config['bitfinex']['api_creds']['key'],
                    exchange_config['bitfinex']['api_creds']['secret'])
