# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import requests

from .api import TokopediaAPI
from .tools import process_response


class TokopediaShop(TokopediaAPI):

    def get_shop_info(self, shop_id=None):
        params = {}
        if shop_id:
            params.update({'shop_id': shop_id})

        prepared_request = self.endpoints.build_request('shop_info', **{
            'params': params
        })
        return process_response(requests.request(**prepared_request))


