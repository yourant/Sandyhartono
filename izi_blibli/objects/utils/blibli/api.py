# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

import requests

from .tools import validate_response, sanitize_response, pagination_get_pages
from .endpoint import BlibliEndpoint


class BlibliAPI(object):

    def __init__(self, bli_account, **kwargs):
        self.bli_account = bli_account
        self.endpoints = BlibliEndpoint(bli_account)
        self.build_request = self.endpoints.build_request
        self.request = requests.request
        self.validators = dict({
            'default': validate_response
        }, **kwargs.get('validators', {}))
        self.sanitizers = dict({
            'default': sanitize_response
        }, **kwargs.get('sanitizers', {}))
        self.pagination_get_pages = pagination_get_pages

    def process_response(self, endpoint_key, response):
        validator = self.validators.get(endpoint_key, self.validators['default'])
        sanitizer = self.sanitizers.get(endpoint_key, self.sanitizers['default'])
        return sanitizer(validator(response))
