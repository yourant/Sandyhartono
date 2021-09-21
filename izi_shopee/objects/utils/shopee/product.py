# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from .api import ShopeeAPI


class ShopeeProduct(ShopeeAPI):

    def __init__(self, sp_account, **kwargs):
        super(ShopeeProduct, self).__init__(sp_account, **kwargs)
        self.product_data = []

    def get_product_info(self, pd_data):
        item_id_list = []
        for data in pd_data:
            item_id_list.append(data['item_id'])
        params = {
            'item_id_list': item_id_list
        }
        prepared_request = self.build_request('product_info',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.access_token,
                                              ** {
                                                  'params': params
                                              })
        sp_data = self.process_response('product_info', self.request(**prepared_request))
        return sp_data['item_list']

    def get_product_list(self, limit=0, per_page=50):
        params = {}
        unlimited = not limit
        if unlimited:
            offset = 1
            while unlimited:
                params.update({
                    'offset': offset,
                    'page_size': per_page,
                    'item_status': 'NORMAL'
                })
                prepared_request = self.build_request('product_list',
                                                      self.sp_account.partner_id,
                                                      self.sp_account.partner_key,
                                                      self.sp_account.shop_id,
                                                      self.sp_account.access_token,
                                                      ** {
                                                          'params': params
                                                      })
                sp_data = self.process_response('product_list', self.request(**prepared_request))
                if sp_data:
                    sp_product = self.get_product_info(sp_data['item'])
                    self.product_data.extend(sp_product)
                    offset += per_page
                    if not sp_data['has_next_page']:
                        unlimited = False
                else:
                    unlimited = False
        else:
            pagination_pages = self.pagination_get_pages(limit=limit, per_page=per_page)
            for pagination_page in pagination_pages:
                params.update({
                    'offset': pagination_page[0],
                    'page_size': pagination_page[1],
                    'item_status ': 'NORMAL'
                })
                prepared_request = self.build_request('product_list',
                                                      self.sp_account.partner_id,
                                                      self.sp_account.partner_key,
                                                      self.sp_account.shop_id,
                                                      self.sp_account.access_token,
                                                      ** {
                                                          'params': params
                                                      })
                sp_data = self.process_response('product_list', self.request(**prepared_request))
                if sp_data:
                    self.product_data.extend(sp_data)

        return self.product_data
