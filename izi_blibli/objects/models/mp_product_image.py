# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models


class MPProductImage(models.Model):
    _inherit = 'mp.product.image'

    bli_image_id = fields.Char(string='Blibli Product Image External ID')


    @api.model
    def blibli_get_sanitizers(self, mp_field_mapping):
        default_sanitizer = self.get_default_sanitizer(mp_field_mapping, root_path='value')
        return {
            'product_info': default_sanitizer
        }
