# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from .api import TokopediaAPI


class TokopediaProduct(TokopediaAPI):

    def __init__(self, tp_account, **kwargs):
        super(TokopediaProduct, self).__init__(tp_account, **kwargs)
        self.product_data = []

    def get_product_info(self, shop_id, limit=0, per_page=50):
        params = {
            'shop_id': shop_id
        }
        unlimited = not limit
        if unlimited:
            page = 1
            while unlimited:
                params.update({
                    'page': page,
                    'per_page': per_page
                })
                prepared_request = self.build_request('product_info', **{
                    'params': params
                })
                tp_data = self.process_response('product_info', self.request(**prepared_request))
                if tp_data:
                    self.product_data.extend(tp_data)
                    page += 1
                else:
                    unlimited = False
        else:
            pagination_pages = self.pagination_get_pages(limit=limit, per_page=per_page)
            for pagination_page in pagination_pages:
                params.update({
                    'page': pagination_page[0],
                    'per_page': pagination_page[1]
                })
                prepared_request = self.build_request('product_info', **{
                    'params': params
                })
                tp_data = self.process_response('product_info', self.request(**prepared_request))
                if tp_data:
                    self.product_data.extend(tp_data)

        return self.product_data
