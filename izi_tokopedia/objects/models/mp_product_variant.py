# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models

from odoo.addons.izi_marketplace.objects.utils.tools import get_mp_asset


class MarketplaceProductVariant(models.Model):
    _inherit = 'mp.product.variant'

    tp_variant_id = fields.Char(string="Tokopedia Product Variant ID", readonly=True)

    @classmethod
    def _add_rec_mp_external_id(cls, mp_external_id_fields=None):
        if not mp_external_id_fields:
            mp_external_id_fields = []

        mp_external_id_fields.append(('tokopedia', 'tp_variant_id'))
        super(MarketplaceProductVariant, cls)._add_rec_mp_external_id(mp_external_id_fields)

    @classmethod
    def _add_rec_mp_field_mapping(cls, mp_field_mappings=None):
        if not mp_field_mappings:
            mp_field_mappings = []

        marketplace = 'tokopedia'
        mp_field_mapping = {
            'tp_variant_id': ('basic/productID', lambda env, r: str(r)),
            'name': ('basic/name', None),
            'default_code': ('other/sku', lambda env, r: r if r else False),
            'list_price': ('price/value', None),
            'weight': ('weight/value', None),
            'length': ('volume/length', None),
            'width': ('volume/width', None),
            'height': ('volume/height', None),
            'image': ('pictures/OriginalURL', lambda env, r: get_mp_asset(r[0])),
        }

        def _handle_parent_id(env, data):
            mp_product_obj = env['mp.product']
            mp_product = mp_product_obj.search_mp_records('tokopedia', data)
            if mp_product:
                return mp_product.id
            return None

        mp_field_mapping.update({
            'mp_product_id': ('variant/parentID', _handle_parent_id),
        })

        mp_field_mappings.append((marketplace, mp_field_mapping))
        super(MarketplaceProductVariant, cls)._add_rec_mp_field_mapping(mp_field_mappings)

    @api.model
    def tokopedia_get_sanitizers(self, mp_field_mapping):
        default_sanitizer = self.get_default_sanitizer(mp_field_mapping, root_path='data')
        return {
            'product_info': default_sanitizer
        }