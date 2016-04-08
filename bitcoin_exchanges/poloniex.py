import time
import json
from moneyed.classes import Money, MultiMoney
from exchange_util import exchange_config, ExchangeABC, ExchangeError, create_ticker, BLOCK_ORDERS, MyOrder

from old import poloniex

polo = poloniex.poloniex(APIKey=exchange_config['poloniex']['api_creds']['key'],
                          Secret=exchange_config['poloniex']['api_creds']['secret'])

REQ_TIMEOUT = poloniex.REQ_TIMEOUT

currencyPair='USDT_BTC'

class Poloniex(ExchangeABC):
    name = 'poloniex'
    fiatcurrency = 'USD'

    def __init__(self):
        super(Poloniex, self).__init__()

    @classmethod
    def get_ticker(cls, **kwargs):
        rawticker = polo.returnTicker()
        usdtick = rawticker['USDT_BTC']
        return create_ticker(bid=usdtick['highestBid'], ask=usdtick['lowestAsk'],
                             high=usdtick['high24hr'], low=usdtick['low24hr'],
                             last=usdtick['last'], volume=usdtick['baseVolume'],
                             timestamp=time.time(), currency='USD')

    @classmethod
    def get_order_book(cls, pair=None):
        pair = currencyPair
        return polo.returnOrderBook(currencyPair=pair)
    
    def get_balance(self, btype='total'):
        data = polo.returnCompleteBalances()

        # filter balances for btc and dash, report totals for both together
        btc_bal = data['BTC']
        usdt_bal = data['USDT']
        available = MultiMoney(Money(btc_bal['available'], currency='BTC'), Money(usdt_bal['available'], currency='USD'))
        onOrders = MultiMoney(Money(btc_bal['onOrders'], currency='BTC'), Money(usdt_bal['onOrders'], currency='USD'))
        if btype == 'total':
            return available + onOrders
        elif btype == 'available':
            return available
        return available + onOrders, available
            
    def get_open_orders(self):        
        try:
            rawos = polo.returnOpenOrders(currencyPair)
        except ValueError as e:
            raise ExchangeError('poloniex', '%s %s while sending to poloniex get_open_orders' % (type(e), str(e)))
        orders = []
        for o in rawos:
            side = 'ask' if o['type'] == 'sell' else 'bid'
            orders.append(MyOrder(Money(o['rate'], self.fiatcurrency), Money(o['amount']), side,
                                  self.name, str(o['orderNumber'])))
        return orders
    
    def create_order(self, amount, price, otype):
        rate=price
        if BLOCK_ORDERS:
            return "order blocked"
        if otype == 'bid':
            otype = 'buy'
        elif otype == 'ask':
            otype = 'sell'
        else:
            raise Exception('unknown side %r' % otype)

        params = {
            'rate' : price,
            'amount' : amount,
            'currencyPair' : currencyPair
        }
        
        if otype == 'sell':
            try:
                order = polo.sell(amount=amount, rate=rate, currencyPair=currencyPair)
            except ValueError as e:
                raise ExchangeError('poloniex', '%s %s while sending to poloniex %r' % (type(e), str(e), params))
        else:
            try:
                order = polo.buy(amount=amount, rate=rate, currencyPair=currencyPair)
            except ValueError as e:
                raise ExchangeError('poloniex', '%s %s while sending to poloniex %r' % (type(e), str(e), params))
            
        if 'orderNumber' in order and order['orderNumber']:
            return str(order['orderNumber'])
        raise ExchangeError('poloniex', 'unable to create order %r response was %r' % (params, order))

    def cancel_order(self, oid):
        params = {'currencyPair': currencyPair, 'orderNumber': oid}

        try:
            resp = polo.cancel(currencyPair, orderNumber=oid)
        except ValueError as e:
            raise ExchangeError('poloniex', '%s %s while sending to poloniex %r' % (type(e), str(e), params))
        if resp and 'success' in resp and resp['success'] == 1:
            return True
        elif 'error' in resp and resp['error'] == 'Order could not be cancelled.':
            return True
        else:
            return False
        
        #get all open orders, then cancel each
    def cancel_orders(self, **kwargs):
        try:
            olist = self.get_open_orders()
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
        result = polo.returnDepositAddresses()
        return str(result['BTC'])
    # TODO: returns addresses per coin

    def get_transactions(self, limit=None):
        params = {'currencyPair': currencyPair}
        try:
            return polo.returnTradeHistory(params)
        except ValueError as e:
            raise ExchangeError('poloniex', '%s %s while sending to poloniex get_transactions' % (type(e), str(e)))



eclass = Poloniex
exchange = Poloniex()

