# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from .api import ShopeeAPI


class ShopeeProduct(ShopeeAPI):

    def __init__(self, sp_account, **kwargs):
        super(ShopeeProduct, self).__init__(sp_account, **kwargs)
        self.product_data = []
        self.product_data_raw = []

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
        raw_data, sp_data = self.process_response('product_info', self.request(**prepared_request))
        return raw_data['item_list'], sp_data

    def get_product_list(self, limit=0, per_page=50):
        params = {}
        unlimited = not limit
        if unlimited:
            offset = 1
            while unlimited:
                params.update({
                    'offset': offset,
                    'page_size': per_page,
                    'item_status': ['NORMAL', 'BANNED', 'DELETED', 'UNLIST']
                })
                prepared_request = self.build_request('product_list',
                                                      self.sp_account.partner_id,
                                                      self.sp_account.partner_key,
                                                      self.sp_account.shop_id,
                                                      self.sp_account.access_token,
                                                      ** {
                                                          'params': params
                                                      })
                sp_data_list = self.process_response('product_list', self.request(**prepared_request))
                if sp_data_list:
                    raw_data, sp_data = self.get_product_info(sp_data_list['item'])
                    self.product_data.extend(sp_data)
                    self.product_data_raw.extend(raw_data)
                    self.logger.info("Product: Imported %d of unlimited." % len(self.product_data))
                    if not sp_data_list['has_next_page']:
                        unlimited = False
                    else:
                        offset = sp_data_list['next_offset']
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
                sp_data_list = self.process_response('product_list', self.request(**prepared_request))
                if sp_data_list:
                    raw_data, sp_data = self.get_product_info(sp_data_list['item'])
                    self.product_data.extend(sp_data)
                    self.product_data_raw.extend(raw_data)
                    self.logger.info("Product: Imported %d of %d." % (len(self.product_data), limit))

        self.logger.info("Product: Finished %d imported." % len(self.product_data))
        return self.product_data_raw, self.product_data
