# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from .api import TokopediaAPI


class TokopediaShop(TokopediaAPI):

    def get_shop_info(self, shop_id=None):
        params = {}
        if shop_id:
            params.update({'shop_id': shop_id})

        prepared_request = self.build_request('shop_info', **{
            'params': params
        })
        return self.process_response('shop_info', self.request(**prepared_request))
