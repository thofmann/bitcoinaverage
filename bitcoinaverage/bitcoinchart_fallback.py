import simplejson
import time
import socket
from decimal import Decimal

import requests
from requests.exceptions import ConnectionError

from bitcoinaverage.api_parsers import API_QUERY_CACHE
from bitcoinaverage.config import BITCOIN_CHARTS_API_URL, DEC_PLACES, API_QUERY_FREQUENCY, API_IGNORE_TIMEOUT, API_REQUEST_HEADERS
from bitcoinaverage.exceptions import CallFailedException
from bitcoinaverage.helpers import write_log


def fetchBitcoinChartsData():
    global API_QUERY_CACHE, API_QUERY_FREQUENCY

    if 'bitcoincharts' not in API_QUERY_CACHE:
        API_QUERY_CACHE['bitcoincharts'] = {'last_call_timestamp': 0,
                                            'result': None,
                                            'call_fail_count': 0,
                                               }

    current_timestamp = int(time.time())
    if (API_QUERY_CACHE['bitcoincharts']['last_call_timestamp']+API_QUERY_FREQUENCY['bitcoincharts'] > current_timestamp):
        result = API_QUERY_CACHE['bitcoincharts']['result']
    else:
        try:
            result = requests.get(BITCOIN_CHARTS_API_URL, verify=False, headers=API_REQUEST_HEADERS).json()
            API_QUERY_CACHE['bitcoincharts'] = {'last_call_timestamp': current_timestamp,
                                                'result':result,
                                                'call_fail_count':0,
                                                   }
        except (KeyError,
                ValueError,
                requests.exceptions.ConnectionError,
                socket.error,
                simplejson.decoder.JSONDecodeError) as error:
            if (API_QUERY_CACHE['bitcoincharts']['last_call_timestamp']+API_IGNORE_TIMEOUT > current_timestamp):
                result = API_QUERY_CACHE['bitcoincharts']['result']
                API_QUERY_CACHE['bitcoincharts']['call_fail_count'] = API_QUERY_CACHE['bitcoincharts']['call_fail_count'] + 1
                write_log('%s call failed, %s fails in a row, using cache, cache age %ss' % ('bitcoincharts',
                            str(API_QUERY_CACHE['bitcoincharts']['call_fail_count']),
                            str(current_timestamp-API_QUERY_CACHE['bitcoincharts']['last_call_timestamp']) ),
                          'WARNING')
            else:
                exception = CallFailedException()
                exception.text = exception.text % (str(API_QUERY_CACHE['bitcoincharts']['call_fail_count']))
                write_log(exception.text, 'ERROR')
                raise exception

    return result

def getData(bitcoincharts_symbols):
    bitcoincharts_data = fetchBitcoinChartsData()

    return_result = {}
    return_result['data_source'] = 'bitcoincharts'
    for api in bitcoincharts_data:
        for currency_code in bitcoincharts_symbols:
            if api['symbol'] == bitcoincharts_symbols[currency_code]:
                return_result[currency_code] = {'ask': Decimal(api['ask']).quantize(DEC_PLACES),
                                                'bid': Decimal(float(api['bid'])).quantize(DEC_PLACES),
                                                'last': Decimal(float(api['close'])).quantize(DEC_PLACES),
                                                'volume': Decimal(float(api['volume'])).quantize(DEC_PLACES),
                                                   }

    return return_result