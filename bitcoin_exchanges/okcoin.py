import hashlib
import requests
from requests.exceptions import Timeout, ConnectionError

from moneyed.classes import Money, MultiMoney

from exchange_util import ExchangeABC, create_ticker, ExchangeError, exchange_config, BLOCK_ORDERS


BASE_URL = 'https://www.okcoin.com/api/v1/'
REQ_TIMEOUT = 10  # seconds


class OKCoin(ExchangeABC):
    name = 'okcoin'
    fiatcurrency = 'USD'

    def __init__(self, partner, secret):
        super(OKCoin, self).__init__()
        self.partner = partner
        self.secret = secret

    def okcoin_encode(self, params):
        postData = ''
        if not 'partner' in params:
            params['partner'] = self.partner
        for k in sorted(params.keys()):
            postData += '%s=%s&' % (k, params[k])
        postData += 'secret_key='+self.secret
        return hashlib.md5(postData).hexdigest().upper()

    def okcoin_request(self, endpoint, params=None):
        params = params or {}
        sig = self.okcoin_encode(params)
        params['partner'] = self.partner
        params['sign'] = sig
        headers = {'contentType': 'application/x-www-form-urlencoded'}
        try:
            response = requests.post(url=BASE_URL + endpoint,
                                     data=params,
                                     headers=headers,
                                     timeout=REQ_TIMEOUT).json()
        except (ConnectionError, Timeout, ValueError) as e:
            raise ExchangeError('okcoin', '%s %s while sending %r' % (type(e), str(e), params))
        if 'error_code' in response:
            raise ExchangeError('okcoin', '%s while sending %r' % (str(response['error_code']), params))
        return response

    def cancel_order(self, order_id, symbol='btc_usd'):
        params = {'order_id': order_id, 'symbol': symbol}
        resp = self.okcoin_request('cancel_order.do', params)
        if resp and 'order_id' in resp and resp['order_id'] == params['order_id']:
            return True
        return False

    def cancel_orders(self, symbol='btc_usd', **kwargs):
        oorders = self.get_open_orders(symbol)
        canceled = True
        for o in oorders:
            result = self.cancel_order(o['order_id'], symbol)
            if not result:
                canceled = False
        return canceled

    def create_order(self, amount, price, otype, symbol='btc_usd'):
        if BLOCK_ORDERS:
            return "order blocked"
        if otype == 'bid':
            otype = 'buy'
        elif otype == 'ask':
            otype = 'sell'
        else:
            raise Exception('unknown side %r' % otype)

        params = {
            'symbol': symbol,
            'type': otype,
            'price': price,
            'amount': amount,
        }
        data = self.okcoin_request('trade.do', params)

        if 'result' in data and data['result']:
            return str(data['order_id'])
        raise ExchangeError('okcoin', 'unable to create order %r response was %r' % (params, data))

    def get_balance(self, btype='total'):
        data = self.okcoin_request('userinfo.do')

        free = MultiMoney()
        freeze = MultiMoney()
        for cur, amount in data['info']['funds']['free'].iteritems():
            free += Money(amount, currency=cur)
            freeze += Money(data['info']['funds']['freezed'][cur], currency=cur)
        if btype == 'total':
            return free + freeze
        elif btype == 'available':
            return free
        return freeze + free, free

    def get_open_orders(self, symbol='btc_usd'):
        params = {'order_id': -1, 'symbol': symbol}
        resp = self.okcoin_request('order_info.do', params)
        if resp and 'result' in resp and resp['result']:
            return resp['orders']
        raise ExchangeError('okcoin', 'unable to get open orders. response was %r' % resp)

    @classmethod
    def get_order_book(cls, pair='btc_usd', **kwargs):
        try:
            return requests.get('%sdepth.do?symbol=%s' % (BASE_URL, pair), timeout=REQ_TIMEOUT).json()
        except (ConnectionError, Timeout, ValueError) as e:
            raise ExchangeError('okcoin', '%s %s while sending get_order_book' % (type(e), str(e)))

    @classmethod
    def get_ticker(cls, pair='btc_usd'):
        try:
            rawtick = requests.get(BASE_URL + 'ticker.do?symbol=%s' % pair, timeout=REQ_TIMEOUT).json()
        except (ConnectionError, Timeout, ValueError) as e:
            raise ExchangeError('okcoin', '%s %s while sending get_ticker to okcoin' % (type(e), str(e)))

        return create_ticker(bid=rawtick['ticker']['buy'], ask=rawtick['ticker']['sell'],
                             high=rawtick['ticker']['high'], low=rawtick['ticker']['low'],
                             volume=rawtick['ticker']['vol'], last=rawtick['ticker']['last'],
                             timestamp=rawtick['date'], currency='USD')

    def get_transactions(self, limit=None, status=1, current_page=1, page_length=200, symbol='btc_usd'):
        params = {'status': status, 'current_page': current_page, 'page_length': page_length, 'symbol': symbol}
        resp = self.okcoin_request('order_history.do', params)
        if resp and 'result' in resp and resp['result']:
            return resp
        raise ExchangeError('okcoin', 'unable to get transactions. response was %r' % resp)

    def get_deposit_address(self):
        return exchange_config['okcoin']['address']


eclass = OKCoin
exchange = OKCoin(exchange_config['okcoin']['api_creds']['partner'],
                    exchange_config['okcoin']['api_creds']['secret'])
