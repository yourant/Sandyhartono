# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import requests

from .api import BlibliAPI


class BlibliShop(BlibliAPI):

    def get_shop_info(self):
        raw_data = {}
        raw_data['shop_id'] = self.bli_account.shop_code
        raw_data['shop_name'] = self.bli_account.shop_name

        return raw_data
