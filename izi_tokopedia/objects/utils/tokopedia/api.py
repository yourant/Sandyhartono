# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import logging
from datetime import datetime

import pytz
import requests

from .tools import validate_response, sanitize_response, pagination_get_pages, pagination_date_range
from .endpoint import TokopediaEndpoint


class TokopediaAPI(object):

    def __init__(self, tp_account, api_version="v1", **kwargs):
        self.tp_account = tp_account
        self.api_version = api_version
        self.api_tz = pytz.timezone('Asia/Jakarta')
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
        self.pagination_date_range = pagination_date_range

    def process_response(self, endpoint_key, response, **kwargs):
        validator = self.validators.get(endpoint_key, self.validators['default'])
        sanitizer = self.sanitizers.get(endpoint_key, self.sanitizers['default'])
        if kwargs.get('no_validate') and kwargs.get('no_sanitize'):
            return response
        elif kwargs.get('no_validate'):
            return sanitizer(response)
        elif kwargs.get('no_sanitize'):
            return validator(response)
        return sanitizer(validator(response))

    def from_api_timestamp(self, api_ts, as_tz='UTC'):
        as_tz = pytz.timezone(as_tz)
        api_dt = datetime.fromtimestamp(api_ts)
        return self.api_tz.localize(api_dt).astimezone(as_tz)

    def to_api_timestamp(self, dt, dt_tz='UTC'):
        dt_tz = pytz.timezone(dt_tz)
        api_dt = dt_tz.localize(dt).astimezone(self.api_tz)
        return int(api_dt.replace(tzinfo=pytz.utc).timestamp())
