# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import requests
from base64 import b64encode

from .tools import validate_response
from .endpoint import TokopediaEndpoint


class TokopediaAccount(object):

    def __init__(self, client_id, client_secret, api_version="v1", **kwargs):
        self.client_id = client_id
        self.client_secret = client_secret
        self.fs_id = kwargs.get('fs_id', None)
        self.access_token = kwargs.get('access_token', None)
        self.expired_date = kwargs.get('expired_date', None)
        self.token_type = kwargs.get('token_type', None)
        self.api_version = api_version
        self.endpoints = TokopediaEndpoint(self, host="accounts", api_version=api_version)

    def get_auth(self, token=False):
        if token:
            auth = 'Basic %s' % b64encode('{}:{}'.format(self.client_id, self.client_secret).encode()).decode()
        else:
            auth = '%s %s' % (self.token_type, self.access_token)
        return auth

    def authenticate(self):
        headers = {
            'Authorization': self.get_auth(token=True),
        }
        prepared_request = self.endpoints.build_request('token', **{
            'headers': headers
        })
        response = validate_response(requests.request(**prepared_request))
        return response.json()
