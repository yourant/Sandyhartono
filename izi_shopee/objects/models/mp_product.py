# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models


class MarketplaceProduct(models.Model):
    _inherit = 'mp.product'

    sp_product_id = fields.Char(string="Shopee Product ID", readonly=True)
    sp_item_status = fields.Char(string="Shopee Item Status", readonly=True)

    @classmethod
    def _build_model_attributes(cls, pool):

        def _handler_price_info(env, data):
            if data:
                return data[0].get('original_price')
            else:
                return None

        def _handler_product_images(env, data):
            pictures = []
            for index, pic in enumerate(data['image_url_list']):
                pictures.append(
                    (0, 0, {
                        'mp_account_id': env.context['mp_account_id'],
                        'sp_image_id': data['image_id_list'][index],
                        'name': pic}
                     )
                )
            return pictures

        cls._rec_mp_external_id = dict(cls._rec_mp_external_id, **{
            'shopee': 'sp_product_id'
        })

        cls._rec_mp_field_mapping = dict(cls._rec_mp_field_mapping, **{
            'shopee': {
                'name': ('item_list/item_name', None),
                'description_sale': ('item_list/description', None),
                'default_code': ('item_list/item_sku', lambda env, r: r if r else False),
                'list_price': ('item_list/price_info', _handler_price_info),
                'weight': ('item_list/weight', lambda env, r: float(r)),
                'length': ('item_list/dimension/package_length', lambda env, r: float(r)),
                'width': ('item_list/dimension/package_width', lambda env, r: float(r)),
                'height': ('item_list/dimension/package_height', lambda env, r: float(r)),
                'sp_product_id': ('item_list/item_id', None),
                'sp_item_status': ('item_list/item_status', None),
                'mp_product_image_ids': ('item_list/image', _handler_product_images)
            }
        })
        super(MarketplaceProduct, cls)._build_model_attributes(pool)

    @api.model
    def shopee_get_sanitizers(self, mp_field_mapping):
        default_sanitizer = self.get_default_sanitizer(mp_field_mapping, root_path='response')
        return {
            'product_info': default_sanitizer
        }
