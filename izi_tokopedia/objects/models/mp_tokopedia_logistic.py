# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models


class MPTokopediaLogistic(models.Model):
    _name = 'mp.tokopedia.logistic'
    _inherit = 'mp.base'
    _rec_name = 'shipper_name'
    _rec_mp_external_id = 'shipper_id'

    shop_id = fields.Many2one(comodel_name="mp.tokopedia.shop", string="Shop", required=True)
    shipper_id = fields.Char(string="Shipper ID", readonly=True)
    shipper_name = fields.Char(string="Shipper Name", readonly=True)
    logo = fields.Char(string="Logo", readonly=True)

    @classmethod
    def _add_rec_mp_field_mapping(cls, marketplace=None, mp_field_mapping=None):
        marketplace = 'tokopedia'

        mp_field_mapping = {
            'shipper_id': ('shipper_id', lambda env, r: str(r)),
            'shipper_name': ('shipper_name', None),
            'logo': ('logo', None)
        }
        super(MPTokopediaLogistic, cls)._add_rec_mp_field_mapping(marketplace, mp_field_mapping)

    @api.model
    def tokopedia_get_sanitizers(self, mp_field_mapping):
        default_sanitizer = self.get_default_sanitizer(mp_field_mapping, root_path='data')
        return {
            'logistic_info': default_sanitizer
        }

    @api.model
    def _finish_mapping_raw_data(self, sanitized_data, values):
        sanitized_data, values = super(MPTokopediaLogistic, self)._finish_mapping_raw_data(sanitized_data, values)
        mp_account = self.get_mp_account_from_context()
        values.update({
            'shop_id': mp_account.tp_shop_id.id
        })
        return sanitized_data, values
