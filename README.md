# Bitcoin Exchange Clients
===============

Clients for managing your Bitcoin exchange accounts. For use in high volume trading by a control application.
Differences in formatting and performance have been evened out using the tools in [bitcoin_exchanges/exchange_util.py](https://github.com/coinapult/bitcoin_exchanges/blob/master/bitcoin_exchanges/exchange_util.py).

Currently supported exchanges are:

+ [Bitfinex](https://www.bitfinex.com/?refcode=xknTcTvLS2)
+ [BTCChina](https://btcchina.com)
+ [BTC-E](https://btc-e.com)
+ [Kraken](https://www.kraken.com/)
+ [OKCoin](https://www.okcoin.com/?invid=2022222)
+ [Huobi](https://www.huobi.com/)
+ [LakeBTC](https://www.lakebtc.com/?ref=10civ1x)
+ [Bitstamp](https://bitstamp.net)

## Installation
run
```
python setup.py install
```

## Configuration
To configure the exchange credentials, copy and paste each exchange's API keys in exchange_config.py.

### Nonce Database
Next, create a mongo collection for tracking nonce's, and save the connected collection object to
exchange_config.nonceDB.

This is only required for BTC-E, because their nonce max is very low. Mongo is heavy
 for this task, but convenient for the original authors. Feel free to abstract it, if any BTC-E users particularly hate
 mongoDB.

Example:

```python
from pymongo import Connection
nonceDB = Connection().nonce_database['nonce']
```

### Storing configuration file
Move the file to a safe directory and give it read only permissions. Export the directory path to the
environmental variable BITCOIN_EXCHANGE_CONFIG_DIR. You may have to repeat this each session. Use permanent settings like
.bashrc, .bash_profile, .profile or similar.

Example commands in linux:

```
mkdir /etc/exchanges/
cp exchange_config.py /etc/exchanges/
chmod 400 /etc/exchanges/exchange_config.py
export BITCOIN_EXCHANGE_CONFIG_DIR="/etc/exchanges/"
```

## Usage
For detailed examples, see [test/clients.py](https://github.com/coinapult/bitcoin_exchanges/blob/master/test/clients.py).
Basically, if you have everything configured correctly, you can do stuff like this:

```python
from bitcoin_exchanges.exchange_util import get_live_exchange_workers

EXCHANGE = get_live_exchange_workers()

for exch in EXCHANGE:
    balance = EXCHANGE[exch].exchange.get_balance()
    print "%s balance is currently %r" % (exch, balance)
    if balance.getMoneys('USD') > 1000:
        # Cheap bitcoins! Warning, this will market buy bitcoins on every live exchange :D
        # EXCHANGE[exch].exchange.create_order(amount=1, price=1000, otype='bid')
        print "toilet paper"
```
