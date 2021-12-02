# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    is_shopee_coins = fields.Boolean(string="Is a Shopee Coins", default=False)

    @classmethod
    def _add_rec_mp_field_mapping(cls, mp_field_mappings=None):
        if not mp_field_mappings:
            mp_field_mappings = []

        marketplace = 'shopee'
        mp_field_mapping = {
            'order_id': ('order_id', None),
            'mp_exid': ('mp_order_exid', None),
            'mp_product_name': ('item_name', None),
            'sp_weight': ('weight', None),
            'product_uom_qty': ('model_quantity_purchased', None),
            'sp_discounted_price': ('model_discounted_price', None),
            'sp_original_price': ('model_original_price', None),
        }

        def _handle_product_id(env, data):
            product_obj = env['product.product']
            mp_product_obj = env['mp.product']
            mp_product_variant_obj = env['mp.product.variant']

            product_id = data.get('item_id', False)
            model_id = data.get('model_id', False)

            product = product_obj
            mp_product = mp_product_obj.search_mp_records('shopee', product_id)
            mp_product_variant = mp_product_variant_obj.search_mp_records('shopee', model_id)

            if mp_product.exists():
                product = mp_product.get_product()
            if mp_product_variant.exists():
                product = mp_product_variant.get_product()

            return product.id

        def _handle_product_sku(env, data):
            sku = None
            if data['item_sku']:
                sku = data['item_sku']
            if data['model_sku']:
                sku = data['model_sku']
            return sku

        def _handle_price_unit(env, data):
            order_component_configs = env['order.component.config'].sudo().search(
                [('active', '=', True), ('mp_account_ids', 'in', env.context.get('mp_account_id'))])
            for component_config in order_component_configs:
                # Process to Remove Product First
                for line in component_config.line_ids:
                    if line.component_type == 'remove_product':
                        if line.remove_discount:
                            return data['model_discounted_price']
            return data['model_original_price']

        mp_field_mapping.update({
            'product_id': ('item_info', _handle_product_id),
            'sp_sku': ('item_info', _handle_product_sku),
            'price_unit': ('item_info', _handle_price_unit)
        })

        mp_field_mappings.append((marketplace, mp_field_mapping))
        super(SaleOrderLine, cls)._add_rec_mp_field_mapping(mp_field_mappings)
