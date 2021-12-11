# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import requests

from .api import ShopeeAPI


class ShopeeShop(ShopeeAPI):

    def get_profile_info(self, data):
        prepared_request = self.build_request('profile_info',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.access_token)

        sp_data_profile = self.process_response('profile_info', self.request(**prepared_request))
        data.update(sp_data_profile)
        return data

    def get_shop_info(self):
        prepared_request = self.build_request('shop_info',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.access_token)

        raw_data, sp_data_shop = self.process_response('shop_info', self.request(**prepared_request))
        raw_data.update({
            'shop_id': self.sp_account.shop_id
        })
        if sp_data_shop:
            raw_data = self.get_profile_info(raw_data)

        return raw_data
