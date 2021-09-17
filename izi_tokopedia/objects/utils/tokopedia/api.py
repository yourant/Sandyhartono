# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

import requests

from .tools import validate_response, process_response, pagination_get_pages
from .endpoint import TokopediaEndpoint


class TokopediaAPI(object):

    def __init__(self, tp_account):
        self.tp_account = tp_account
        self.endpoints = TokopediaEndpoint(tp_account)
        self.build_request = self.endpoints.build_request
        self.request = requests.request
        self.validate_response = validate_response
        self.process_response = process_response
        self.pagination_get_pages = pagination_get_pages
