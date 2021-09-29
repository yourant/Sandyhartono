# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models

from odoo.addons.izi_marketplace.objects.utils.tools import get_mp_asset


class MarketplaceProductVariant(models.Model):
    _inherit = 'mp.product.variant'

    bli_variant_id = fields.Char(string="Blibli Product Variant ID", readonly=True)

    @classmethod
    def _add_rec_mp_external_id(cls, mp_external_id_fields=None):
        if not mp_external_id_fields:
            mp_external_id_fields = []

        mp_external_id_fields.append(('blibli', 'bli_variant_id'))
        super(MarketplaceProductVariant, cls)._add_rec_mp_external_id(mp_external_id_fields)

    @classmethod
    def _add_rec_mp_field_mapping(cls, mp_field_mappings=None):
        if not mp_field_mappings:
            mp_field_mappings = []

        marketplace = 'blibli'
        mp_field_mapping = {}

        def _handle_price_info(env, data):
            if data:
                return data['prices'][0]['price']
            else:
                return None

        def _handle_default_code(env, data):
            if data:
                return data.get('merchantSku')
            else:
                return None

        def _handle_weight(env, data):
            if data:
                return data.get('weight')
            else:
                return None

        def _handle_length(env, data):
            if data:
                return data.get('length')
            else:
                return None

        def _handle_height(env, data):
            if data:
                return data.get('height')
            else:
                return None

        def _handle_width(env, data):
            if data:
                return data.get('width')
            else:
                return None

        def _handle_product_id(env, data):
            if data:
                return data.get('itemSku')
            else:
                return None

        def _handle_name(env, data):
            if data:
                return data.get('itemName')
            else:
                return None

        def _handle_image(env, data):
            if data:
                if env.context.get('store_product_img'):
                    return get_mp_asset(data['images'][0]['locationPath'])
            else:
                return None

        def _handle_parent_id(env, data):
            mp_product_obj = env['mp.product']
            mp_product = mp_product_obj.search_mp_records('blibli', data['itemSku'][:16]+'00001')
            if mp_product:
                return mp_product.id
            return None

        mp_field_mapping.update({
            'name': ('items', _handle_name),
            'image': ('items', _handle_image),
            'list_price': ('items', _handle_price_info),
            'default_code': ('items', _handle_default_code),
            'mp_product_id': ('items', _handle_parent_id),
            'weight': ('items', _handle_weight),
            'length': ('items', _handle_length),
            'width': ('items', _handle_width),
            'height': ('items', _handle_height),
            'bli_variant_id': ('items', _handle_product_id)
        })

        mp_field_mappings.append((marketplace, mp_field_mapping))
        super(MarketplaceProductVariant, cls)._add_rec_mp_field_mapping(mp_field_mappings)

    @api.model
    def blibli_get_sanitizers(self, mp_field_mapping):
        default_sanitizer = self.get_default_sanitizer(mp_field_mapping, root_path='value')
        return {
            'product_info': default_sanitizer
        }
