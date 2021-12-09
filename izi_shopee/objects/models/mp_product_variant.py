# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models
from odoo.addons.izi_marketplace.objects.utils.tools import json_digger
from odoo.addons.izi_marketplace.objects.utils.tools import get_mp_asset


class MPProductVariant(models.Model):
    _inherit = 'mp.product.variant'

    sp_variant_id = fields.Char(string='Product Variant External ID')
    sp_variant_image_id = fields.Char(string='Product Variant Image ID')

    @classmethod
    def _add_rec_mp_external_id(cls, mp_external_id_fields=None):
        if not mp_external_id_fields:
            mp_external_id_fields = []

        mp_external_id_fields.append(('shopee', 'sp_variant_id'))
        super(MPProductVariant, cls)._add_rec_mp_external_id(mp_external_id_fields)

    @classmethod
    def _add_rec_mp_field_mapping(cls, mp_field_mappings=None):
        if not mp_field_mappings:
            mp_field_mappings = []

        marketplace = 'shopee'
        mp_field_mapping = {
            'sp_variant_id': ('sp_variant_id', lambda env, r: str(r)),
            'name': ('name', None),
            'default_code': ('default_code', lambda env, r: r if r else False),
            'list_price': ('list_price', None),
            'weight': ('weight', lambda env, r: float(r)),
            'sp_variant_image_id': ('image_id', None)
        }

        def _handle_parent_id(env, data):
            mp_product_obj = env['mp.product']
            mp_product = mp_product_obj.search_mp_records('shopee', data)
            if mp_product:
                return mp_product.id
            return None

        def _handle_product_images(env, data):
            if data and env.context.get('store_product_img'):
                return get_mp_asset(data)
            else:
                return None

        mp_field_mapping.update({
            'image': ('image', _handle_product_images),
            'mp_product_id': ('mp_product_id', _handle_parent_id),
        })

        mp_field_mappings.append((marketplace, mp_field_mapping))
        super(MPProductVariant, cls)._add_rec_mp_field_mapping(mp_field_mappings)

    @api.model
    def generate_variant_data(self, mp_product_raw):
        variant_list = []

        varian_model = json_digger(mp_product_raw, 'variants/model')
        varian_tier = json_digger(mp_product_raw, 'variants/tier_variation')

        def generate_tier_dict(tier_variation):
            tier_dict = {}
            num_attrs = len(tier_variation)
            if num_attrs == 1:
                attr = tier_variation[0]
                for attr_value_index, attr_value in enumerate(attr['option_list']):
                    key = str([attr_value_index])
                    value = {
                        'name': [attr_value.get('option')],
                        'image': attr_value.get('image', {})
                    }
                    tier_dict.update(dict([(key, value)]))
            elif num_attrs == 2:
                first_attr_values = [dict([('name', attr_value.get('option')), ('image', attr_value.get('image', {}))])
                                     for attr_value in tier_variation[0]['option_list']]
                second_attr_values = [dict([('name', attr_value.get('option')), ('image', attr_value.get('image', {}))])
                                      for attr_value in tier_variation[1]['option_list']]
                for first_attr_value_index, first_attr_value in enumerate(first_attr_values):
                    for second_attr_value_index, second_attr_value in enumerate(second_attr_values):
                        key = str([first_attr_value_index, second_attr_value_index])
                        value = {
                            'name': [first_attr_value['name'], second_attr_value['name']],
                            'image': first_attr_value.get('image', {})
                        }
                        tier_dict.update(dict([(key, value)]))
            return tier_dict

        tier_dict = generate_tier_dict(varian_tier)

        for model in varian_model:
            variant_dict = {
                'mp_product_id': mp_product_raw['item_id'],
                'weight': mp_product_raw['weight'],
                'sp_variant_id': json_digger(model, 'model_id'),
                'list_price': json_digger(model, 'price_info/original_price')[0],
                'default_code': json_digger(model, 'model_sku')
            }

            tier_index = str(json_digger(model, 'tier_index'))
            product_name = mp_product_raw['item_name']
            product_variant_name = product_name+' - %s' % (','.join(tier_dict[tier_index]['name']))
            product_variant_image = tier_dict[tier_index]['image'].get('image_url', None)
            product_variant_image_id = tier_dict[tier_index]['image'].get('image_id', None)

            variant_dict.update({
                'name': product_variant_name,
                'image': product_variant_image,
                'image_id': product_variant_image_id
            })

            variant_list.append(variant_dict)

        return variant_list

    @api.model
    def shopee_get_sanitizers(self, mp_field_mapping):
        default_sanitizer = self.get_default_sanitizer(mp_field_mapping, root_path='data')
        return {
            'product_info': default_sanitizer
        }
