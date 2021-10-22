# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import time

from requests import PreparedRequest

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
                    prepared_request = self.build_request('order_list', params=params)
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
                    prepared_request = self.build_request('order_list', params=params)
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

        prepared_request = self.build_request('order_detail', params=params)
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

    def action_accept_order(self, *args, **kwargs):
        return getattr(self, '%s_action_accept_order' % self.api_version)(*args, **kwargs)

    def v1_action_accept_order(self, order_id):
        self.endpoints.tp_account.order_id = order_id
        prepared_request = self.build_request('order_accept', params={}, force_params=True)
        response = self.request(**prepared_request)
        response_data = self.process_response('default', response)
        return response_data

    def action_reject_order(self, *args, **kwargs):
        return getattr(self, '%s_action_reject_order' % self.api_version)(*args, **kwargs)

    def v1_action_reject_order(self, order_id, reason_code, reason, **kwargs):
        self.endpoints.tp_account.order_id = order_id

        reason_code = int(reason_code)
        data = {
            'reason_code': reason_code,
            'reason': reason
        }

        if reason_code == 4:
            if not kwargs.get('shop_close_end_date') or not kwargs.get('shop_close_note'):
                raise TypeError("shop_close_end_date and shop_close_not is mandatory!")

            data.update({
                'shop_close_end_date': kwargs.get('shop_close_end_date'),
                'shop_close_note': kwargs.get('shop_close_note')
            })

        prepared_request = self.build_request('order_reject', json=data, params={}, force_params=True)
        response = self.request(**prepared_request)
        response_data = self.process_response('default', response)
        return response_data

    def action_get_shipping_label(self, *args, **kwargs):
        return getattr(self, '%s_action_get_shipping_label' % self.api_version)(*args, **kwargs)

    def v1_action_get_shipping_label(self, order_id, printed=0):
        self.endpoints.tp_account.order_id = order_id

        params = {'printed': printed}

        prepared_request = self.build_request('order_shipping_label', params=params)
        response = self.request(**prepared_request)
        response_data = self.process_response('default', response, no_sanitize=True)
        return response_data

    def action_print_shipping_label(self, *args, **kwargs):
        return getattr(self, '%s_action_print_shipping_label' % self.api_version)(*args, **kwargs)

    def url_action_print_shipping_label(self, order_ids, printed=0):
        if not isinstance(order_ids, list):
            raise TypeError("order_ids should be in list format!")

        if not order_ids:
            raise TypeError("order_ids can not be empty!")

        params = {
            'order_id': ','.join(order_ids),
            'mark_as_printed': printed
        }

        url = self.endpoints.get_url('order_shipping_label')
        prepared_request_obj = PreparedRequest()
        prepared_request_obj.prepare_url(url, params)
        return prepared_request_obj.url

    def action_get_booking_code(self, *args, **kwargs):
        return getattr(self, '%s_action_get_booking_code' % self.api_version)(*args, **kwargs)

    def v1_action_get_booking_code(self, order_id=None):
        params = {}

        if order_id:
            params.update({'order_id': order_id})

        prepared_request = self.build_request('fulfillment_order', params=params)
        response = self.request(**prepared_request)
        response_data = self.process_response('booking_code', response)
        return response_data
