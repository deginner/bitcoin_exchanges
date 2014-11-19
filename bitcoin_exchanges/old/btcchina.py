#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
copied from BTC-China wiki
http://btcchina.org/api-trade-documentation-en#python

Hopefully improved a little bit by implementing ticker methods and using requests package. - Ira Miller, Coinapult
"""
import time
import re
import hmac
import hashlib
import base64
import json
from decimal import Decimal
import requests
from requests.exceptions import Timeout, ConnectionError
from bitcoin_exchanges.exchange_util import ExchangeError


REQ_TIMEOUT = 10  # seconds


class BTCChina():
    def __init__(self, access=None, secret=None, normalization_rate=Decimal(1 / 6.1 * 0.975)):
        self.access_key = access
        self.secret_key = secret
        self.url = "https://api.btcchina.com"
        self.normalization_rate = normalization_rate

    def _get_tonce(self):
        return int(time.time() * 1000000)

    def _get_params_hash(self, pdict):
        pstring = ""
        # The order of params is critical for calculating a correct hash
        fields = ['tonce', 'accesskey', 'requestmethod', 'id', 'method', 'params']
        for f in fields:
            if pdict[f]:
                if f == 'params':
                    # Convert list to string, then strip brackets and spaces
                    # probably a cleaner way to do this
                    param_string = re.sub("[\[\] ]", "", str(pdict[f]))
                    param_string = re.sub("'", '', param_string)
                    pstring += f + '=' + param_string + '&'
                else:
                    pstring += f + '=' + str(pdict[f]) + '&'
            else:
                pstring += f + '=&'
        pstring = pstring.strip('&')

        # now with correctly ordered param string, calculate hash
        phash = hmac.new(self.secret_key, pstring, hashlib.sha1).hexdigest()
        return phash

    def _private_request(self, post_data, retry=0):
        # fill in common post_data parameters
        tonce = self._get_tonce()
        post_data['tonce'] = tonce
        post_data['accesskey'] = self.access_key
        post_data['requestmethod'] = 'post'

        # If ID is not passed as a key of post_data, just use tonce
        if 'id' not in post_data:
            post_data['id'] = tonce

        pd_hash = self._get_params_hash(post_data)

        # must use b64 encode
        auth_string = 'Basic ' + base64.b64encode(self.access_key + ':' + pd_hash)
        headers = {'Authorization': auth_string, 'Json-Rpc-Tonce': tonce}

        # post_data dictionary passed as JSON
        # self.conn.request("POST",'/api_trade_v1.php',json.dumps(post_data),headers)
        # response = self.conn.getresponse()
        try:
            response = requests.post(self.url + '/api_trade_v1.php', data=json.dumps(post_data), headers=headers,
                                     verify=False, timeout=REQ_TIMEOUT)
        except (ConnectionError, Timeout) as e:
            raise ExchangeError('btcchina', 'Could not complete request %r for reason %s' % (post_data, e))

        # check response code, ID, and existence of 'result' or 'error'
        # before passing a dict of results
        # if response.status == 200:
        if response.status_code == 200:
            # this might fail if non-json data is returned
            # resp_dict = json.loads(response.read())
            resp_dict = json.loads(response.text)

            # The id's may need to be used by the calling application,
            # but for now, check and discard from the return dict
            if str(resp_dict['id']) == str(post_data['id']):
                if 'result' in resp_dict:
                    return resp_dict['result']
                elif 'error' in resp_dict:
                    return resp_dict['error']
        elif response.status_code == 401 and retry < 2:
            # possible nonce collision?
            self._private_request(post_data, retry=retry + 1)
        else:
            print "status:" + str(response.status_code)
            raise ExchangeError('btcchina', 'error response for %r: %s' % (post_data, str(response.status_code)))

        raise ExchangeError('btcchina', 'Invalid response for %r' % post_data)

    def get_account_info(self, post_data=None):
        if not post_data:
            post_data = {}
        post_data['method'] = 'getAccountInfo'
        post_data['params'] = []
        return self._private_request(post_data)

    def get_market_depth(self, post_data=None):
        try:
            depth = requests.get('https://data.btcchina.com/data/orderbook')
            return depth.json()
        except (ConnectionError, Timeout, ValueError) as e:
            raise ExchangeError('btcchina', 'Could not get_market_depth using data %s for reason %s' % (post_data, e))

    def buy(self, price, amount, post_data=None):
        if not post_data:
            post_data = {}
        post_data['method'] = 'buyOrder'
        post_data['params'] = [price, amount]
        return self._private_request(post_data)

    def sell(self, price, amount, post_data=None):
        if not post_data:
            post_data = {}
        post_data['method'] = 'sellOrder'
        post_data['params'] = [price, amount]
        return self._private_request(post_data)

    def cancel(self, order_id, post_data=None):
        if not post_data:
            post_data = {}
        post_data['method'] = 'cancelOrder'
        post_data['params'] = [order_id]
        return self._private_request(post_data)

    def request_withdrawal(self, currency, amount, post_data=None):
        if not post_data:
            post_data = {}
        post_data['method'] = 'requestWithdrawal'
        post_data['params'] = [currency, amount]
        return self._private_request(post_data)

    def get_deposits(self, currency='BTC', pending=True, post_data=None):
        if not post_data:
            post_data = {}
        post_data['method'] = 'getDeposits'
        if pending:
            post_data['params'] = [currency]
        else:
            post_data['params'] = [currency, 'false']
        return self._private_request(post_data)

    def get_orders(self, oid=None, open_only=True, post_data=None):
        # this combines getOrder and getOrders
        if not post_data:
            post_data = {}
        if oid is None:
            post_data['method'] = 'getOrders'
            if open_only:
                post_data['params'] = []
            else:
                post_data['params'] = ['false']
        else:
            post_data['method'] = 'getOrder'
            post_data['params'] = [oid]
        return self._private_request(post_data)

    def cancel_all_orders(self):
        orders = self.get_orders()
        for order in orders['order']:
            self.cancel(order_id=order['id'])

    def get_withdrawals(self, wid='BTC', pending=True, post_data=None):
        # this combines getWithdrawal and getWithdrawls
        if not post_data:
            post_data = {}
        try:
            wid = int(wid)
            post_data['method'] = 'getWithdrawal'
            post_data['params'] = [wid]
        except:
            post_data['method'] = 'getWithdrawals'
            if pending:
                post_data['params'] = [wid]
            else:
                post_data['params'] = [wid, 'false']
        return self._private_request(post_data)

    def get_ticker(self, retry=0):
        try:
            resp = requests.get('https://data.btcchina.com/data/ticker', verify=False,
                                timeout=REQ_TIMEOUT)
        except (ConnectionError, Timeout) as e:
            raise ExchangeError('btcchina', 'Could not get_ticker for reason %s' % e)
        try:
            return json.loads(resp.text)
        except ValueError:
            if retry < 5:
                self.get_ticker(retry=retry + 1)

    def get_usd_ticker(self):
        cnyticker = self.get_ticker()
        if 'ticker' in cnyticker:
            usdticker = {'ticker': {}}
            usdticker['ticker']['sell'] = Decimal(cnyticker['ticker']['sell']) * self.normalization_rate
            usdticker['ticker']['buy'] = Decimal(cnyticker['ticker']['buy']) * self.normalization_rate
            usdticker['ticker']['last'] = Decimal(cnyticker['ticker']['last']) * self.normalization_rate
            usdticker['ticker']['high'] = Decimal(cnyticker['ticker']['high']) * self.normalization_rate
            usdticker['ticker']['low'] = Decimal(cnyticker['ticker']['low']) * self.normalization_rate
            usdticker['ticker']['vol'] = cnyticker['ticker']['vol']
            return usdticker

    def get_transactions(self, limit=None, ttype='all', offset=0):
        limit = 10 if limit is None else 0
        post_data = {'method': 'getTransactions',
                     'params': [ttype, limit, offset]}
        return self._private_request(post_data)
