# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

class TokopediaEndpoint(object):
    HOSTS = {
        'base': 'https://fs.tokopedia.net',
        'accounts': 'https://accounts.tokopedia.com'
    }

    ENDPOINTS = {
        'token': ('POST', '/token?grant_type=client_credentials'),
        'shop_info': ('GET', '/v1/shop/fs/{fs_id}/shop-info'),
        'product_info': ('GET', '/inventory/v1/fs/{fs_id}/product/info')
    }

    def __init__(self, tp_account, host="base"):
        self.tp_account = tp_account
        self.host = host

    def get_url(self, endpoint):
        data = {
            'host': self.HOSTS[self.host],
            'endpoint': self.ENDPOINTS[endpoint][1].format(**vars(self.tp_account))
        }
        return "{host}{endpoint}".format(**data)

    def build_request(self, endpoint, **kwargs):
        headers = dict({
            'Authorization': self.tp_account.get_auth(),
            'Content-Length': '0',
            'User-Agent': 'PostmanRuntime/7.17.1'
        }, **kwargs.get('headers', {}))

        params = dict({
            'per_page': 50
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
