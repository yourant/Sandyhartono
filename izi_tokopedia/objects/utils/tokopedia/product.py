# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from .api import TokopediaAPI


class TokopediaProduct(TokopediaAPI):

    def __init__(self, tp_account, **kwargs):
        super(TokopediaProduct, self).__init__(tp_account, **kwargs)

    def get_product_info(self, *args, **kwargs):
        return getattr(self, '%s_get_product_info' % self.api_version)(*args, **kwargs)

    def v1_get_product_info(self, shop_id=None, product_id=None, limit=0, per_page=50):
        product_data, product_data_raw = [], []
        params = {}

        if shop_id:
            params.update({
                'shop_id': shop_id
            })

        if product_id:
            limit = 1
            if isinstance(product_id, list):
                product_id = ','.join([str(pid) for pid in product_id])
            params.update({
                'product_id': product_id
            })

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
                raw_data, tp_data = self.process_response('product_info', self.request(**prepared_request))
                if raw_data:
                    product_data.extend(tp_data)
                    product_data_raw.extend(raw_data)
                    self._logger.info("Product: Imported %d record(s) of unlimited." % len(product_data))
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
                raw_data, tp_data = self.process_response('product_info', self.request(**prepared_request))
                if raw_data:
                    product_data.extend(tp_data)
                    product_data_raw.extend(raw_data)
                    if limit == 1:
                        self._logger.info("Product: Imported 1 record.")
                    else:
                        self._logger.info("Product: Imported %d record(s) of %d." % (len(product_data), limit))

        self._logger.info("Product: Finished %d record(s) imported." % len(product_data))
        return product_data_raw, product_data
