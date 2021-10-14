# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from .api import ShopeeAPI


class ShopeeOrder(ShopeeAPI):

    def __init__(self, sp_account, **kwargs):
        super(ShopeeOrder, self).__init__(sp_account, **kwargs)
        self.order_data = []
        self.order_data_raw = []

    def get_order_list(self, *args, **kwargs):
        return getattr(self, '%s_get_order_list' % self.api_version)(*args, **kwargs)

    def get_order_detail(self, *args, **kwargs):
        return getattr(self, '%s_get_order_detail' % self.api_version)(*args, **kwargs)

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

    def v2_get_order_detail(self, **kwargs):
        response_field = ['item_list', 'recipient_address', 'note,shipping_carrier', 'pay_time',
                          'buyer_user_id', 'buyer_username', 'payment_method', 'package_list', 'actual_shipping_fee',
                          'estimated_shipping_fee', 'actual_shipping_fee_confirmed', 'total_amount']
        order_id_list = []
        if kwargs.get('sp_data', False):
            sp_data = kwargs.get('sp_data')
            for data in sp_data:
                order_id_list.append(data['order_sn'])
        elif kwargs.get('order_id', False):
            order_id_list.append(kwargs.get('order_id'))

        params = {
            'order_sn_list': ','.join(order_id_list),
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

        temp_raw_data = raw_data['order_list']
        for index, data in enumerate(temp_raw_data):
            if data['order_status'] == 'PROCESSED':
                shipping_info = getattr(self, '%s_get_shipping_doc_info' %
                                        self.api_version)(**{
                                            'order_sn': data['order_sn'],
                                            'package_number': data['package_list'][0]['package_number']
                                        })
                raw_data['order_list'][index].update(shipping_info)
            else:
                raw_data['order_list'][index].update({
                    'shipping_document_info': False
                })

        return raw_data['order_list']

    def v2_get_order_list(self, from_date, to_date, limit=0, per_page=50, time_range=None):
        date_ranges = self.pagination_date_range(from_date, to_date)

        for date_range in date_ranges:
            from_timestamp = self.to_api_timestamp(date_range[0])
            to_timestamp = self.to_api_timestamp(date_range[1])
            params = {
                'time_range_field': time_range,
                'time_from': from_timestamp,
                'time_to': to_timestamp
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
                        params = {
                            'sp_data': response_data['order_list']
                        }
                        raw_data = getattr(self, '%s_get_order_detail' %
                                           self.api_version)(**params)
                        # self.order_data.extend(sp_data)
                        self.order_data_raw.extend(raw_data)
                        self._logger.info("Order: Imported %d of unlimited." % len(self.order_data))
                        if not response_data['next_cursor']:
                            unlimited = False
                        else:
                            cursor = response_data['next_cursor']
                    else:
                        unlimited = False

        self._logger.info("Order: Finished %d record(s) imported." % len(self.order_data))
        # return self.order_data_raw, self.order_data
        return self.order_data_raw
