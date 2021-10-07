# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from .api import BlibliAPI


class BlibliOrder(BlibliAPI):

    def __init__(self, bli_account, **kwargs):
        super(BlibliOrder, self).__init__(bli_account, **kwargs)
        self.order_data = []
        self.order_data_raw = []

    # def get_order_list(self, *args, **kwargs):
    #     return getattr(self, '%s_get_order_list' % self.api_version)(*args, **kwargs)

    def get_order_detail(self, bli_data=None, order_id=None):
        order_id_list = {}
        raw_data = []
        order_data = []
        for order in bli_data:
            if int(order['orderNo']) in order_id_list:
                pass
                order_id_list[int(order['orderNo'])].append(int(order['orderItemNo']))
            else:
                order_id_list[int(order['orderNo'])] = [int(order['orderItemNo'])]
        # elif order_id:
        #     order_id_list.append(order_id)
        for order in order_id_list.items():
            params = {
                'channelId': self.bli_account.shop_name,
                'storeId': str(self.bli_account.store_id),
                'orderItemNo': order[1][0],
                'orderNo': order[0]
            }
            prepared_request = self.endpoints.build_request('order_detail', **{
                'params': params
            })
            raw_data_temp, order_data_temp = self.process_response('order_detail', self.request(**prepared_request))
            if order_data_temp in order_data:
                pass
            else:
                order_data.append(order_data_temp)
            raw_data.append(raw_data_temp)
        return raw_data, order_data

    def get_order_list(self, from_date, to_date, shop_id=None, limit=0, per_page=50):
        date_ranges = self.pagination_date_range(from_date, to_date)

        for date_range in date_ranges:
            from_timestamp = date_range[0].strftime("%Y-%m-%d %H:%M:%S")
            to_timestamp = date_range[1].strftime("%Y-%m-%d %H:%M:%S")

            params = {
                'channelId': self.bli_account.shop_name,
                'businessPartnerCode': self.bli_account.shop_code,
                'storeId': str(self.bli_account.store_id),
                'filterStartDate': from_timestamp,
                'filterEndDate': to_timestamp,
                'size': per_page
            }
            prepared_request = self.endpoints.build_request('logistic', **{
                'params': params
            })

            unlimited = not limit
            if unlimited:
                page = 0
                while unlimited:
                    params.update({
                        'page': page
                    })
                    prepared_request = self.endpoints.build_request('order_list', **{
                        'params': params
                    })
                    response_data = self.process_response('order_list', self.request(**prepared_request))
                    if response_data['content']:
                        # raw_data, bli_data = getattr(self, '%s_get_order_detail' %
                        #                             self.api_version)(response_data['order_list'])
                        raw_data, bli_data = self.get_order_detail(response_data['content'])
                        self.order_data.extend(bli_data)
                        self.order_data_raw.extend(raw_data)
                        self._logger.info("Order: Imported %d of unlimited." % len(self.order_data))
                        page = page+1
                    else:
                        unlimited = False

        self._logger.info("Order: Finished %d record(s) imported." % len(self.order_data))
        return self.order_data_raw, self.order_data
