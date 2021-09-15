# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import requests
import hashlib
import hmac
import time
import urllib
import logging
import json
from .endpoint import ENDPOINTS_PATH,BASE_ENDPOINTS

_logger = logging.getLogger(__name__)

class ShopeeAccount(object):

    def __init__(self, partner_id, partner_key, **kwargs):
        self.partner_id = partner_id
        self.partner_key = partner_key
        self.base_url = kwargs.get('base_url', None)
        self.mp_id = kwargs.get('mp_id', None)
        self.shop_id = kwargs.get('shop_id', None)
        self.code = kwargs.get('code', None)
        self.refresh_token = kwargs.get('refresh_token', None)


    def get_redirect_url(self):
        return '%s/api/user/auth/shopee/%s' % (self.base_url, self.mp_id)
    
    def get_auth_url_v2(self):
        timeest = int(time.time())
        base_string = '%s%s%s' % (self.partner_id, ENDPOINTS_PATH.get('auth'), timeest)
        sign = hmac.new(self.partner_key.encode(), base_string.encode(), hashlib.sha256).hexdigest()
        return '%(host)s%(path)s?partner_id=%(partner_id)s&redirect=%(redirect)s&timestamp=%(timestamp)s&sign=%(sign)s' % {
            'host': BASE_ENDPOINTS.get('sp_base_url'),
            'path': ENDPOINTS_PATH.get('auth'),
            'partner_id': self.partner_id,
            'redirect': urllib.parse.quote(self.get_redirect_url()),
            'timestamp': timeest,
            'sign': sign
        }
    
    def get_token(self):
        if self.shop_id:
            timeest = int(time.time())
            base_string = '%s%s%s%s' % (self.partner_id, ENDPOINTS_PATH.get('token_renew') if self.refresh_token else ENDPOINTS_PATH.get('token_get'), timeest, self.shop_id)
            sign = hmac.new(self.partner_key.encode(), base_string.encode(), hashlib.sha256).hexdigest()
            resp = requests.post('%(url)s%(path)s?partner_id=%(partner_id)s&shop_id=%(shop_id)s&timestamp=%(timestamp)s&sign=%(sign)s' % {
                'url': BASE_ENDPOINTS.get('sp_base_url'),
                'path': ENDPOINTS_PATH.get('token_renew') if self.refresh_token else ENDPOINTS_PATH.get('token_get'),
                'partner_id': int(self.partner_id),
                'shop_id': int(self.shop_id),
                'timestamp': timeest,
                'sign': sign
            }, json={
                **({'refresh_token': self.refresh_token} if self.refresh_token else {'code': self.code}),
                'shop_id': int(self.shop_id),
                'partner_id': int(self.partner_id)
            }, headers={
                'Content-Type': 'application/json'
            })
        
            _logger.info('\n%s' % (json.dumps(resp.json(), indent=2)))
            
            return resp.json()

    
