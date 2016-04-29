BLOCK_ORDERS = False  # If True, then orders will not be submitted to exchanges

"""
:param 'live'       bool: if live == True for an exchange, it will be used, and is available using get_live_exchange_workers
:param 'live_pairs' list: if a pair is present in list, it will be used, and is available using get_live_pairs 
                          the pair must confrom to the standard formating
:supported pairs: the comment 'suppported pairs' provides a list of pairs each client supports. This is meant to be a reference to indicate which pairs can be specified in the 'live_pairs' parameter.
"""
exchange_config = {
    'btcchina': {
        'live': False,
        'best_bid': 0,  # confirmed
        'best_ask': -1,  # confirmed
        'live_pairs': [],
        # supported pairs ['BTC_CNY', 'LTC_CNY', 'LTC_BTC']
        'api_creds': {'key': '',  'secret': ''}
    },
    'bitstamp': {
        'live': False,
        'best_bid': 0,  # confirmed
        'best_ask': 0,  # confirmed
        'live_pairs': [],
        # Bitstamp only supports BTC_USD.
        'api_creds': {'key': '',  'secret': '', 'clientid': ''}
},
    'bitfinex': {
        'live': False,
        'best_bid': 0,  # confirmed
        'best_ask': 0,  # confirmed
        'live_pairs': [],
        # supported pairs:  ['BTC_USD', 'LTC_USD', 'LTC_BTC', 'ETH_USD', 'ETH_BTC']
        'api_creds': {'key': '', 'secret': ''}
    },
    'btce': {
        'live': False,
        'best_bid': 0,  # confirmed
        'best_ask': 0,  # confirmed
        'live_pairs': [],
        # supported paire: ['BTC_USD', 'BTC_EUR', 'LTC_BTC']
        'api_creds': {'key': '', 'secret': ''},
        'address': ''  # a deposit address from your account
    },
    'huobi': {
        'live': False,
        'best_bid': 0,  # confirmed
        'best_ask': -1,  # confirmed
        'live_pairs': [],
        # supported pairs: ['BTC_USD', 'BTC_CNY', 'LTC_CNY']
        'api_creds': {'key': '', 'secret': ''},
        'address': ''  # a deposit address from your account
    },
    'kraken': {
        'live': False,
        'best_bid': 0,  # confirmed
        'best_ask': 0,  # confirmed
        'live_pairs': [],
        # supported pairs: ['BTC_USD', 'BTC_EUR', 'LTC_USD', 'BTC_LTC']
        # Note: Kraken uses BTC_LTC instead of the more common LTC_BTC
        'api_creds': {'key': '', 'secret': ''}
    },
    'lakebtc': {
        'live': False,
        'best_bid': 0,  # confirmed
        'best_ask': 0,  # confirmed
        'live_pairs': [],
        # supported pairs: ['BTC_USD', 'BTC_EUR', 'BTC_JPY', 'BTC_GBP', 'BTC_CNY']
        # Note: these are the only offered via https://www.lakebtc.com/api_v1/ticker
        'address': ''  # a deposit address from your account
    },
    'okcoin': {
        'live': False,
        'best_bid': 0,  # confirmed
        'best_ask': -1,  # confirmed
        'live_pairs': [],
        # supported_pairs: ['BTC_USD', 'LTC_USD']
        'api_creds': {'partner': '', 'secret': ''},
        'address': ''  # a deposit address from your account
    },
    'poloniex': {
        'live': False,
        'best_bid': 0, #confirmed
        'best_ask': 0, #confirmed
        'live_pairs': [],
        # supported pairs: ['BTC_USDT', 'DASH_BTC', 'DASH_USDT'],
        'api_creds': {'key': '',
                      'secret': ''},
        'address': ''  # a deposit address from your account
    },
    'exmo': {
        'live': False,
        'best_bid': 0, #confirmed
        'best_ask': 0, #confirmed
        'live_pairs': [],
        # supported pairs: [
        # 'BTC_EUR", 'BTC_USD',
        # 'DASH_BTC','DASH_USD',
        # 'ETH_BTC', 'ETH_USD']
        'api_creds': {'key': '',
                      'secret': ''},
        'address': ''  # a deposit address from your account
    },
    'bittrex': {
        'live': False,
        'best_bid': 0,
        'best_ask': -1, 
        'live_pairs': [],
        # supported pairs: ['BTC_USDT', 'DASH_BTC', 'DASH_USDT'],
        'api_creds': {'key': '',
                      'secret': ''},
        'address': ''  # a deposit address from your account
    }
    
}

# replace with mongoDB collection for nonce tracking
# from pymongo import Connection
# nonceDB = Connection().nonce_database['nonce']
