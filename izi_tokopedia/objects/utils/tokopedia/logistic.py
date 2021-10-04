# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from .api import TokopediaAPI


class TokopediaLogistic(TokopediaAPI):

    def get_logistic_active_info(self, *args, **kwargs):
        return getattr(self, '%s_get_logistic_active_info' % self.api_version)(*args, **kwargs)

    def get_logistic_info(self, *args, **kwargs):
        return getattr(self, '%s_get_logistic_info' % self.api_version)(*args, **kwargs)

    def v1_get_logistic_active_info(self, shop_id=None):
        params = {}
        if shop_id:
            params.update({'shop_id': shop_id})

        prepared_request = self.build_request('logistic_active_info', **{
            'params': params
        })
        return self.process_response('logistic_active_info', self.request(**prepared_request))

    def v2_get_logistic_info(self, shop_id=None):
        params = {}
        if shop_id:
            params.update({'shop_id': shop_id})

        prepared_request = self.build_request('logistic_info', **{
            'params': params
        })
        return self.process_response('logistic_info', self.request(**prepared_request))
