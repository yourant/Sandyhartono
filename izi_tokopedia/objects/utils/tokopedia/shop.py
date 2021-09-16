# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import requests

from .tools import process_response
from .endpoint import TokopediaEndpoint


class TokopediaShop(object):

    def __init__(self, tp_account):
        self.tp_account = tp_account
        self.endpoints = TokopediaEndpoint(tp_account)

    def get_shop_info(self, shop_id=None):
        params = {}
        if shop_id:
            params.update({'shop_id': shop_id})

        prepared_request = self.endpoints.build_request('shop_info', **{
            'params': params
        })
        return process_response(requests.request(**prepared_request))


