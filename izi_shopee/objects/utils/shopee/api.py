# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

import requests

from .tools import validate_response, process_response, pagination_get_pages
from .endpoint import ShopeeEndpoint


class ShopeeAPI(object):

    def __init__(self, sp_account):
        self.sp_account = sp_account
        self.endpoints = ShopeeEndpoint(sp_account)
        self.build_request = self.endpoints.build_request
        self.request = requests.request
        self.validate_response = validate_response
        self.process_response = process_response
        self.pagination_get_pages = pagination_get_pages
