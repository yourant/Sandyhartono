# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import uuid
from requests.auth import HTTPBasicAuth


class BlibliEndpoint(object):
    HOSTS = {
        'base': 'https://api.blibli.com'
    }

    ENDPOINTS = {
        # endpoint_key: (http_method, endpoint_url)
        'logistic': ('GET', '/v2/proxy/seller/v1/logistics'),
        'product_list': ('POST', '/v2/proxy/mta/api/businesspartner/v2/product/getProductList'),
        'product_info': ('GET', '/v2/proxy/mta/api/businesspartner/v1/product/detailProduct'),
        'order_list': ('GET', '/v2/proxy/mta/api/businesspartner/v1/order/orderList'),
        'order_detail': ('GET', '/v2/proxy/mta/api/businesspartner/v1/order/orderDetail'),
    }

    def __init__(self, bli_account, host="base"):
        self.bli_account = bli_account
        self.host = host

    def get_url(self, endpoint):
        data = {
            'host': self.HOSTS[self.host],
            'endpoint': self.ENDPOINTS[endpoint][1].format(**vars(self.bli_account))
        }
        return "{host}{endpoint}".format(**data)

    def build_request(self, endpoint, **kwargs):
        headers = dict({
            'Authorization': self.bli_account.get_auth(),
            'Content-Length': '0',
            'User-Agent': 'PostmanRuntime/7.17.1',
            'Api-Seller-Key': self.bli_account.seller_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }, **kwargs.get('headers', {}))

        params = dict({
            'requestId': str(uuid.uuid4())
        }, **kwargs.get('params', {}))

        prepared_request = {
            'method': self.ENDPOINTS[endpoint][0],
            'url': self.get_url(endpoint),
            'params': params,
            'headers': headers
        }

        if 'data' in kwargs:
            prepared_request.update({'data': kwargs.get('data')})

        if 'json' in kwargs:
            prepared_request.update({'json': kwargs.get('json')})

        if 'files' in kwargs:
            prepared_request.update({'files': kwargs.get('files')})

        return prepared_request
