# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models
from odoo.exceptions import ValidationError


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
    is_open = fields.Boolean(string="Is Open?", readonly=True, mp_raw=True, mp_raw_handler=lambda env, r: bool(r))
    status = fields.Integer(string="Status", readonly=True, mp_raw=True)
    date_shop_created = fields.Date(string="Date Shop Created", readonly=True, mp_raw=True)
    domain = fields.Char(string="Domain", readonly=True, mp_raw=True)

    @api.model
    def tokopedia_get_sanitizers(self, mp_field_mapping):
        default_sanitizer = self.get_default_sanitizer(mp_field_mapping, root_path='data')
        return {
            'shop_info': default_sanitizer
        }

    @api.model
    def _finish_create_records(self, records):
        mp_account_obj = self.env['mp.account']

        context = self._context
        if not context.get('mp_account_id'):
            raise ValidationError("Please define mp_account_id in context!")

        mp_account = mp_account_obj.browse(context.get('mp_account_id'))

        records = super(MPTokopediaShop, self)._finish_create_records(records)
        mp_account.write({'tp_shop_id': records[0].id})
        return records
