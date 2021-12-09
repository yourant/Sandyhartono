# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import requests
from base64 import b64encode
from requests.auth import HTTPBasicAuth
from .tools import validate_response
from .endpoint import BlibliEndpoint


class BlibliAccount(object):

    def __init__(self, usermail, shop_name, **kwargs):
        self.usermail = usermail
        self.shop_name = shop_name
        self.shop_code = kwargs.get('shop_code', None)
        self.seller_key = kwargs.get('seller_key', None)
        self.store_id = kwargs.get('store_id', None)
        self.client_id = kwargs.get('client_id', None)
        self.client_secret = kwargs.get('client_secret', None)
        self.endpoints = BlibliEndpoint(self)

    def get_auth(self):
        auth = 'Basic %s' % b64encode('{}:{}'.format(self.client_id, self.client_secret).encode()).decode()
        return auth

    def authenticate(self):
        # Test with API if credential is True
        params = {
            'storeCode': self.shop_code,
            'channelId': self.shop_name,
            'username': self.usermail,
            'storeId': str(self.store_id)
        }
        prepared_request = self.endpoints.build_request('logistic', **{
            'params': params
        })
        response = validate_response(requests.request(**prepared_request))
        return response.json()
