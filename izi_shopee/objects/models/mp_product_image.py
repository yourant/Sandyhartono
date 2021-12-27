# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models


class MPProductImage(models.Model):
    _inherit = 'mp.product.image'

    sp_image_id = fields.Char(string='Shopee Product Image External ID')


    @api.model
    def shopee_get_sanitizers(self, mp_field_mapping):
        default_sanitizer = self.get_default_sanitizer(mp_field_mapping, root_path='response')
        return {
            'product_info': default_sanitizer
        }
