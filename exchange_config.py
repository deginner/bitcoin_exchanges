BLOCK_ORDERS = False  # If True, then orders will not be submitted to exchanges

# if live == True for an exchange, it will be used, and is available using get_live_exchange_workers
exchange_config = {
    'btcchina': {
        'live': True,
        'best_bid': 0,  # confirmed
        'best_ask': -1,  # confirmed
        'api_creds': {'key': '',  'secret': ''}
    },
    'bitstamp': {
        'live': True,
        'best_bid': 0,  # confirmed
        'best_ask': 0,  # confirmed
        'api_creds': {'key': '',  'secret': '', 'clientid': ''}
    },
    'bitfinex': {
        'live': True,
        'best_bid': 0,  # confirmed
        'best_ask': 0,  # confirmed
        'api_creds': {'key': '', 'secret': ''}
    },
    'btce': {
        'live': True,
        'best_bid': 0,  # confirmed
        'best_ask': 0,  # confirmed
        'api_creds': {'key': '', 'secret': ''},
        'address': ''  # a deposit address from your account
    },
    'huobi': {
        'live': True,
        'best_bid': 0,  # confirmed
        'best_ask': -1,  # confirmed
        'api_creds': {'key': '', 'secret': ''},
        'address': ''  # a deposit address from your account
    },
    'kraken': {
        'live': True,
        'best_bid': 0,  # confirmed
        'best_ask': 0,  # confirmed
        'api_creds': {'key': '', 'secret': ''}
    },
    'lakebtc': {
        'live': True,
        'best_bid': 0,  # confirmed
        'best_ask': 0,  # confirmed
        'api_creds': {'key': '', 'secret': ''},  # key is your email address
        'address': ''  # a deposit address from your account
    },
    'okcoin': {
        'live': True,
        'best_bid': 0,  # confirmed
        'best_ask': -1,  # confirmed
        'api_creds': {'partner': '', 'secret': ''},
        'address': ''  # a deposit address from your account
    },
    'poloniex': {
        'live': True,
        'best_bid': 0, 
        'best_ask': -1, 
        'api_creds': {'key': '',
                      'secret': ''},
        'address': ''  # a deposit address from your account
    }
    
}

# replace with mongoDB collection for nonce tracking
# from pymongo import Connection
# nonceDB = Connection().nonce_database['nonce']
