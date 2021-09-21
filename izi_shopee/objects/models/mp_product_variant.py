# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models


class MPProductVariant(models.Model):
    _inherit = 'mp.product.variant'

    sp_variant_id = fields.Char(string='Product Variant External ID')

    @classmethod
    def _build_model_attributes(cls, pool):
        cls._rec_mp_external_id = dict(cls._rec_mp_external_id, **{
            'shopee': 'sp_variant_id'
        })
        super(MPProductVariant, cls)._build_model_attributes(pool)
