Bitcoin Exchange Clients
===============

Clients for managing your Bitcoin exchange accounts.

To configure the exchange credentials, copy and paste each exchange's API keys in exchange_config.py.

Next, create a mongo collection for tracking nonce's, and save the connected collection object to
exchange_config.nonceDB.

Example:

from pymongo import Connection
nonceDB = Connection().nonce_database['nonce']

Finally move the file to a safe directory and give it read only permissions. Finally, export the directory path to the
environmental variable BITCOIN_EXCHANGE_CONFIG_DIR.

Example commands in linux:

mkdir /etc/exchanges/
cp exchange_config.py /etc/exchanges/
chmod 400 /etc/exchanges/exchange_config.py
export BITCOIN_EXCHANGE_CONFIG_DIR="/etc/exchanges/"

