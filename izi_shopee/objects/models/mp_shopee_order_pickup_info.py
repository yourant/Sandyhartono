# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
from datetime import datetime, timedelta
from odoo import api, fields, models
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT


class MPShopeeOrderPickupInfo(models.Model):
    _name = 'mp.shopee.order.pickup.info'
    _inherit = 'mp.base'
    _description = 'Marketplace Shopee Order Pickup Information'
    _rec_mp_external_id = 'pickup_time_id'

    pickup_time_id = fields.Char(string='Pickup Time ID')
    start_datetime = fields.Datetime(string='Start Datetime')
    end_datetime = fields.Datetime(string='End Datetime')
    order_id = fields.Many2one(comodel_name='sale.order', string='Shopee Order')
    address_id = fields.Many2one(comodel_name='mp.shopee.shop.address', string='Shop Address')
    active = fields.Boolean(string='Active', default=True)

    @api.multi
    def name_get(self):
        res = []
        date_dict = {
            'Monday': 'Senin',
            'Tuesday': 'Selasa',
            'Wednesday': 'Rabu',
            'Thursday': 'Kamis',
            'Friday': 'Jum\'at',
            'Saturday': 'Sabtu',
            'Sunday': 'Minggu'
        }
        for rec in self:
            day = date_dict[datetime.strptime(rec.start_datetime, '%Y-%m-%d %H:%M:%S').strftime('%A')]
            if rec.end_datetime:
                time = datetime.strptime(rec.start_datetime, '%Y-%m-%d %H:%M:%S').strftime('%d-%m-%y, %H:%M') + \
                    '-' + datetime.strptime(rec.end_datetime, '%Y-%m-%d %H:%M:%S').strftime('%H:%M')
            else:
                start_time_obj = datetime.strptime(rec.start_datetime, '%Y-%m-%d %H:%M:%S') + timedelta(hours=7)
                time = start_time_obj.strftime('%d-%m-%y, %H:%M')
            date_time = day+', '+time

            res.append((rec.id, date_time))
        return res

    @classmethod
    def _add_rec_mp_field_mapping(cls, mp_field_mappings=None):
        if not mp_field_mappings:
            mp_field_mappings = []

        marketplace = 'shopee'
        mp_field_mapping = {
            'pickup_time_id': ('pickup_time_id', None),
            'order_id': ('order_id', None),
            'address_id': ('address_id', None),
        }

        def handle_start_time(env, data):
            time_text = data['time_text']
            date = datetime.strptime(data['date_from_timestamp'], DEFAULT_SERVER_DATETIME_FORMAT)
            start_datetime = None
            if time_text == 'Now':
                start_datetime = datetime.now()
            else:
                start_time = time_text.split('-')[0]
                if 'am' in start_time or 'pm' in start_time:
                    if 'am' in start_time:
                        start_time = start_time.replace('am', ' AM')
                    elif 'pm' in start_time:
                        start_time = start_time.replace('pm', ' PM')
                    start_time_obj = datetime.strptime(start_time, '%I:%M %p')
                    start_hour = start_time_obj.hour
                    start_minute = start_time_obj.minute
                    start_second = start_time_obj.second
                else:
                    start_hour = int(start_time.split(':')[0])
                    start_minute = int(start_time.split(':')[1])
                    start_second = int(start_time.split(':')[2]) if len(start_time.split(':')) > 2 else 0

                start_datetime = date.replace(hour=start_hour, minute=start_minute, second=start_second)
            return start_datetime

        def handle_end_time(env, data):
            time_text = data['time_text']
            date = datetime.strptime(data['date_from_timestamp'], DEFAULT_SERVER_DATETIME_FORMAT)
            end_datetime = None
            if time_text != 'Now':
                end_time = time_text.split('-')[1]
                if 'am' in end_time or 'pm' in end_time:
                    if 'am' in end_time:
                        end_time = end_time.replace('am', ' AM')
                    elif 'pm' in end_time:
                        end_time = end_time.replace('pm', ' PM')
                    end_time_obj = datetime.strptime(end_time, '%I:%M %p')
                    end_hour = end_time_obj.hour
                    end_minute = end_time_obj.minute
                    end_second = end_time_obj.second
                else:
                    end_hour = int(end_time.split(':')[0])
                    end_minute = int(end_time.split(':')[1])
                    end_second = int(end_time.split(':')[2]) if len(end_time.split(':')) > 2 else 0

                end_datetime = date.replace(hour=end_hour, minute=end_minute, second=end_second)

            return end_datetime

        mp_field_mapping.update({
            'start_datetime': ('time_info', handle_start_time),
            'end_datetime': ('time_info', handle_end_time),
        })

        mp_field_mappings.append((marketplace, mp_field_mapping))
        super(MPShopeeOrderPickupInfo, cls)._add_rec_mp_field_mapping(mp_field_mappings)
