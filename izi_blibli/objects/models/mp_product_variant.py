# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models

from odoo.addons.izi_marketplace.objects.utils.tools import get_mp_asset


class MarketplaceProductVariant(models.Model):
    _inherit = 'mp.product.variant'

    bli_variant_id = fields.Char(string="Blibli Product Variant ID", readonly=True)

    @classmethod
    def _add_rec_mp_external_id(cls, marketplace=None, mp_external_id_field=None):
        marketplace, mp_external_id_field = 'blibli', 'bli_variant_id'
        super(MarketplaceProductVariant, cls)._add_rec_mp_external_id(marketplace, mp_external_id_field)

    @classmethod
    def _add_rec_mp_field_mapping(cls, marketplace=None, mp_field_mapping=None):
        marketplace = 'blibli'

        mp_field_mapping = {
            # 'name': ('items', _handle_name),
            # 'image': ('items', _handle_image),
            # 'list_price': ('items', _handle_price_info),
            # 'default_code': ('items', _handle_default_code),
            # 'weight': ('items', _handle_weight),
            # 'length': ('items', _handle_length),
            # 'width': ('items', _handle_width),
            # 'height': ('items', _handle_height),
            # 'bli_product_id': ('items', _handle_product_id)
        }

        def _handle_parent_id(env, data):
            mp_product_obj = env['mp.product']
            mp_product = mp_product_obj.search_mp_records('blibli', data)
            if mp_product:
                return mp_product.id
            return None

        mp_field_mapping.update({
            'mp_product_id': ('variant/parentID', _handle_parent_id),
        })

        super(MarketplaceProductVariant, cls)._add_rec_mp_field_mapping(marketplace, mp_field_mapping)

    @api.model
    def blibli_get_sanitizers(self, mp_field_mapping):
        default_sanitizer = self.get_default_sanitizer(mp_field_mapping, root_path='value')
        return {
            'product_info': default_sanitizer
        }
