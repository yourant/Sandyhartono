# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import uuid
import requests
from requests.auth import HTTPBasicAuth
# from .endpoint import ENDPOINTS_PATH,BASE_ENDPOINTS


class BlibliAccount(object):

    def __init__(self, usermail, shop_name, **kwargs):
        self.usermail = usermail
        self.shop_name = shop_name
        self.shop_code = kwargs.get('shop_code', None)
        self.seller_key = kwargs.get('seller_key', None)
        self.store_id = kwargs.get('store_id', None)
        self.client_id = kwargs.get('client_id', None)
        self.client_secret = kwargs.get('client_secret', None)

    def authenticate(self):
        # Test with API if credential is True
        params = {
            'requestId': 'IZI-'+ str(uuid.uuid4()),
            'storeCode': self.shop_code,
            'channelId': self.shop_name,
            'username': self.usermail,
            'storeId': int(self.store_id)
        }
        res = requests.get(
            'https://api.blibli.com/v2/proxy/seller/v1/logistics', 
            auth=HTTPBasicAuth(self.client_id, self.client_secret),
            params=params,
            headers={
                'Api-Seller-Key': self.seller_key,
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        )
        if res.status_code == 200:
            result = True
        else:
            result = False
        return result