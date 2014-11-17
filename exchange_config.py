# if live == True for an exchange, it will be used, and is available using get_live_exchange_workers
exchange_config = {
    'btcchina': {
        'live': True,
        'api_creds': {'key': '',  'secret': ''}
    },
    'bitstamp': {
        'live': True,
        'api_creds': {'key': '',  'secret': '', 'clientid': ''}
    },
    'bitfinex': {
        'live': True,
        'api_creds': {'key': '', 'secret': ''}
    },
    'btce': {
        'live': True,
        'api_creds': {'key': '', 'secret': ''}
    },
    'kraken': {
        'live': True,
        'api_creds': {'key': '', 'secret': ''}
    }
}

# replace with mongoDB collection for nonce tracking
# from pymongo import Connection
# nonceDB = Connection().nonce_database['nonce']