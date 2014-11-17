from moneyed.classes import Money, MultiMoney
from exchange_util import exchange_config, ExchangeABC, ExchangeError, create_ticker

from old import btcchina

fee = 0
btcny = btcchina.BTCChina(access=exchange_config['btcchina']['api_creds']['key'],
                          secret=exchange_config['btcchina']['api_creds']['secret'])


class BTCChina(ExchangeABC):
    name = 'btcchina'
    fiatcurrency = 'CNY'

    def __init__(self):
        super(BTCChina, self).__init__()

    def account_info(self):
        return btcny.get_account_info()

    def cancel_order(self, oid):
        return btcny.cancel(oid)

    def cancel_orders(self, **kwargs):
        btcny.cancel_all_orders()
        return True

    def create_order(self, amount, price=0, otype='bid'):
        if isinstance(amount, Money):
            famount = round(float(amount.amount), 2)
        else:
            famount = float(amount)
        if int(famount) == famount:
            famount = float(famount) - 0.0001

        if isinstance(price, Money):
            fprice = round(float(price.amount), 2)
        else:
            fprice = float(price)
        if int(fprice) == fprice:
            fprice = float(fprice) - 0.01
        if otype in ('ask', 'sell'):
            order = btcny.sell(fprice, famount)
        else:
            order = btcny.buy(fprice, famount)
        if order and isinstance(order, bool):
            return "stupid btcchina does not return ids"
        else:
            raise ExchangeError('btcchina', 'unable to create %s %r at %r order for reason %s' % (otype, amount,
                                                                                                  price, order))

    def get_balance(self, btype='total'):
        ainfo = self.account_info()
        total = MultiMoney()
        available = MultiMoney()
        if ainfo is None:
            if btype == 'all':
                return total, available
            else:
                return total
        # XXX
        if ('btc' not in ainfo['balance'] or 'amount' not in ainfo['balance']['btc'] or
                ainfo['balance']['btc']['amount'] is None):
            ainfo['balance']['btc']['amount'] = 0
        if ainfo['balance']['cny']['amount'] is None:
            ainfo['balance']['cny']['amount'] = 0
        if ainfo['frozen']['btc']['amount'] is None:
            ainfo['frozen']['btc']['amount'] = 0
        if ainfo['frozen']['cny']['amount'] is None:
            ainfo['frozen']['cny']['amount'] = 0
        available += Money(amount=ainfo['balance']['btc']['amount'])
        total += Money(amount=ainfo['balance']['btc']['amount'])
        total += Money(amount=ainfo['frozen']['btc']['amount'])
        available += Money(amount=ainfo['balance']['cny']['amount'], currency='CNY')
        total += Money(amount=ainfo['balance']['cny']['amount'], currency='CNY')
        total += Money(amount=ainfo['frozen']['cny']['amount'], currency='CNY')

        if btype == 'total':
            return total
        elif btype == 'available':
            return available
        else:
            return total, available

    def get_depth(self):
        return btcny.get_market_depth()

    def get_open_orders(self):
        return btcny.get_orders()

    get_order_book = get_depth

    def get_ticker(self, **kwargs):
        rawticker = btcny.getTicker()
        if 'ticker' in rawticker:
            ticker = rawticker['ticker']
            return create_ticker(bid=ticker['buy'], ask=ticker['sell'], high=ticker['high'], low=ticker['low'],
                                 volume=ticker['vol'], last=ticker['last'], timestamp=ticker['date'],
                                 currency='CNY')
        raise ExchangeError('btcchina', 'unable to get ticker')

    def get_transactions(self, limit=None):
        return btcny.get_transactions(limit=limit)

    def get_usd_ticker(self):
        return btcny.getUSDTicker()


exchange = BTCChina()
