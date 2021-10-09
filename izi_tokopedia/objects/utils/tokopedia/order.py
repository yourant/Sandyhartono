# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import time

from .api import TokopediaAPI


class TokopediaOrder(TokopediaAPI):

    def __init__(self, tp_account, **kwargs):
        super(TokopediaOrder, self).__init__(tp_account, **kwargs)

    def get_order_list(self, *args, **kwargs):
        return getattr(self, '%s_get_order_list' % self.api_version)(*args, **kwargs)

    def v2_get_order_list(self, from_date, to_date, shop_id=None, limit=0, per_page=50):
        response_datas = []
        params = {
            'fs_id': self.tp_account.fs_id,
        }

        if shop_id:
            params.update({'shop_id': shop_id})

        date_ranges = self.pagination_date_range(from_date, to_date)
        for date_range in date_ranges:
            from_timestamp = self.to_api_timestamp(date_range[0])
            to_timestamp = self.to_api_timestamp(date_range[1])

            params.update({
                'from_date': from_timestamp,
                'to_date': to_timestamp
            })

            if limit > 0 and limit == len(response_datas):
                break

            unlimited = not limit
            if unlimited:
                page = 1
                while unlimited:
                    params.update({
                        'page': page,
                        'per_page': per_page
                    })
                    prepared_request = self.build_request('order_list', **{
                        'params': params
                    })
                    response = self.request(**prepared_request)
                    response_data = self.process_response('default', response)
                    if response_data:
                        response_datas.extend(response_data)
                        self._logger.info("Order: Imported %d record(s) of unlimited." % len(response_datas))
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
                    prepared_request = self.build_request('order_list', **{
                        'params': params
                    })
                    response = self.request(**prepared_request)
                    response_data = self.process_response('order_list', response)
                    if response_data:
                        response_datas.extend(response_data)
                        if limit == 1:
                            self._logger.info("Order: Imported 1 record.")
                        else:
                            self._logger.info("Order: Imported %d record(s) of %d." % (len(response_datas), limit))

        self._logger.info("Order: Finished %d record(s) imported." % len(response_datas))
        return response_datas

    def get_order_detail(self, *args, **kwargs):
        return getattr(self, '%s_get_order_detail' % self.api_version)(*args, **kwargs)

    def v2_get_order_detail(self, order_id=None, invoice_num=None, show_log=False):
        params = {}

        if not order_id and not invoice_num:
            raise ValueError("Required params is required, please input order_id or invoice_num!")

        if order_id:
            params.update({
                'order_id': order_id,
            })

        if invoice_num:
            params.update({
                'invoice_num': invoice_num,
            })

        prepared_request = self.build_request('order_detail', **{
            'params': params
        })
        response = self.request(**prepared_request)
        if show_log:
            self._logger.info(
                "Order: Getting order detail of %s... Please wait!" % response.json()['data']['invoice_number'])
        tp_limit_rate_reset = abs(float(response.headers.get('X-Ratelimit-Reset-After', 0)))
        if tp_limit_rate_reset > 0:
            self._logger.info(
                "Order: Too many requests, Tokopedia asking to waiting for %s second(s)" % str(tp_limit_rate_reset))
            time.sleep(tp_limit_rate_reset + 1)
        return self.process_response('order_detail', response)
