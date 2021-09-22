# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models


class MarketplaceProduct(models.Model):
    _inherit = 'mp.product'

    sp_product_id = fields.Char(string="Shopee Product ID", readonly=True)
    sp_item_status = fields.Char(string="Shopee Product Status", readonly=True)
    sp_has_variant = fields.Boolean(string="Shopee is Variant", readonly=True)

    @classmethod
    def _build_model_attributes(cls, pool):

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
                        'name': pic}
                     )
                )
            return pictures

        def _handle_product_variant(env, data):
            def generate_tier_dict(a, b):
                tier_dict = {}
                for i, aa in enumerate(a):
                    if b:
                        for j, bb in enumerate(b):
                            index_str = str([i, j])
                            tier_dict.update({
                                index_str: [aa, bb]
                            })
                    else:
                        index_str = str([i])
                        tier_dict.update({
                            index_str: [aa]
                        })
                return tier_dict

            variants = [(5, 0, 0)]
            if 'variants' in data:
                value_options1 = []
                value_options2 = []
                for index, tier in enumerate(data['variants']['tier_variation']):
                    for option in tier['option_list']:
                        if index == 0:
                            value_options1.append(option['option'])
                        else:
                            value_options2.append(option['option'])
                tier_dict = generate_tier_dict(value_options1, value_options2)
                product_name = data['item_name']
                for attr in data['variants']['model']:
                    tier_key = str(attr['tier_index'])
                    variants.append((0, 0, {
                        'mp_account_id': env.context['mp_account_id'],
                        'name': product_name+' - %s' % (','.join(tier_dict[tier_key])),
                        'default_code': attr['model_sku'] if 'model_sku' in attr else False,
                        'list_price': attr['price_info'][0]['original_price'],
                        'sp_variant_id': attr['model_id'],
                        'raw': data['variants']}
                    ))
                return variants
            else:
                return None

        cls._rec_mp_external_id = dict(cls._rec_mp_external_id, **{
            'shopee': 'sp_product_id'
        })

        cls._rec_mp_field_mapping = dict(cls._rec_mp_field_mapping, **{
            'shopee': {
                'name': ('item_list/item_name', None),
                'description_sale': ('item_list/description', None),
                'default_code': ('item_list/item_sku', lambda env, r: r if r else False),
                'list_price': ('item_list/price_info', _handle_price_info),
                'weight': ('item_list/weight', lambda env, r: float(r)),
                'length': ('item_list/dimension/package_length', lambda env, r: float(r)),
                'width': ('item_list/dimension/package_width', lambda env, r: float(r)),
                'height': ('item_list/dimension/package_height', lambda env, r: float(r)),
                'sp_product_id': ('item_list/item_id', None),
                'sp_item_status': ('item_list/item_status', None),
                'sp_has_variant': ('item_list/has_model', None),
                'mp_product_image_ids': ('item_list/image', _handle_product_images),
                'mp_product_variant_ids': ('item_list', _handle_product_variant)
            }
        })
        super(MarketplaceProduct, cls)._build_model_attributes(pool)

    @ api.model
    def shopee_get_sanitizers(self, mp_field_mapping):
        default_sanitizer = self.get_default_sanitizer(mp_field_mapping, root_path='response')
        return {
            'product_info': default_sanitizer
        }
