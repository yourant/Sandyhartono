# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models


class MPProductImage(models.Model):
    _inherit = 'mp.product.image'

    sp_image_id = fields.Char(string='Product Image External ID')

    @classmethod
    def _build_model_attributes(cls, pool):
        cls._rec_mp_external_id = dict(cls._rec_mp_external_id, **{
            'shopee': 'sp_image_id'
        })

        super(MPProductImage, cls)._build_model_attributes(pool)

    @api.model
    def shopee_get_sanitizers(self, mp_field_mapping):
        default_sanitizer = self.get_default_sanitizer(mp_field_mapping, root_path='response')
        return {
            'product_info': default_sanitizer
        }
