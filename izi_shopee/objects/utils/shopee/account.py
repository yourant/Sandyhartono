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

    def __init__(self, partner_id, partner_key):
        self.partner_id = partner_id
        self.partner_key = partner_key


    def get_redirect_url(self):
        if self.ensure_one() and isinstance(self.id, int):
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            return '%s/api/user/auth/shopee/%s' % (base_url, self.id)

    def get_auth_url_v2(self):
        timeest = int(time.time())
        base_string = '%s%s%s' % (self.partner_id, ENDPOINTS_PATH.get('auth'), timeest)
        sign = hmac.new(self.partner_key.encode(), base_string.encode(), hashlib.sha256).hexdigest()
        if self.ensure_one() and isinstance(self.id, int):
            return '%(host)s%(path)s?partner_id=%(partner_id)s&redirect=%(redirect)s&timestamp=%(timestamp)s&sign=%(sign)s' % {
                'host': BASE_ENDPOINTS.get('sp_base_url'),
                'path': ENDPOINTS_PATH.get('auth'),
                'partner_id': self.partner_id,
                'redirect': urllib.parse.quote(self.get_redirect_url()),
                'timestamp': timeest,
                'sign': sign
            }
    
    def get_token(self, **kwargs):
        mp_token_obj = self.env['mp.token']

        code = kwargs.get('code')
        shop_id = kwargs.get('shop_id')
        refresh_token = kwargs.get('refresh_token')
        last_code_id = kwargs.get('last_code_id')

        if self.ensure_one() and shop_id: 
            timeest = int(time.time())
            base_string = '%s%s%s%s' % (self.partner_id, ENDPOINTS_PATH.get('token_renew') if refresh_token else ENDPOINTS_PATH.get('token_get'), timeest, shop_id)
            sign = hmac.new(self.partner_key.encode(), base_string.encode(), hashlib.sha256).hexdigest()
            resp = requests.post('%(url)s%(path)s?partner_id=%(partner_id)s&shop_id=%(shop_id)s&timestamp=%(timestamp)s&sign=%(sign)s' % {
                'url': BASE_ENDPOINTS.get('sp_base_url'),
                'path': ENDPOINTS_PATH.get('token_renew') if refresh_token else ENDPOINTS_PATH.get('token_get'),
                'partner_id': self.partner_id,
                'shop_id': int(shop_id),
                'timestamp': timeest,
                'sign': sign
            }, json={
                **({'refresh_token': refresh_token} if refresh_token else {'code': code}),
                'shop_id': int(shop_id),
                'partner_id': self.partner_id
            }, headers={
                'Content-Type': 'application/json'
            })
            
            _logger.info('\n%s' % (json.dumps(resp.json(), indent=2)))
            if resp.json().get('access_token') and resp.json().get('refresh_token') and  resp.json().get('expire_in'):
                mp_token_obj.create_token(self, resp.json)
                
            #     code_id = mp_token_obj.create({
            #         'mp_id': self.id,
            #         'code': code,
            #         'shop_id': shop_id,
            #         'access_token': r.json().get('access_token'),
            #         'refresh_token': r.json().get('refresh_token'),
            #         'expires_in': r.json().get('expire_in')
            #     })
            #     if last_code_id:
            #         last_code_id.unlink()
            # else:
            #     code_id = False
            
            # return code_id

    
