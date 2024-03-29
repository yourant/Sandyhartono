# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import time
from datetime import datetime, timedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.izi_marketplace.objects.utils.tools import mp
from odoo.addons.izi_shopee.objects.utils.shopee.order import ShopeeOrder


class WizardShopeeOrderPickup(models.TransientModel):
    _name = 'wiz.sp_order_pickup'
    _description = 'Shopee Order Pickup Wizard'

    order_ids = fields.Many2many(comodel_name="sale.order", relation="rel_sp_order_pickup_sale_order",
                                 column1="order_pickup_id", column2="order_id", string="Order(s)", required=True)
    pickup_id = fields.Many2one(comodel_name='mp.shopee.order.pickup.info', string='Pickup Time')
    address_id = fields.Many2one(comodel_name='mp.shopee.shop.address', string='Pickup Address')

    @ mp.shopee.capture_error
    def confirm(self):
        date_dict = {
            'Monday': 'Senin',
            'Tuesday': 'Selasa',
            'Wednesday': 'Rabu',
            'Thursday': 'Kamis',
            'Friday': 'Jum\'at',
            'Saturday': 'Sabtu',
            'Sunday': 'Minggu'
        }
        for order in self.order_ids:
            if order.mp_account_id.mp_token_id.state == 'valid':
                params = {'access_token': order.mp_account_id.mp_token_id.name}
                sp_account = order.mp_account_id.shopee_get_account(**params)
                sp_order = ShopeeOrder(sp_account)

                kwargs = {
                    'order_sn': order.mp_external_id,
                    'pickup': {
                        "tracking_no": "",
                        "address_id": int(self.address_id.mp_external_id),
                        "pickup_time_id": self.pickup_id.mp_external_id
                    }
                }
                mp_shopee_order_pickup_info_obj = self.env['mp.shopee.order.pickup.info']
                pickup_ids = mp_shopee_order_pickup_info_obj.search(
                    [('order_id', '=', order.id), ('id', '!=', self.pickup_id.id)])
                for pickup in pickup_ids:
                    pickup.active = False
                action_status = sp_order.action_ship_order(**kwargs)
                if action_status == "success":
                    day = date_dict[self.pickup_id.start_datetime.strftime('%A')]
                    start_datetime = self.pickup_id.start_datetime.strftime('%d-%m-%y, %H:%M')
                    end_datetime = self.pickup_id.end_datetime.strftime(
                        '%H:%M') if self.pickup_id.end_datetime else False
                    if start_datetime and end_datetime:
                        str_time = start_datetime + '-' + end_datetime
                    elif start_datetime and not end_datetime:
                        start_datetime = self.pickup_id.start_datetime + timedelta(hours=7)
                        str_time = start_datetime.strftime('%d-%m-%y, %H:%M')

                    date_time = day+', ' + str_time
                    order.sp_pickup_date = date_time
                    if order.state == 'draft':
                        order.action_confirm()
                    time.sleep(1)
                    order.shopee_fetch_order()
