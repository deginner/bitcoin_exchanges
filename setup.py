import setuptools

setuptools.setup(
    name='bitcoin_exchanges',
    version='0.0.2',
    packages=['bitcoin_exchanges', 'bitcoin_exchanges.old'],
    url='',
    license='GPLv3',
    author='coinapult',
    author_email='admin@coinapult.com',
    description='Clients for managing your Bitcoin exchange accounts',
    zip_safe=False,
    install_requires=[
        'requests',
        'pymongo',
        'hashlib'
    ],
    dependency_links=['git+https://github.com/bearbones/py-moneyed/',
                      'requests',
                      'pymongo',
                      'hashlib']
)
