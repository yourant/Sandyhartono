# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models


class MarketplaceProduct(models.Model):
    _inherit = 'mp.product'

    tp_product_id = fields.Char(string="Tokopedia Product ID", readonly=True)
    tp_has_variant = fields.Boolean(string="Tokopedia Product has Variant", readonly=True)

    @classmethod
    def _add_rec_mp_external_id(cls, marketplace=None, mp_external_id_field=None):
        marketplace, mp_external_id_field = 'tokopedia', 'tp_product_id'
        super(MarketplaceProduct, cls)._add_rec_mp_external_id(marketplace, mp_external_id_field)

    @classmethod
    def _add_rec_mp_field_mapping(cls, mp_field_mappings=None):
        if not mp_field_mappings:
            mp_field_mappings = []

        marketplace = 'tokopedia'
        mp_field_mapping = {
            'tp_product_id': ('basic/productID', lambda env, r: str(r)),
            'tp_has_variant': ('variant/isParent', lambda env, r: r if r else False),
            'name': ('basic/name', None),
            'description_sale': ('basic/shortDesc', None),
            'default_code': ('other/sku', lambda env, r: r if r else False),
            'list_price': ('price/value', None),
            'weight': ('weight/value', None),
            'length': ('volume/length', None),
            'width': ('volume/width', None),
            'height': ('volume/height', None),
        }

        def _handle_pictures(env, data):
            mp_product_image_obj = env['mp.product.image']

            mp_product_image_data = [(5,)]

            raw_datas, sanitized_datas = mp_product_image_obj._prepare_mapping_raw_data(raw_data=data)
            sanitized_datas, values_list = mp_product_image_obj._run_mapping_raw_data(raw_datas, sanitized_datas,
                                                                                      multi=isinstance(sanitized_datas,
                                                                                                       list))
            for values in values_list:
                mp_product_image_data.append((0, 0, values))

            return mp_product_image_data

        mp_field_mapping.update({
            'mp_product_image_ids': ('pictures', _handle_pictures)
        })

        mp_field_mappings.append((marketplace, mp_field_mapping))
        super(MarketplaceProduct, cls)._add_rec_mp_field_mapping(mp_field_mappings)

    @api.model
    def tokopedia_get_sanitizers(self, mp_field_mapping):
        default_sanitizer = self.get_default_sanitizer(mp_field_mapping, root_path='data')
        return {
            'product_info': default_sanitizer
        }
