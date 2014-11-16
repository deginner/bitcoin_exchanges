from collections import namedtuple
from decimal import Decimal
import abc
import importlib
import os
import sys

from moneyed import Money
from pymongo.errors import DuplicateKeyError


config_dir = os.path.dirname(os.environ.get('BITCOIN_EXCHANGE_CONFIG_DIR', '.'))
if config_dir not in sys.path:
    sys.path.append(config_dir)
from exchange_config import exchange_config

OrderbookItem = namedtuple('OrderbookItem', 'price amount')


class ExchangeABC:
    """
    ExchangeABC defines a contract such that any exchange we code for
    must agree to.
    """
    __metaclass__ = abc.ABCMeta
    name = 'Exchange'
    fiatcurrency = 'USD'
    nonceDB = None

    def __init__(self):
        pass

    @abc.abstractmethod
    def cancel_order(self, oid):
        """Cancel a specific order.
        :return: True if order was already or now canceled, otherwise False
        :rtype: bool
        """
        pass

    @abc.abstractmethod
    def cancel_orders(self, otype=None):
        """Cancel all orders, or optionally just those of a given type.
        :return: True if orders were successfully canceled or no orders exist, otherwise False
        :rtype: bool
        """
        pass

    @abc.abstractmethod
    def create_order(self, amount, price, otype):
        """
        Create a new order of a given size, at a certain price and a specific type.
        :return: The unique order id given by the exchange
        :rtype: str
        """
        pass

    def format_book_item(self, item):
        """
        Format an item from the orderbook (e.g. bid or ask) in a specific way.
        If the data provided by the exchange does not match the default
        implementation, then this method must be re-implemented.
        :rtype: OrderbookItem
        """
        # expects each order to be a list with first element as price and second as size
        return OrderbookItem(Decimal(item[0]), Decimal(item[1]))

    def unformat_book_item(self, item):
        """
        Reverse format an item to the raw orderbook style.
        If the data provided by the exchange does not match the default
        implementation, then this method must be re-implemented.
        :rtype: OrderbookItem
        """
        # expects each order to be a list with first element as price and second as size
        return [str(item[0]), str(item[1])]

    @abc.abstractmethod
    def get_balance(self, btype='total'):
        """
        :param str btype: Balance types of 'total', 'available', and 'all' are supported.
        :return: the balance(s) for a exchange. If a btype of 'all' is specified, a tuple with the total balance first
                 then available. (total, available)
        """
        pass

    @abc.abstractmethod
    def get_open_orders(self):
        """
        :return:  a list of open orders.
        :rtype: list
        """
        pass

    @abc.abstractmethod
    def get_order_book(self, pair=None):
        """
        Get the orderbook for this exchange.

        :param pair: If the exchange supports multiple pairs, then the "pair" param
                             can be used to specify a given orderbook. In case the exchange
                             does not support that, then the "pair" param is ignored.
        :return: a list of bids and asks
        :rtype: list
        """
        pass

    @abc.abstractmethod
    def get_ticker(self, pair=None):
        """
        Return the current ticker for this exchange.
        :param pair: If the exchange supports multiple pairs, then the "pair" param
                     can be used to specify a given orderbook. In case the exchange
                     does not support that, then the "pair" param is ignored.
        :return: a Ticker with at minimum bid, ask and last.
        :rtype: Ticker
        """
        pass

    @abc.abstractmethod
    def get_transactions(self, limit=None):
        """
        :param limit: ?
        :return: a list of transactions, possibly only a subset of them."""
        pass

    def next_nonce(self):
        """Atomically increment and get a nonce for an exchange."""
        entry = self.nonceDB.find_and_modify({'exchange': self.name}, {'$inc': {'seq': 1}}, new=True)
        return entry['seq']

    def create_nonce(self, nonce):
        """
        Save a starting nonce for a given exchange.

        :param int nonce: an integer that will be incremented on each
            next_nonce call.
        :return: nonce if an entry was created, None otherwise.
        """
        try:
            self.nonceDB.insert({'exchange': self.name, 'nonce': nonce})
        except DuplicateKeyError:
            # exchange already present.
            return None
        return nonce


class ExchangeError(Exception):
    """
    An error from one of the exchanges.
    """

    def __init__(self, exchange, message):
        self.exchange = exchange
        self.error = message
        super(ExchangeError, self).__init__(message)

    def __str__(self):
        return str(self.exchange) + ":\t" + str(self.error)


Ticker = namedtuple('Ticker', ['bid', 'ask', 'high', 'low', 'volume', 'last',
                               'timestamp'])


# Convenience Function to create tuples
def create_ticker(bid=0, ask=0, high=0, low=0, volume=0, last=0, timestamp=0,
                  currency='USD'):
    return Ticker(Money(bid, currency), Money(ask, currency),
                  Money(high, currency), Money(low, currency),
                  Money(volume, 'BTC'), Money(last, currency),
                  timestamp)


def get_live_exchange_workers():
    exchanges = {}
    for exch in exchange_config:
        if exchange_config[exch]['live']:
            exchanges[exch] = importlib.import_module('bitcoin_exchanges.%s' % exch)
    return exchanges
