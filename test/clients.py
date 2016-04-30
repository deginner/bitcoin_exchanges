from decimal import Decimal
import unittest

from moneyed import Money, MultiMoney

from bitcoin_exchanges.exchange_util import get_live_exchange_workers, Ticker, \
    ExchangeError, OrderbookItem, \
    exchange_config, MyOrder, get_live_exchange_pairs

EXCHANGE = get_live_exchange_workers()
PAIRS = get_live_exchange_pairs()
                
class TestAPI(unittest.TestCase):
            
    def test_ticker(self):
        """For each live exchange, poll for ticker for each pair enabled
        for the exchange and check that the returned result conforms to
        the create_ticker function in exchange_util.
        """
        for name, mod in EXCHANGE.iteritems():
            print "test_ticker %s" % name
            pairs = PAIRS[name]
            print pairs
            for pair in pairs:
                print pair
                result = mod.eclass.get_ticker(pair)
                print result
            self.assertIsInstance(result, Ticker)

            self.assertIsInstance(result.bid, Money)
            # check bid cur is quote cur
            quote = mod.exchange.quote_currency(pair)
            self.assertEqual(str(result.bid.currency), quote)
            self.assertIsInstance(result.ask, Money)
            self.assertIsInstance(result.high, Money)
            self.assertIsInstance(result.low, Money)
            self.assertIsInstance(result.last, Money)
            self.assertIsInstance(result.volume, Money)
            # check volume cur is base cur
            base = mod.exchange.base_currency(pair)
            self.assertEqual(str(result.volume.currency), base)
            self.assertGreater(result.timestamp, 1414170000)
            if name not in ('btcchina', 'kraken'):
            # These do not implement the ticker timeout in the same way
                mod.REQ_TIMEOUT = 0.0001
                self.assertRaises(ExchangeError, mod.eclass.get_ticker)
                mod.REQ_TIMEOUT = 10
                
    def test_get_balance(self):
        """Retrieve your balance from each live exchange, verify formatting"""
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
        """Attempt to create bid and sell orders for each live pair on 
           each live exchange.
        """
        for name, mod in EXCHANGE.iteritems():
            print "test_create_order %s" % name
            pairs = PAIRS[name]
            for pair in pairs:
                print pair
                ticker = mod.eclass.get_ticker(pair)
                print ticker
                bid_price = float(ticker.last.amount) / 2
                print bid_price
                amount = 0.02
                if pair[0] == 'B':
                    """
                    If the BTC_USD price is less than $275, 
                    increase the amount, otherwise the condition will bid too high

                    TODO: check and augment amount if bid_price * 0.02 < 5.5
                    """
                    if bid_price * 0.02 < 5.5:  # minimum order size is $5 on bitstamp, which is the highest min size
                        bid_price = 5.5 / 0.02
                elif pair[0] == 'L': # minimum LTC amount for btc-e is 0.1LTC
                    amount = 0.5
                elif pair[0] == 'D':
                    amount = 0.5
                ask_price = float(ticker.last.amount) * 2
                print ask_price
                bal = mod.exchange.get_balance(btype='available')
                if bal.getMoneys(mod.exchange.quote_currency(pair)) > Money(bid_price * amount, currency=mod.exchange.quote_currency(pair)):
                    oid = mod.exchange.create_order(amount=amount, price=bid_price, otype='bid', pair=pair)
                    print oid
                    self.assertIsInstance(oid, str)
                else:
                    print "insufficient balance to test create bid order for %s %s" % (name, pair)

                self.assertRaises(ExchangeError, mod.exchange.create_order, amount=100000000,
                                      price=10, otype='bid', pair=pair)
                
                if bal.getMoneys(mod.exchange.base_currency(pair)) >= Money(amount, currency=mod.exchange.base_currency(pair)):
                    oid = mod.exchange.create_order(amount=amount, price=ask_price, otype='ask', pair=pair)
                    print oid
                    self.assertIsInstance(oid, str)
                else:
                    print "insufficient balance to test create ask order for %s %s" % (name, pair)

                toomuch = bal.getMoneys(mod.exchange.base_currency(pair)) * 2
                self.assertRaises(ExchangeError, mod.exchange.create_order, amount=float(toomuch.amount), price=ask_price, otype='ask', pair=pair)

    def test_z_cancel_orders(self):
        """Cancel all orders for all live pairs on all live exchanges"""
        for name, mod in EXCHANGE.iteritems():
            print "test_z_cancel_orders %s" % name
            pairs = PAIRS[name]
            print pairs
            for pair in pairs:
                print pair                
                resp = mod.exchange.cancel_orders(pair)
                print resp
            
            self.assertIsInstance(resp, bool)
            self.assertTrue(resp)

    def test_order_book(self):
        """For each live exchange, poll for the orderbook for each pair enabled
           and check the result conforms to the default orderbook 
           implemenation.  

           The default order book implementation expects each order to be 
           a list with first element as price and second as size.
        """
        for name, mod in EXCHANGE.iteritems():
            print "test_order_book %s" % name
            pairs = PAIRS[name]
            print pairs
            for pair in pairs:
                print pair
                raw_book = mod.eclass.get_order_book(pair)
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
            print addy
            self.assertIsInstance(addy, str)
            self.assertIn(addy[0], '13')
            # todo real address hash check

    def test_get_open_orders(self):
        """Retrieve all open orders for all live pairs on all live exchanges
        and confirm the result conforms with MyOrder in exchange_util
        """
        for name, mod in EXCHANGE.iteritems():
            print "test_get_open_orders %s" % name
            
            pairs = PAIRS[name]
            print pairs
            for pair in pairs:
                print pair
                orders = mod.exchange.get_open_orders(pair)
                print orders
                self.assertIsInstance(orders, list)
                
                for o in orders:
                    self.assertIsInstance(o, MyOrder)
                    self.assertIsInstance(o.price, Money)
                    self.assertEqual(str(o.price.currency), mod.exchange.quote_currency(pair))
                    self.assertIsInstance(o.amount, Money)
                    self.assertEqual(str(o.amount.currency), mod.exchange.base_currency(pair))
                    self.assertIn(o.side, ('bid', 'ask'))
                    self.assertIn(o.exchange, EXCHANGE)
                    self.assertIsInstance(o.order_id, str)
                    
if __name__ == "__main__":
    unittest.main()
