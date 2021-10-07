# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from .api import ShopeeAPI


class ShopeeProduct(ShopeeAPI):

    def __init__(self, sp_account, **kwargs):
        super(ShopeeProduct, self).__init__(sp_account, **kwargs)
        self.product_data = []
        self.product_data_raw = []

    def get_product_variant(self, item_id):
        params = {
            'item_id': item_id
        }
        prepared_request = self.build_request('product_variant_list',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.access_token,
                                              ** {
                                                  'params': params
                                              })
        sp_data_list = self.process_response('product_variant_list', self.request(**prepared_request))
        return sp_data_list

    def get_product_info(self, pd_data=None, product_id=None):
        item_id_list = []

        if pd_data:
            for data in pd_data:
                item_id_list.append(data['item_id'])
        elif product_id:
            item_id_list.append(product_id)

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
        temp_raw_data = raw_data['item_list']
        for index, data in enumerate(temp_raw_data):
            if data['has_model']:
                pd_variant_data = self.get_product_variant(data['item_id'])
                raw_data['item_list'][index].update({
                    'variants': pd_variant_data
                })
        return raw_data['item_list'], sp_data

    def get_product_list(self, limit=0, per_page=50):
        params = {}
        unlimited = not limit
        if unlimited:
            offset = 0
            while unlimited:
                params.update({
                    'offset': offset,
                    'page_size': per_page,
                    'item_status': ['NORMAL', 'UNLIST']
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
                    self._logger.info("Product: Imported %d of unlimited." % len(self.product_data))
                    if not sp_data_list['has_next_page']:
                        unlimited = False
                    else:
                        offset += len(sp_data_list['item'])
                else:
                    unlimited = False
        else:
            pagination_pages = self.pagination_get_pages(limit=limit, per_page=per_page)
            for pagination_page in pagination_pages:
                params.update({
                    'offset': pagination_page[0],
                    'page_size': pagination_page[1],
                    'item_status ': ['NORMAL', 'UNLIST']
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
                    self._logger.info("Product: Imported %d of %d." % (len(self.product_data), limit))

        self._logger.info("Product: Finished %d imported." % len(self.product_data))
        return self.product_data_raw, self.product_data
