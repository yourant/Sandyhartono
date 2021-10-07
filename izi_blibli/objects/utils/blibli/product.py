# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from .api import BlibliAPI


class BlibliProduct(BlibliAPI):

    def __init__(self, bli_account, **kwargs):
        super(BlibliProduct, self).__init__(bli_account, **kwargs)
        self.product_data = []
        self.product_data_raw = []

    def get_product_info(self, pd_data):
        raw_data = []
        bli_data = []
        for key, data in pd_data.items():
            params = {
                'businessPartnerCode': self.bli_account.shop_code,
                'channelId': self.bli_account.shop_name,
                'gdnSku': data[0]
            }
            prepared_request = self.build_request('product_info', ** {
                'params': params
            })
            raw_datas, bli_data_temp = self.process_response('product_info', self.request(**prepared_request))
            if len(data) > 1:
                raw_datas['bli_has_variant'] = True
                raw_datas['bli_variant_ids'] = data
                bli_data_temp['bli_has_variant'] = raw_datas['bli_has_variant']
                bli_data.append(bli_data_temp)
            else:
                raw_datas['bli_has_variant'] = False
                bli_data_temp['bli_has_variant'] = raw_datas['bli_has_variant']
                bli_data.append(bli_data_temp)
            raw_data.append(raw_datas)

        return raw_data, bli_data

    def get_product_list(self, limit=0, per_page=50):
        payload = {}
        params = {
            'businessPartnerCode': self.bli_account.shop_code,
            'channelId': self.bli_account.shop_name,
            'username': self.bli_account.usermail
        }
        unlimited = not limit
        if unlimited:
            page = 0
            offset = 0
            while unlimited:
                payload.update({
                    'page': page,
                    'size': per_page
                })
                prepared_request = self.build_request('product_list',  ** {
                    'params': params,
                    'json': payload
                })
                bli_data_list = self.process_response('product_list', self.request(**prepared_request))
                if bli_data_list:
                    bli_product_by_sku = {}
                    for product_bli in bli_data_list['content']:
                        if product_bli['productSku'] in bli_product_by_sku:
                            bli_product_by_sku[product_bli['productSku']].append(product_bli['gdnSku'])
                        else:
                            bli_product_by_sku[product_bli['productSku']] = [product_bli['gdnSku']]

                raw_data, bli_data = self.get_product_info(bli_product_by_sku)
                self.product_data.extend(bli_data)
                self.product_data_raw.extend(raw_data)
                self._logger.info("Product: Imported %d of unlimited." % len(self.product_data))
                offset += per_page
                if bli_data_list['pageMetaData']['totalRecords'] >= offset:
                    page += 1
                else:
                    unlimited = False
        else:
            pagination_pages = self.pagination_get_pages(limit=limit, per_page=per_page)
            for pagination_page in pagination_pages:
                payload.update({
                    'page': pagination_page[0],
                    'size': pagination_page[1]
                })
                prepared_request = self.build_request('product_list',
                                                      ** {
                                                          'params': params,
                                                          'json': payload
                                                      })
                bli_data_list = self.process_response('product_list', self.request(**prepared_request))
                if bli_data_list:
                    raw_data, bli_data = self.get_product_info(bli_data_list['item'])
                    self.product_data.extend(bli_data)
                    self.product_data_raw.extend(raw_data)
                    self._logger.info("Product: Imported %d of %d." % (len(self.product_data), limit))

        self._logger.info("Product: Finished %d imported." % len(self.product_data))
        return self.product_data_raw, self.product_data

    def get_product_variant(self, product_id):
        params = {
            'businessPartnerCode': self.bli_account.shop_code,
            'channelId': self.bli_account.shop_name,
            'gdnSku': product_id
        }
        prepared_request = self.build_request('product_info', ** {
            'params': params
        })
        raw_datas, bli_data = self.process_response('product_info', self.request(**prepared_request))
        raw_data = [raw_datas]
        return raw_data, bli_data
