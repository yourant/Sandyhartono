# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
from .api import ShopeeAPI


class ShopeeOrder(ShopeeAPI):

    def __init__(self, sp_account, **kwargs):
        super(ShopeeOrder, self).__init__(sp_account, **kwargs)
        self.order_data = []
        self.order_data_raw = []

    def get_income(self, *args, **kwargs):
        return getattr(self, '%s_get_income' % self.api_version)(*args, **kwargs)

    def v1_get_income(self, **kwargs):
        body = {
            'ordersn': kwargs.get('order_sn'),
        }
        prepared_request = self.build_request('get_my_income',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              ** {
                                                  'json': body
                                              })
        response = self.process_response('get_my_income', self.request(**prepared_request), no_sanitize=True)
        return response.json()

    def get_airways_bill(self, **kwargs):
        return getattr(self, '%s_get_awb' % self.api_version)(**kwargs)

    def v1_get_awb(self, **kwargs):
        body = {
            'ordersn_list': [kwargs.get('order_sn')],
        }
        prepared_request = self.build_request('get_awb_url',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              ** {
                                                  'json': body
                                              })
        response = self.process_response('get_awb_url', self.request(**prepared_request), no_sanitize=True)
        raw_data = response.json()
        awb_dict = {}
        if raw_data.get('result', False):
            for data in raw_data['result']['airway_bills']:
                awb_dict[data['ordersn']] = data['airway_bill']
        return awb_dict

    def get_shipping_parameter(self, **kwargs):
        return getattr(self, '%s_get_shipping_parameter' %
                       self.api_version)(**{
                           'order_sn': kwargs.get('order_sn'),
                       })

    def v2_get_shipping_parameter(self, **kwargs):
        params = {
            'order_sn': kwargs.get('order_sn'),
        }
        prepared_request = self.build_request('shipping_parameter',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.access_token,
                                              ** {
                                                  'params': params
                                              })
        raw_data = self.process_response('shipping_parameter', self.request(**prepared_request))
        return raw_data

    def get_shipping_doc_info(self, **kwargs):
        return getattr(self, '%s_get_shipping_doc_info' %
                       self.api_version)(**{
                           'order_sn': kwargs.get('order_sn'),
                           'package_number': kwargs.get('package_number')
                       })

    def v2_get_shipping_doc_info(self, **kwargs):
        params = {
            'order_sn': kwargs.get('order_sn'),
            'package_number': kwargs.get('package_number')
        }
        prepared_request = self.build_request('shipping_doc_info',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.access_token,
                                              ** {
                                                  'params': params
                                              })
        raw_data = self.process_response('shipping_doc_info', self.request(**prepared_request))
        return raw_data

    def get_order_detail(self, **kwargs):
        return getattr(self, '%s_get_order_detail' % self.api_version)(**kwargs)

    def v2_get_order_detail(self, **kwargs):
        def req_order_detail(order_ids):
            params = {
                'order_sn_list': ','.join(order_ids),
                'response_optional_fields': ','.join(response_field)
            }
            prepared_request = self.build_request('order_detail',
                                                  self.sp_account.partner_id,
                                                  self.sp_account.partner_key,
                                                  self.sp_account.shop_id,
                                                  self.sp_account.access_token,
                                                  ** {
                                                      'params': params
                                                  })
            raw_data = self.process_response('order_detail', self.request(**prepared_request))
            return raw_data['order_list']

        response_field = ['item_list', 'recipient_address', 'note,shipping_carrier', 'pay_time',
                          'buyer_user_id', 'buyer_username', 'payment_method', 'package_list', 'actual_shipping_fee',
                          'estimated_shipping_fee', 'actual_shipping_fee_confirmed', 'total_amount',
                          'checkout_shipping_carrier']
        order_id_list = []
        raw_datas = {'order_list': []}
        per_page = 50
        count_order = 0
        if kwargs.get('sp_data', False):
            sp_data = kwargs.get('sp_data')
            order_list_split = [sp_data[x:x+per_page] for x in range(0, len(sp_data), per_page)]
            for datas in order_list_split:
                order_id_list = []
                for order in datas:
                    order_id_list.append(order['order_sn'])
                count_order += len(order_id_list)
                self._logger.info("Order: Get order detail %d of %d." % (count_order, len(sp_data)))
                raw_data = req_order_detail(order_id_list)
                raw_datas['order_list'].extend(raw_data)

        elif kwargs.get('order_id', False):
            order_id_list.append(kwargs.get('order_id'))
            self._logger.info("Order: Get order detail %d of %d." % (len(order_id_list), len(order_id_list)))
            raw_data = req_order_detail(order_id_list)
            raw_datas['order_list'].extend(raw_data)

        temp_raw_data = raw_datas['order_list']
        for index, data in enumerate(temp_raw_data):
            shipping_parameter = False
            shipping_info = False
            # get shipping type
            if data['order_status'] in ['READY_TO_SHIP', 'PROCESSED']:
                shipping_parameter = self.get_shipping_parameter(order_sn=data['order_sn'])

                # get shipping document info
                if data['order_status'] == 'PROCESSED':
                    shipping_info = self.get_shipping_doc_info(
                        order_sn=data['order_sn'], package_number=data['package_list'][0]['package_number'])
                    shipping_info = shipping_info['shipping_document_info']

            raw_datas['order_list'][index].update({
                'shipping_paramater': shipping_parameter,
                'shipping_document_info': shipping_info
            })

        self._logger.info("Order: Finished Get order detail %d record(s) imported." % len(raw_datas['order_list']))
        return raw_datas['order_list']

    def get_order_list(self, **kwargs):
        return getattr(self, '%s_get_order_list' % self.api_version)(**kwargs)

    def v2_get_order_list(self, from_date, to_date, limit=0, per_page=50, time_mode=None, **kwargs):
        date_ranges = self.pagination_date_range(from_date, to_date)
        for date_range in date_ranges:
            from_timestamp = self.to_api_timestamp(date_range[0])
            to_timestamp = self.to_api_timestamp(date_range[1])
            params = {
                'time_range_field': time_mode,
                'time_from': from_timestamp,
                'time_to': to_timestamp,
                'response_optional_fields': 'order_status'
            }
            unlimited = not limit
            if unlimited:
                cursor = ""
                while unlimited:
                    params.update({
                        'page_size': per_page,
                        'cursor': cursor
                    })
                    prepared_request = self.build_request('order_list',
                                                          self.sp_account.partner_id,
                                                          self.sp_account.partner_key,
                                                          self.sp_account.shop_id,
                                                          self.sp_account.access_token,
                                                          ** {
                                                              'params': params
                                                          })
                    response_data = self.process_response('order_list', self.request(**prepared_request))
                    if response_data['order_list']:
                        self.order_data_raw.extend(response_data['order_list'])
                        self._logger.info("Order: Get order list %d of unlimited." % len(response_data['order_list']))
                        if not response_data['next_cursor']:
                            unlimited = False
                        else:
                            cursor = response_data['next_cursor']
                    else:
                        unlimited = False

        self._logger.info("Order: Finished Get order List %d record(s) imported." % len(self.order_data_raw))
        # return self.order_data_raw, self.order_data
        return self.order_data_raw

    def action_ship_order(self, **kwargs):
        return getattr(self, '%s_ship_order' % self.api_version)(**kwargs)

    def v2_ship_order(self, **kwargs):
        payload = {
            'order_sn': kwargs.get('order_sn'),
            # 'package_number': kwargs.get('package_number'),
        }
        if kwargs.get('dropoff', False):
            payload.update({'dropoff': kwargs.get('dropoff')})
        elif kwargs.get('pickup', False):
            payload.update({'pickup': kwargs.get('pickup')})
        prepared_request = self.build_request('ship_order',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.access_token,
                                              ** {
                                                  'json': payload
                                              })
        response = self.process_response('ship_order', self.request(**prepared_request), no_sanitize=True)
        raw_data = response.json()
        if raw_data['error']:
            return 'failed'
        else:
            return 'success'

    def action_reject_order(self, **kwargs):
        return getattr(self, '%s_reject_order' % self.api_version)(**kwargs)

    def v2_reject_order(self, **kwargs):
        payload = {
            'order_sn': kwargs.get('order_exid'),
            'cancel_reason': kwargs.get('reason_code')
        }
        if kwargs.get('item_list', False):
            payload.update({'item_list': kwargs.get('item_list')})

        prepared_request = self.build_request('reject_order',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.access_token,
                                              ** {
                                                  'json': payload
                                              })
        response = self.process_response('reject_order', self.request(**prepared_request), no_sanitize=True)
        raw_data = response.json()
        return raw_data['message']

    def action_handle_buyer_cancel(self, **kwargs):
        return getattr(self, '%s_handle_buyer_cancel' % self.api_version)(**kwargs)

    def v2_handle_buyer_cancel(self, **kwargs):
        payload = {
            'order_sn': kwargs.get('order_sn'),
            'operation': kwargs.get('operation')
        }

        prepared_request = self.build_request('buyer_cancellation',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.access_token,
                                              ** {
                                                  'json': payload
                                              })
        response = self.process_response('buyer_cancellation', self.request(**prepared_request))
        if response.get('update_time', False):
            return "success"
        else:
            return "fail"

    def get_awb_number(self, **kwargs):
        return getattr(self, '%s_get_awb_number' %
                       self.api_version)(**{
                           'order_sn': kwargs.get('order_sn'),
                       })

    def v2_get_awb_number(self, **kwargs):
        params = {
            'order_sn': kwargs.get('order_sn'),
        }
        prepared_request = self.build_request('get_awb_num',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.access_token,
                                              ** {
                                                  'params': params
                                              })
        raw_data = self.process_response('get_awb_num', self.request(**prepared_request))
        return raw_data
