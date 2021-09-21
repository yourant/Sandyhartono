# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models


class MarketplaceProduct(models.Model):
    _inherit = 'mp.product'

    sp_product_id = fields.Char(string="Shopee Product ID", readonly=True)
    sp_item_status = fields.Char(string="Shopee Item Status", readonly=True)

    @classmethod
    def _build_model_attributes(cls, pool):

        cls._rec_mp_external_id = dict(cls._rec_mp_external_id, **{
            'shopee': {
                'mp_external_id': 'sp_product_id'
            }
        })

        cls._rec_mp_field_mapping = dict(cls._rec_mp_field_mapping, **{
            'shopee': {
                'name': ('item_name', None),
                'description_sale': ('description', None),
                'default_code': ('item_sku', lambda r: r if r else False),
                'list_price': ('price_info/original_price', None),
                'weight': ('weight', lambda r: float(r)),
                'length': ('dimension/package_length', lambda r: float(r)),
                'width': ('dimension/package_width', lambda r: float(r)),
                'height': ('dimension/package_height', lambda r: float(r)),
                'sp_product_id': ('item_id', None),
                'sp_item_status': ('item_status', None)
            }
        })
        super(MarketplaceProduct, cls)._build_model_attributes(pool)

    @api.model
    def shopee_get_sanitizers(self, mp_field_mapping):
        default_sanitizer = self.get_default_sanitizer(mp_field_mapping, root_path='response')
        return {
            'product_detail': default_sanitizer
        }
