# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import requests

from .api import ShopeeAPI
from .tools import process_response


class ShopeeLogistic(ShopeeAPI):

    def get_logsitic_list(self):
        prepared_request = self.endpoints.build_request('logistic_list',
                                                        self.sp_account.partner_id,
                                                        self.sp_account.partner_key,
                                                        self.sp_account.shop_id,
                                                        self.sp_account.access_token)
        return process_response(requests.request(**prepared_request))
