# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    bli_order_item_id = fields.Char(string="Blibli Order Item ID", required_if_marketplace="blibli")

    @classmethod
    def _add_rec_mp_external_id(cls, mp_external_id_fields=None):
        if not mp_external_id_fields:
            mp_external_id_fields = []

        mp_external_id_fields.append(('blibli', 'bli_order_item_id'))
        super(SaleOrderLine, cls)._add_rec_mp_external_id(mp_external_id_fields)

    @classmethod
    def _add_rec_mp_field_mapping(cls, mp_field_mappings=None):
        if not mp_field_mappings:
            mp_field_mappings = []

        marketplace = 'blibli'
        mp_field_mapping = {
            'order_id': ('order_id', None),
            'bli_order_item_id': ('orderItemNo', lambda env, r: str(r)),
            'name': ('productName', None),
            'price_unit': ('productPrice', None),
            'bli_weight': ('itemWeightInKg', None),
            'product_uom_qty': ('qty', None),
            'bli_insurance_price': ('insurance_price', None),
        }

        def _handle_product_id(env, data):
            product_obj = env['product.product']
            mp_product_obj = env['mp.product']
            mp_product_variant_obj = env['mp.product.variant']

            product = product_obj
            mp_product = mp_product_obj.search_mp_records('blibli', data)
            mp_product_variant = mp_product_variant_obj.search_mp_records('blibli', data)

            if mp_product.exists():
                product = mp_product.get_product()
            if mp_product_variant.exists():
                product = mp_product_variant.get_product()

            return product.id

        mp_field_mapping.update({'product_id': ('gdnItemSku', _handle_product_id)})

        mp_field_mappings.append((marketplace, mp_field_mapping))
        super(SaleOrderLine, cls)._add_rec_mp_field_mapping(mp_field_mappings)
