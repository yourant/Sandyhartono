# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from .api import ShopeeAPI


class ShopeeLogistic(ShopeeAPI):

    def get_logsitic_list(self):
        prepared_request = self.build_request('logistic_list',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.access_token)
        return self.process_response('logistic_list', self.request(**prepared_request))
