# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models
from odoo.addons.izi_marketplace.objects.utils.tools import get_mp_asset


class MarketplaceProduct(models.Model):
    _inherit = 'mp.product'

    sp_product_id = fields.Char(string="Shopee Product ID", readonly=True)
    sp_item_status = fields.Char(string="Shopee Product Status", readonly=True)
    sp_has_variant = fields.Boolean(string="Shopee is Variant", readonly=True)

    @classmethod
    def _add_rec_mp_external_id(cls, marketplace=None, mp_external_id_field=None):
        marketplace, mp_external_id_field = 'shopee', 'sp_product_id'
        super(MarketplaceProduct, cls)._add_rec_mp_external_id(marketplace, mp_external_id_field)

    @classmethod
    def _add_rec_mp_field_mapping(cls, marketplace=None, mp_field_mapping=None):
        marketplace = 'shopee'

        mp_field_mapping = {
            'name': ('item_list/item_name', None),
            'description_sale': ('item_list/description', None),
            'default_code': ('item_list/item_sku', lambda env, r: r if r else False),
            'weight': ('item_list/weight', lambda env, r: float(r)),
            'length': ('item_list/dimension/package_length', lambda env, r: float(r)),
            'width': ('item_list/dimension/package_width', lambda env, r: float(r)),
            'height': ('item_list/dimension/package_height', lambda env, r: float(r)),
            'sp_product_id': ('item_list/item_id', None),
            'sp_item_status': ('item_list/item_status', None),
            'sp_has_variant': ('item_list/has_model', None),
        }

        def _handle_price_info(env, data):
            if data:
                return data[0].get('original_price')
            else:
                return None

        def _handle_product_images(env, data):
            pictures = [(5, 0, 0)]
            for index, pic in enumerate(data['image_url_list']):
                pictures.append(
                    (0, 0, {
                        'mp_account_id': env.context['mp_account_id'],
                        'sp_image_id': data['image_id_list'][index],
                        'sequence': index,
                        'name': pic,
                        'image': get_mp_asset(pic)}
                     )
                )
            return pictures

        mp_field_mapping.update({
            'list_price': ('item_list/price_info', _handle_price_info),
            'mp_product_image_ids': ('item_list/image', _handle_product_images),
            })

        super(MarketplaceProduct, cls)._add_rec_mp_field_mapping(marketplace, mp_field_mapping)

    @api.model
    def shopee_get_sanitizers(self, mp_field_mapping):
        default_sanitizer = self.get_default_sanitizer(mp_field_mapping, root_path='response')
        return {
            'product_info': default_sanitizer
        }
