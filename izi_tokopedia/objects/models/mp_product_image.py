# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models

from odoo.addons.izi_marketplace.objects.utils.tools import get_mp_asset


class MarketplaceProductImage(models.Model):
    _inherit = 'mp.product.image'

    tp_image_id = fields.Char(string='Tokopedia Product Image ID', readonly=True)
    tp_filename = fields.Char(string="Tokopedia Product Image File Name", readonly=True)


    @classmethod
    def _add_rec_mp_field_mapping(cls, mp_field_mappings=None):
        if not mp_field_mappings:
            mp_field_mappings = []

        marketplace = 'tokopedia'
        mp_field_mapping = {
            'name': ('OriginalURL', None),
            'image': ('OriginalURL',
                      lambda env, r: get_mp_asset(r) if env.context.get('store_product_img') else None),
            'mp_external_id': ('picID', lambda env, r: str(r)),
            'tp_image_id': ('picID', lambda env, r: str(r)),
            'tp_filename': ('fileName', None),
        }

        mp_field_mappings.append((marketplace, mp_field_mapping))
        super(MarketplaceProductImage, cls)._add_rec_mp_field_mapping(mp_field_mappings)

    @api.model
    def tokopedia_get_sanitizers(self, mp_field_mapping):
        default_sanitizer = self.get_default_sanitizer(mp_field_mapping, root_path='data')
        return {
            'product_info': default_sanitizer
        }

    @api.model
    def _finish_mapping_raw_data(self, sanitized_data, values):
        context = self._context
        sanitized_data, values = super(MarketplaceProductImage, self)._finish_mapping_raw_data(sanitized_data, values)
        if 'index' in context:
            values['sequence'] = context.get('index')
        return sanitized_data, values
