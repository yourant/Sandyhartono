# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models
from lxml.html import fromstring as html_fromstring
from odoo.addons.izi_marketplace.objects.utils.tools import get_mp_asset


class MarketplaceProduct(models.Model):
    _inherit = 'mp.product'

    bli_product_id = fields.Char(string="Blibli Product ID", readonly=True)
    bli_has_variant = fields.Boolean(string="Blibli Product has Variant", readonly=True)

    @classmethod
    def _add_rec_mp_external_id(cls, mp_external_id_fields=None):
        if not mp_external_id_fields:
            mp_external_id_fields = []

        mp_external_id_fields.append(('blibli', 'bli_product_id'))
        super(MarketplaceProduct, cls)._add_rec_mp_external_id(mp_external_id_fields)

    @classmethod
    def _add_rec_mp_field_mapping(cls, mp_field_mappings=None):
        if not mp_field_mappings:
            mp_field_mappings = []

        marketplace = 'blibli'
        mp_field_mapping = {
            'name': ('productName', None),
            'bli_has_variant': ('bli_has_variant', None),
        }

        def _handle_price_info(env, data):
            if data:
                return data[0]['prices'][0]['price']
            else:
                return None

        def _handle_default_code(env, data):
            if data:
                return data[0].get('merchantSku')
            else:
                return None

        def _handle_weight(env, data):
            if data:
                return data[0].get('shippingWeight')
            else:
                return None

        def _handle_length(env, data):
            if data:
                return data[0].get('length')
            else:
                return None

        def _handle_height(env, data):
            if data:
                return data[0].get('height')
            else:
                return None

        def _handle_width(env, data):
            if data:
                return data[0].get('width')
            else:
                return None

        def _handle_product_id(env, data):
            if data:
                return data[0].get('itemSku')
            else:
                return None

        def _handle_description(env, data):
            if data:
                return html_fromstring(data).text_content()
            else:
                return None

        def _handle_product_images(env, data):
            if data:
                pictures = [(5, 0, 0)]
                for index, pic in enumerate(data[0]['images']):
                    base_data_image = {
                            'mp_account_id': env.context['mp_account_id'],
                            'bli_image_id': data[0]['merchantSku']+str(index),
                            'name': pic['locationPath']
                            }
                    if env.context.get('store_product_img'):
                        base_data_image.update({
                            'image': get_mp_asset(pic['locationPath'])
                        })
                    pictures.append((0, 0, base_data_image))
                return pictures
            else:
                return None

        mp_field_mapping.update({
            'mp_product_image_ids': ('items', _handle_product_images),
            'list_price': ('items', _handle_price_info),
            'description_sale': ('description', _handle_description),
            'default_code': ('items', _handle_default_code),
            'weight': ('items', _handle_weight),
            'length': ('items', _handle_length),
            'width': ('items', _handle_width),
            'height': ('items', _handle_height),
            'bli_product_id': ('items', _handle_product_id)
        })

        mp_field_mappings.append((marketplace, mp_field_mapping))
        super(MarketplaceProduct, cls)._add_rec_mp_field_mapping(mp_field_mappings)

    @ api.model
    def blibli_get_sanitizers(self, mp_field_mapping):
        default_sanitizer = self.get_default_sanitizer(mp_field_mapping, root_path='value')
        return {
            'product_info': default_sanitizer
        }
