import time
import json
from moneyed.classes import Money, MultiMoney
from exchange_util import exchange_config, ExchangeABC, ExchangeError, create_ticker, BLOCK_ORDERS, MyOrder, get_live_exchange_pairs

from old import poloniex

polo = poloniex.poloniex(APIKey=exchange_config['poloniex']['api_creds']['key'],
                          Secret=exchange_config['poloniex']['api_creds']['secret'])

REQ_TIMEOUT = poloniex.REQ_TIMEOUT

class Poloniex(ExchangeABC):
    name = 'poloniex'

    def __init__(self):
        super(Poloniex, self).__init__()

    @classmethod
    def format_pair(cls, pair):
        """
        poloniex confuses base and quote currency, and uses non-standard USD.

        formatted : unformatted
        'BTC_USDT': 'USDT_BTC',
        'DASH_BTC': 'BTC_DASH',
        'DASH_USDT': 'USDT_DASH'
        """
        if 'USDT' in pair.upper():
            pair = pair.upper().replace('USDT', 'USD')
        return cls.reverse_pair(pair)

    @classmethod
    def unformat_pair(cls, pair):
        if 'USD' in pair.upper() and 'USDT' not in pair.upper():
            pair = pair.upper().replace('USD', 'USDT')
        return cls.reverse_pair(pair)

    @classmethod
    def reverse_pair(cls, pair):
        pa = pair.split("_")
        return ("%s_%s" % (pa[1], pa[0])).upper()

    @classmethod
    def get_ticker(cls, pair=None):
        rawticker = polo.returnTicker()
        exch_pair = exchange.unformat_pair(pair)
        ticker = rawticker[exch_pair]
        return create_ticker(bid=ticker['highestBid'], ask=ticker['lowestAsk'],
                             high=ticker['high24hr'], low=ticker['low24hr'],
                             last=ticker['last'], volume=ticker['quoteVolume'],
                             # polo flips the pair
                             timestamp=time.time(), currency=exchange.base_currency(pair),
                             vcurrency=exchange.quote_currency(pair))

    @classmethod
    def get_order_book(cls, pair=None):
        exch_pair = exchange.unformat_pair(pair)
        response = polo.returnOrderBook(currencyPair=exch_pair)
        return response

    def get_balance(self, btype='total'):
        data = polo.returnCompleteBalances()
        # filter balances for btc and dash, report totals for both together
        btc_bal = data['BTC']
        usdt_bal = data['USDT']
        dash_bal = data['DASH']
        available = MultiMoney(Money(btc_bal['available'], currency='BTC'),
                               Money(usdt_bal['available'], currency='USDT'),
                               Money(dash_bal['available'], currency='DASH'))
        onOrders = MultiMoney(Money(btc_bal['onOrders'], currency='BTC'),
                              Money(usdt_bal['onOrders'], currency='USDT'),
                              Money(dash_bal['onOrders'], currency='DASH'))
        if btype == 'total':
            return available + onOrders
        elif btype == 'available':
            return available
        return available + onOrders, available
            
    def get_open_orders(self, pair=None):
        exch_pair = exchange.unformat_pair(pair)
        try:
            rawos = polo.returnOpenOrders(currencyPair=exch_pair)
        except ValueError as e:
            raise ExchangeError('poloniex',
                '%s %s while sending to poloniex get_open_orders' % (type(e), str(e)))
        orders = []
        if isinstance(rawos, str):
            raise ExchangeError('poloniex',
                'unknown error %s while sending to poloniex get_open_orders' % rawos)
        for o in rawos:
            side = 'ask' if o['type'] == 'sell' else 'bid'
            orders.append(MyOrder(Money(o['rate'], exchange.base_currency(pair)), # flipped
                                  Money(o['amount'], exchange.quote_currency(pair)), # flipped
                                  side, self.name, str(o['orderNumber'])))
        return orders
    
    def create_order(self, amount, price, otype, pair):
        rate=price
        exch_pair = exchange.unformat_pair(pair)
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
            'currencyPair' : exch_pair
        }
        
        if otype == 'sell':
            try:
                order = polo.sell(amount=amount, rate=rate, currencyPair=exch_pair)
            except ValueError as e:
                raise ExchangeError('poloniex',
                   '%s %s while sending to poloniex %r' % (type(e), str(e), params))
        else:
            try:
                order = polo.buy(amount=amount, rate=rate, currencyPair=exch_pair)
            except ValueError as e:
                raise ExchangeError('poloniex',
                    '%s %s while sending to poloniex %r' % (type(e), str(e), params))
            
        if 'orderNumber' in order and order['orderNumber']:
            return str(order['orderNumber'])
        raise ExchangeError('poloniex',
            'unable to create order %r response was %r' % (params, order))

    def cancel_order(self, oid, pair):
        exch_pair = exchange.unformat_pair(pair)
        params = {'currencyPair': exch_pair, 'orderNumber': oid}

        try:
            resp = polo.cancel(currencyPair=exch_pair, orderNumber=oid)
        except ValueError as e:
            raise ExchangeError('poloniex',
                '%s %s while sending to poloniex %r' % (type(e), str(e), params))
        if resp and 'success' in resp and resp['success'] == 1:
            return True
        elif 'error' in resp and resp['error'] == 'Order could not be cancelled.':
            return True
        else:
            return False
        
    #get all open orders, then cancel each
    def cancel_orders(self, pair):
        try:
            olist = self.get_open_orders(pair)
        except ExchangeError as ee:
            if ee.error == "no orders":
                return True
            else:
                raise ee
        success = True
        for o in olist:
            if not self.cancel_order(o.order_id, pair):
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

