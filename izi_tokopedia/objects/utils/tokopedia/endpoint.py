# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

class TokopediaEndpoint(object):
    HOSTS = {
        'base': 'https://fs.tokopedia.net',
        'accounts': 'https://accounts.tokopedia.com'
    }

    ENDPOINTS = {
        # api_version: {endpoint_key: (http_method, endpoint_url)}
        'v1': {
            'token': ('POST', '/token?grant_type=client_credentials'),
            'register_key': ('POST', '/v1/fs/{fs_id}/register'),
            'shop_info': ('GET', '/v1/shop/fs/{fs_id}/shop-info'),
            'product_info': ('GET', '/inventory/v1/fs/{fs_id}/product/info'),
            'logistic_active_info': ('GET', '/v1/logistic/fs/{fs_id}/active-info'),
        },
        'v2': {
            'logistic_info': ('GET', '/v2/logistic/fs/{fs_id}/info'),
            'order_list': ('GET', '/v2/order/list'),
            'order_detail': ('GET', '/v2/fs/{fs_id}/order'),
        }
    }

    def __init__(self, tp_account, host="base", api_version="v1"):
        self.tp_account = tp_account
        self.host = host
        self.api_version = api_version

    def get_endpoints(self, endpoint_key=None):
        endpoints = self.ENDPOINTS.get(self.api_version)
        if endpoint_key:
            return endpoints.get(endpoint_key)
        return endpoints

    def get_url(self, endpoint_key):
        data = {
            'host': self.HOSTS[self.host],
            'endpoint': self.get_endpoints(endpoint_key)[1].format(**vars(self.tp_account))
        }
        return "{host}{endpoint}".format(**data)

    def build_request(self, endpoint_key, **kwargs):
        headers = dict({
            'Authorization': self.tp_account.get_auth(),
            'Content-Length': '0',
            'User-Agent': 'PostmanRuntime/7.17.1'
        }, **kwargs.get('headers', {}))

        if kwargs.get('force_params'):
            params = kwargs.get('params', {})
        else:
            params = dict({
                'per_page': 50
            }, **kwargs.get('params', {}))

        prepared_request = {
            'method': self.get_endpoints(endpoint_key)[0],
            'url': self.get_url(endpoint_key),
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
