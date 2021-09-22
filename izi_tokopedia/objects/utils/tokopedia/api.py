# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import logging

import requests

from .tools import validate_response, sanitize_response, pagination_get_pages
from .endpoint import TokopediaEndpoint


class TokopediaAPI(object):

    def __init__(self, tp_account, api_version="v1", **kwargs):
        self.tp_account = tp_account
        self.api_version = api_version
        self.endpoints = TokopediaEndpoint(tp_account, api_version=api_version)
        self.build_request = self.endpoints.build_request
        self.request = requests.request
        self.validators = dict({
            'default': validate_response
        }, **kwargs.get('validators', {}))
        self.sanitizers = dict({
            'default': sanitize_response
        }, **kwargs.get('sanitizers', {}))
        self._logger = logging.getLogger(__name__)
        self.pagination_get_pages = pagination_get_pages

    def process_response(self, endpoint_key, response):
        validator = self.validators.get(endpoint_key, self.validators['default'])
        sanitizer = self.sanitizers.get(endpoint_key, self.sanitizers['default'])
        return sanitizer(validator(response))
