# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import requests
from base64 import b64encode

from .endpoint import ENDPOINTS


class TokopediaAccount(object):

    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret

    def get_auth(self):
        auth = b64encode('{}:{}'.format(self.client_id, self.client_secret).encode()).decode()
        return 'Basic %s' % auth

    def authenticate(self):
        headers = {
            'Authorization': self.get_auth(),
            'Content-Length': '0',
            'User-Agent': 'PostmanRuntime/7.17.1'
        }
        resp = requests.post(ENDPOINTS.get('auth'), headers=headers)
        return resp.json()
