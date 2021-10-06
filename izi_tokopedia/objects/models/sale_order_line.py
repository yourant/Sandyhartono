# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    tp_order_detail_id = fields.Char(string="Tokopedia Order Detail ID", required_if_marketplace="tokopedia")

    @classmethod
    def _add_rec_mp_field_mapping(cls, mp_field_mappings=None):
        if not mp_field_mappings:
            mp_field_mappings = []

        marketplace = 'tokopedia'
        mp_field_mapping = {
            'tp_order_detail_id': ('order_detail_id', lambda env, r: str(r)),
            'tp_product_id': ('product_id', lambda env, r: str(r)),
            'name': ('product_name', None),
            'price_unit': ('product_price', None),
            'tp_subtotal_price': ('subtotal_price', None),
            'tp_weight': ('weight', None),
            'tp_total_weight': ('total_weight', None),
            'product_uom_qty': ('quantity', None),
            'tp_quantity_deliver': ('quantity_deliver', None),
            'tp_quantity_reject': ('quantity_reject', None),
            'tp_insurance_price': ('insurance_price', None),
            'tp_normal_price': ('normal_price', None),
            'tp_sku': ('sku', None)
        }

        mp_field_mappings.append((marketplace, mp_field_mapping))
        super(SaleOrderLine, cls)._add_rec_mp_field_mapping(mp_field_mappings)