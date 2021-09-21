# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models


class MarketplaceProduct(models.Model):
    _inherit = 'mp.product'

    sp_product_id = fields.Char(string="Shopee Product ID", readonly=True)
    sp_item_status = fields.Char(string="Shopee Item Status", readonly=True)

    @classmethod
    def _build_model_attributes(cls, pool):

        def _handle_price_info(data):
            if data:
                return data[0].get('original_price')
            else:
                return None

        cls._rec_mp_external_id = dict(cls._rec_mp_external_id, **{
                'shopee': 'sp_product_id'
        })

        cls._rec_mp_field_mapping = dict(cls._rec_mp_field_mapping, **{
            'shopee': {
                'name': ('item_list/item_name', None),
                'description_sale': ('item_list/description', None),
                'default_code': ('item_list/item_sku', lambda r: r if r else False),
                'list_price': ('item_list/price_info', _handle_price_info),
                'weight': ('item_list/weight', lambda r: float(r)),
                'length': ('item_list/dimension/package_length', lambda r: float(r)),
                'width': ('item_list/dimension/package_width', lambda r: float(r)),
                'height': ('item_list/dimension/package_height', lambda r: float(r)),
                'sp_product_id': ('item_list/item_id', None),
                'sp_item_status': ('item_list/item_status', None)
            }
        })
        super(MarketplaceProduct, cls)._build_model_attributes(pool)

    @api.model
    def shopee_get_sanitizers(self, mp_field_mapping):
        default_sanitizer = self.get_default_sanitizer(mp_field_mapping, root_path='response')
        return {
            'product_info': default_sanitizer
        }
