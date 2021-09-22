# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models


class MarketplaceProduct(models.Model):
    _inherit = 'mp.product'

    tp_product_id = fields.Char(string="Tokopedia Product ID", readonly=True)

    @classmethod
    def _build_model_attributes(cls, pool):
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

        cls._rec_mp_external_id = dict(cls._rec_mp_external_id, **{
            'tokopedia': 'tp_product_id'
        })

        cls._rec_mp_field_mapping = dict(cls._rec_mp_field_mapping, **{
            'tokopedia': {
                'tp_product_id': ('basic/productID', lambda env, r: str(r)),
                'name': ('basic/name', None),
                'description_sale': ('basic/shortDesc', None),
                'default_code': ('other/sku', lambda env, r: r if r else False),
                'list_price': ('price/value', None),
                'weight': ('weight/value', None),
                'length': ('volume/length', None),
                'width': ('volume/width', None),
                'height': ('volume/height', None),
                'mp_product_image_ids': ('pictures', _handle_pictures)
            }
        })
        super(MarketplaceProduct, cls)._build_model_attributes(pool)

    @api.model
    def tokopedia_get_sanitizers(self, mp_field_mapping):
        default_sanitizer = self.get_default_sanitizer(mp_field_mapping, root_path='data')
        return {
            'product_info': default_sanitizer
        }
