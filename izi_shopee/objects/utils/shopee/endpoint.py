# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import hashlib
import hmac
import time
import json


class ShopeeEndpoint(object):

    HOSTS = {
        'base': 'https://partner.shopeemobile.com'
    }

    ENDPOINTS = {
        'v1': {
            'get_awb_url': ('POST', '/api/v1/logistics/airway_bill/get_mass'),
            'get_my_income': ('POST', '/api/v1/orders/income')
        },
        'v2': {
            'auth': ('POST', '/api/v2/shop/auth_partner'),
            'token_renew': ('POST', '/api/v2/auth/access_token/get'),
            'token_get': ('POST', '/api/v2/auth/token/get'),
            'shop_info': ('GET', '/api/v2/shop/get_shop_info'),
            'profile_info': ('GET', '/api/v2/shop/get_profile'),
            'logistic_list': ('GET', '/api/v2/logistics/get_channel_list'),
            'product_list': ('GET', '/api/v2/product/get_item_list'),
            'product_info': ('GET', '/api/v2/product/get_item_base_info'),
            'product_variant_list': ('GET', '/api/v2/product/get_model_list'),
            'order_list': ('GET', '/api/v2/order/get_order_list'),
            'order_detail': ('GET', '/api/v2/order/get_order_detail'),
            'shipping_doc_info': ('GET', '/api/v2/logistics/get_shipping_document_info'),
            'shipping_parameter': ('GET', '/api/v2/logistics/get_shipping_parameter'),
            'ship_order': ('POST', '/api/v2/logistics/ship_order'),
            'batch_ship_order': ('POST', '/api/v2/logistics/batch_ship_order'),
            'reject_order': ('POST', '/api/v2/order/cancel_order'),
            'buyer_cancellation': ('POST', '/api/v2/order/handle_buyer_cancellation'),
            'get_awb_num': ('GET', '/api/v2/logistics/get_tracking_number'),
            'set_push_webhook': ('POST', '/api/v2/push/set_push_config')
        }
    }

    def __init__(self, sp_account, host="base", api_version="v2"):
        self.sp_account = sp_account
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
            'endpoint': self.get_endpoints(endpoint_key)[1].format(**vars(self.sp_account))
        }
        return "{host}{endpoint}".format(**data)

    def timestamp(self):
        return(int(time.time()))

    def v1_sign(self, url, body, partner_key):
        bs = url + "|" + json.dumps(body)
        dig = hmac.new(partner_key.encode(), msg=bs.encode(), digestmod=hashlib.sha256).hexdigest()
        return dig

    def v2_sign(self, endpoint_key, partner_id, partner_key, shop_id, timeest, access_token=False):

        if not access_token:
            base_string = '%s%s%s%s' % (partner_id, self.get_endpoints(endpoint_key)[1], timeest, shop_id)
        else:
            base_string = '%s%s%s%s%s' % (partner_id,
                                          self.get_endpoints(endpoint_key)[1],
                                          timeest, access_token, shop_id)
        sign = hmac.new(partner_key.encode(), base_string.encode(), hashlib.sha256).hexdigest()

        return sign

    def v2_build_request(self, endpoint_key, partner_id, partner_key, shop_id, access_token=False, **kwargs):
        headers = dict({
            'Content-Length': '0',
            'User-Agent': 'PostmanRuntime/7.17.1',
            'Content-Type': 'application/json'
        }, **kwargs.get('headers', {}))

        timeest = self.timestamp()
        if not access_token:
            sign = self.v2_sign(endpoint_key, partner_id, partner_key, shop_id, timeest)
            params = dict({
                'partner_id': partner_id,
                'shop_id': shop_id,
                'timestamp': timeest,
                'sign': sign

            }, **kwargs.get('params', {}))
        else:
            sign = self.v2_sign(endpoint_key, partner_id, partner_key, shop_id, timeest, access_token)
            params = dict({
                'partner_id': partner_id,
                'shop_id': shop_id,
                'timestamp': timeest,
                'sign': sign,
                'access_token': access_token

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

    def v1_build_request(self, endpoint_key, partner_id, partner_key, shop_id, **kwargs):
        timeest = self.timestamp()
        body = {
            'partner_id': int(partner_id),
            'shopid': int(shop_id),
            'timestamp': timeest,
        }
        if 'json' in kwargs:
            body.update(kwargs.get('json'))

        sign = self.v1_sign(self.get_url(endpoint_key), body, partner_key)
        headers = dict({
            'Content-Length': '0',
            'User-Agent': 'PostmanRuntime/7.17.1',
            'Content-Type': 'application/json',
            'Authorization': sign
        }, **kwargs.get('headers', {}))

        prepared_request = {
            'method': self.get_endpoints(endpoint_key)[0],
            'url': self.get_url(endpoint_key),
            'headers': headers
        }

        if self.get_endpoints(endpoint_key)[0] in ["POST", "PUT", "PATH"]:
            prepared_request.update({'json': body})
        else:
            prepared_request.update({'params': body})

        if 'data' in kwargs:
            prepared_request.update({'data': kwargs.get('data')})

        if 'files' in kwargs:
            prepared_request.update({'files': kwargs.get('files')})

        return prepared_request
