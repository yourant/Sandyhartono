# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import requests

from .api import BlibliAPI


class BlibliLogistic(BlibliAPI):

    def get_logsitic_list(self):
        params = {
            'storeCode': self.bli_account.shop_code,
            'channelId': self.bli_account.shop_name,
            'username': self.bli_account.usermail,
            'storeId': str(self.bli_account.store_id)
        }
        prepared_request = self.endpoints.build_request('logistic', **{
            'params': params
        })
        return self.process_response('logistic', self.request(**prepared_request))
