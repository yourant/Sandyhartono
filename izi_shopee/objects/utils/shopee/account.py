# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import requests
import hashlib
import hmac
import time
import urllib
import logging
import json

from .tools import validate_response
from .endpoint import ShopeeEndpoint

_logger = logging.getLogger(__name__)


class ShopeeAccount(object):

    def __init__(self, partner_id, partner_key, api_version="v2", ** kwargs):
        self.partner_id = partner_id
        self.partner_key = partner_key
        self.base_url = kwargs.get('base_url', None)
        self.mp_id = kwargs.get('mp_id', None)
        self.shop_id = kwargs.get('shop_id', None)
        self.code = kwargs.get('code', None)
        self.refresh_token = kwargs.get('refresh_token', None)
        self.access_token = kwargs.get('access_token', None)
        self.api_version = api_version
        self.endpoints = ShopeeEndpoint(self, host="base", api_version=api_version)

    def get_redirect_url(self):
        return '%s/api/user/auth/shopee/%s' % (self.base_url, self.mp_id)

    def get_auth_url_v2(self):
        timeest = int(time.time())
        base_string = '%s%s%s' % (self.partner_id, ShopeeEndpoint.ENDPOINTS.get(
            self.api_version).get('auth')[1], timeest)
        sign = hmac.new(self.partner_key.encode(), base_string.encode(), hashlib.sha256).hexdigest()
        return '%(host)s%(path)s?partner_id=%(partner_id)s&redirect=%(redirect)s&timestamp=%(timestamp)s&sign=%(sign)s' % {
            'host': ShopeeEndpoint.HOSTS.get('base'),
            'path': ShopeeEndpoint.ENDPOINTS.get(self.api_version).get('auth')[1],
            'partner_id': self.partner_id,
            'redirect': urllib.parse.quote(self.get_redirect_url()),
            'timestamp': timeest,
            'sign': sign
        }

    def get_token(self):
        if self.shop_id:
            headers = {
                'Content-Type': 'application/json',
            }
            payload = {
                'shop_id': int(self.shop_id),
                'partner_id': int(self.partner_id)
            }
            if self.refresh_token:
                payload.update({'refresh_token': self.refresh_token})
            else:
                payload.update({'code': self.code})
            prepared_request = self.endpoints.v2_build_request('token_renew' if self.refresh_token else 'token_get',
                                                               self.partner_id, self.partner_key, self.shop_id,
                                                               **{
                                                                   'headers': headers,
                                                                   'json': payload
                                                               })
            response = validate_response(requests.request(**prepared_request))
            _logger.info('\n%s' % (json.dumps(response.json(), indent=2)))
            return response.json(), prepared_request.get('json')
