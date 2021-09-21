# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models


class MarketplaceProduct(models.Model):
    _inherit = 'mp.product'

    tp_product_id = fields.Char(string="Tokopedia Product ID", readonly=True)

    @classmethod
    def _build_model_attributes(cls, pool):
        cls._rec_mp_external_id = dict(cls._rec_mp_external_id, **{
            'tokopedia': 'tp_product_id'
        })

        cls._rec_mp_field_mapping = dict(cls._rec_mp_field_mapping, **{
            'tokopedia': {
                'tp_product_id': ('basic/productID', lambda env, r: str(r)),
                'name': ('basic/name', None),
                'description_sale': ('basic/shortDesc', None),
                'default_code': ('other/sku', lambda env, r: r if r else False),
                'list_price': ('price/value', None),
                'weight': ('weight/value', None),
                'length': ('volume/length', None),
                'width': ('volume/width', None),
                'height': ('volume/height', None),
            }
        })
        super(MarketplaceProduct, cls)._build_model_attributes(pool)

    @api.model
    def tokopedia_get_sanitizers(self, mp_field_mapping):
        default_sanitizer = self.get_default_sanitizer(mp_field_mapping, root_path='data')
        return {
            'product_info': default_sanitizer
        }
