exchange_config = {
    'btcchina': {
        'live': True,
        'trade_fee': 0.00,
        'dominant_pair': "btccny",
        'api_keys': {'key': '',  'secret': ''}
    },
    'bitstamp': {
        'live': True,
        'trade_fee': 0.002,
        'dominant_pair': "btcusd",
        'api_keys': {'key': '',  'secret': ''}
    },
    'bitfinex': {
        'live': True,
        'withdrawal_fee_range': [0, 0],
        'dominant_pair': "btcusd",
        'api_keys': {'key': '', 'secret': ''}
    },
    'btce': {
        'live': True,
        'trade_fee': 0.002,
        'dominant_pair': "btcusd",
        'api_keys': {'key': '',
                     'secret': ''}

    },
    'kraken': {
        'live': True,
        'trade_fee': 0.005,
        'dominant_pair': "btceur",
        'api_keys': {'key': '', 'secret': ''}
    }
}

nonceDB = None  # replace with mongoDB database for nonce tracking