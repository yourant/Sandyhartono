# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    tp_order_detail_id = fields.Char(string="Tokopedia Order Detail ID", required_if_marketplace="tokopedia")

    @classmethod
    def _add_rec_mp_external_id(cls, mp_external_id_fields=None):
        if not mp_external_id_fields:
            mp_external_id_fields = []

        mp_external_id_fields.append(('tokopedia', 'tp_order_detail_id'))
        super(SaleOrderLine, cls)._add_rec_mp_external_id(mp_external_id_fields)

    @classmethod
    def _add_rec_mp_field_mapping(cls, mp_field_mappings=None):
        if not mp_field_mappings:
            mp_field_mappings = []

        marketplace = 'tokopedia'
        mp_field_mapping = {
            'order_id': ('order_id', None),
            'tp_order_detail_id': ('order_detail_id', lambda env, r: str(r)),
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

        def _handle_product_id(env, data):
            product_obj = env['product.product']
            mp_product_obj = env['mp.product']
            mp_product_variant_obj = env['mp.product.variant']

            product = product_obj
            mp_product = mp_product_obj.search_mp_records('tokopedia', data)
            mp_product_variant = mp_product_variant_obj.search_mp_records('tokopedia', data)

            if mp_product.exists():
                product = mp_product.get_product()
            if mp_product_variant.exists():
                product = mp_product_variant.get_product()

            return product.id

        mp_field_mapping.update({'product_id': ('product_id', _handle_product_id)})

        mp_field_mappings.append((marketplace, mp_field_mapping))
        super(SaleOrderLine, cls)._add_rec_mp_field_mapping(mp_field_mappings)
