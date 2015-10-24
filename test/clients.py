from decimal import Decimal
import unittest

from moneyed import Money, MultiMoney

from bitcoin_exchanges.exchange_util import get_live_exchange_workers, Ticker, ExchangeError, OrderbookItem, \
    exchange_config, MyOrder

EXCHANGE = get_live_exchange_workers()


class TestAPI(unittest.TestCase):
    def test_ticker(self):
        for name, mod in EXCHANGE.iteritems():
            print "test_ticker %s" % name
            result = mod.eclass.get_ticker()
            self.assertIsInstance(result, Ticker)

            self.assertIsInstance(result.bid, Money)
            self.assertIsInstance(result.ask, Money)
            self.assertIsInstance(result.high, Money)
            self.assertIsInstance(result.low, Money)
            self.assertIsInstance(result.last, Money)
            self.assertIsInstance(result.volume, Money)
            self.assertEqual(str(result.volume.currency), "BTC")
            self.assertGreater(result.timestamp, 1414170000)

            if name not in ('btcchina', 'kraken'):  # These do not implement the ticker timeout in the same way
                mod.REQ_TIMEOUT = 0.0001
                self.assertRaises(ExchangeError, mod.eclass.get_ticker)
                mod.REQ_TIMEOUT = 10

    def test_get_balance(self):
        for name, mod in EXCHANGE.iteritems():
            print "test_get_balance %s" % name
            total = mod.exchange.get_balance(btype='total')
            self.assertIsInstance(total, MultiMoney)

            avail = mod.exchange.get_balance(btype='available')
            self.assertIsInstance(avail, MultiMoney)

            result = mod.exchange.get_balance(btype='both')
            self.assertIsInstance(result, tuple)
            self.assertIsInstance(result[0], MultiMoney)
            self.assertEqual(result[0], total)
            self.assertIsInstance(result[1], MultiMoney)
            self.assertEqual(result[1], avail)

    def test_create_order(self):
        for name, mod in EXCHANGE.iteritems():
            print "test_create_order %s" % name
            ticker = mod.exchange.get_ticker()
            bid_price = float(ticker.last.amount) / 2
            bid_size = 0.02
            if bid_price * bid_size < 5.5:  # minimum order size is $5 on bitstamp, which is the highest min size
                bid_size = 5.5 / bid_price
            ask_price = float(ticker.last.amount) * 2
            bal = mod.exchange.get_balance(btype='available')
            if bal.getMoneys(mod.exchange.fiatcurrency) > Money(bid_price * bid_size, currency=mod.exchange.fiatcurrency):
                oid = mod.exchange.create_order(amount=bid_size, price=bid_price, otype='bid')
                self.assertIsInstance(oid, str)
            else:
                print "insufficient balance to test create bid order for %s" % name

            self.assertRaises(ExchangeError, mod.exchange.create_order, amount=100000000, price=10,
                              otype='bid')

            if bal.getMoneys('BTC') >= Money(0.02):
                oid = mod.exchange.create_order(amount=0.02, price=ask_price, otype='ask')
                self.assertIsInstance(oid, str)
            else:
                print "insufficient balance to test create ask order for %s" % name

            toomuch = bal.getMoneys('BTC') * 2
            self.assertRaises(ExchangeError, mod.exchange.create_order, amount=float(toomuch.amount), price=ask_price,
                              otype='ask')

    def test_z_cancel_orders(self):
        for name, mod in EXCHANGE.iteritems():
            print "test_z_cancel_orders %s" % name
            resp = mod.exchange.cancel_orders()
            self.assertIsInstance(resp, bool)
            self.assertTrue(resp)

    def test_order_book(self):
        for name, mod in EXCHANGE.iteritems():
            print "test_order_book %s" % name
            raw_book = mod.eclass.get_order_book()

            # check raw book for formatting
            self.assertIn('asks', raw_book)
            self.assertIn('bids', raw_book)
            self.assertGreater(len(raw_book['asks']), 0)
            self.assertGreater(len(raw_book['bids']), 0)

            # check format_book_item
            for i in raw_book['asks']:
                item = mod.eclass.format_book_item(i)
                self.assertIsInstance(item, OrderbookItem)
                self.assertIsInstance(item[0], Decimal)
                self.assertIsInstance(item[1], Decimal)

            # check best_bid and best_ask are correct
            best_bid = mod.eclass.format_book_item(raw_book['bids'][exchange_config[name]['best_bid']])
            best_ask = mod.eclass.format_book_item(raw_book['asks'][exchange_config[name]['best_ask']])
            self.assertGreaterEqual(float(best_bid[0]) * 1.05, float(best_ask[0]))

    def test_deposit_address(self):
        for name, mod in EXCHANGE.iteritems():
            if name in ('btce', 'huobi', 'okcoin'):
                continue  # these don't support this feature
            print "test_deposit_address %s" % name
            addy = mod.exchange.get_deposit_address()
            self.assertIsInstance(addy, str)
            self.assertIn(addy[0], '13')
            # todo real address hash check

    def test_get_open_orders(self):
        for name, mod in EXCHANGE.iteritems():
            print "test_get_open_orders %s" % name
            orders = mod.exchange.get_open_orders()
            self.assertIsInstance(orders, list)
            for o in orders:
                self.assertIsInstance(o, MyOrder)
                self.assertIsInstance(o.price, Money)
                self.assertEqual(str(o.price.currency), mod.exchange.fiatcurrency)
                self.assertIsInstance(o.amount, Money)
                self.assertEqual(str(o.amount.currency), 'BTC')
                self.assertIn(o.side, ('bid', 'ask'))
                self.assertIn(o.exchange, EXCHANGE)
                self.assertIsInstance(o.order_id, str)


if __name__ == "__main__":
    unittest.main()
