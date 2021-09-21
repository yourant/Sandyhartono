# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import hashlib
import hmac
import time


class ShopeeEndpoint(object):

    HOSTS = {
        'base': 'https://partner.shopeemobile.com'
    }

    ENDPOINTS = {
        'auth': ('POST', '/api/v2/shop/auth_partner'),
        'token_renew': ('POST', '/api/v2/auth/access_token/get'),
        'token_get': ('POST', '/api/v2/auth/token/get'),
        'logistic_list': ('GET', '/api/v2/logistics/get_channel_list'),
        'product_list': ('GET', '/api/v2/product/get_item_list'),
        'product_info': ('GET', '/api/v2/product/get_item_base_info'),
        'product_variant_list': ('GET', '/api/v2/product/get_model_list')
    }

    def __init__(self, sp_account, host="base"):
        self.sp_account = sp_account
        self.host = host

    def get_url(self, endpoint):
        data = {
            'host': self.HOSTS[self.host],
            'endpoint': self.ENDPOINTS[endpoint][1].format(**vars(self.sp_account))
        }
        return "{host}{endpoint}".format(**data)

    def timestamp(self):
        return(int(time.time()))

    def sign(self, endpoint, partner_id, partner_key, shop_id, timeest, access_token=False):

        if not access_token:
            base_string = '%s%s%s%s' % (partner_id, self.ENDPOINTS[endpoint][1], timeest, shop_id)
        else:
            base_string = '%s%s%s%s%s' % (partner_id, self.ENDPOINTS[endpoint][1], timeest, access_token, shop_id)
        sign = hmac.new(partner_key.encode(), base_string.encode(), hashlib.sha256).hexdigest()

        return sign

    def build_request(self, endpoint, partner_id, partner_key, shop_id, access_token=False, **kwargs):
        headers = dict({
            'Content-Length': '0',
            'User-Agent': 'PostmanRuntime/7.17.1',
            'Content-Type': 'application/json'
        }, **kwargs.get('headers', {}))

        timeest = self.timestamp()
        if not access_token:
            sign = self.sign(endpoint, partner_id, partner_key, shop_id, timeest)
            params = dict({
                'partner_id': partner_id,
                'shop_id': shop_id,
                'timestamp': timeest,
                'sign': sign

            }, **kwargs.get('params', {}))
        else:
            sign = self.sign(endpoint, partner_id, partner_key, shop_id, timeest, access_token)
            params = dict({
                'partner_id': partner_id,
                'shop_id': shop_id,
                'timestamp': timeest,
                'sign': sign,
                'access_token': access_token

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
