# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import logging
import requests
import pytz
from datetime import datetime

from .tools import validate_response, sanitize_response, pagination_get_pages, pagination_date_range
from .endpoint import ShopeeEndpoint


class ShopeeAPI(object):

    def __init__(self, sp_account, api_version="v2", ** kwargs):
        self.sp_account = sp_account
        self.api_version = api_version
        self.api_tz = pytz.timezone('Asia/Jakarta')
        self.endpoints = ShopeeEndpoint(sp_account, api_version=api_version)
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

    def process_response(self, endpoint_key, response):
        validator = self.validators.get(endpoint_key, self.validators['default'])
        sanitizer = self.sanitizers.get(endpoint_key, self.sanitizers['default'])
        return sanitizer(validator(response))

    def from_api_timestamp(self, api_ts, as_tz='UTC'):
        as_tz = pytz.timezone(as_tz)
        api_dt = datetime.fromtimestamp(api_ts)
        return self.api_tz.localize(api_dt).astimezone(as_tz)

    def to_api_timestamp(self, dt, dt_tz='UTC'):
        dt_tz = pytz.timezone(dt_tz)
        api_dt = dt_tz.localize(dt).astimezone(self.api_tz)
        return int(api_dt.replace(tzinfo=None).timestamp())
