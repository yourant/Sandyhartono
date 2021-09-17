# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models


class MPTokopediaShop(models.Model):
    _name = 'mp.tokopedia.shop'
    _inherit = 'mp.base'
    _description = 'Marketplace Tokopedia Shop'
    _rec_name = 'shop_name'
    _rec_mp_external_id = 'shop_id'

    shop_id = fields.Integer(string="Shop ID", readonly=True, mp_raw=True)
    user_id = fields.Integer(string="User ID", readonly=True, mp_raw=True)
    shop_name = fields.Char(string="Shop Name", readonly=True, mp_raw=True)
    shop_url = fields.Char(string="Shop URL", readonly=True, mp_raw=True)
    is_open = fields.Boolean(string="Is Open?", readonly=True, mp_raw=True, mp_raw_handler=lambda r: bool(r))
    status = fields.Integer(string="Status", readonly=True, mp_raw=True)
    date_shop_created = fields.Date(string="Date Shop Created", readonly=True, mp_raw=True)
    domain = fields.Char(string="Domain", readonly=True, mp_raw=True)

    @api.model
    def create_shop(self, tp_data, multi=False):
        mp_tokopedia_shop_obj = self.env['mp.tokopedia.shop']

        if multi:
            tp_datas = tp_data
            mp_tokopedia_shops = mp_tokopedia_shop_obj

            for tp_data in tp_datas:
                mp_tokopedia_shops |= self.create_shop(tp_data)

            return mp_tokopedia_shops

        raw_data, values = self.mapping_raw_data(raw_data=tp_data)
        return mp_tokopedia_shop_obj.create(values)

