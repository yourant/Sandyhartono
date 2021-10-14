# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models
from lxml.html import fromstring as html_fromstring


class MPShopeeLogistic(models.Model):
    _name = 'mp.shopee.logistic'
    _inherit = 'mp.base'
    _description = 'Marketplace Shopee Logistic'
    _rec_name = 'logistics_channel_name'
    _rec_mp_external_id = 'logistics_channel_id'

    logistics_channel_id = fields.Char(string="Logistic ID", readonly=True)
    logistics_channel_name = fields.Char(string="Logistic Name", readonly=True)
    logistics_description = fields.Char(string="Logistic Description", readonly=True)
    is_category = fields.Boolean(string='Logistic Category', readonly=True)
    item_max_weight = fields.Float(string="Item Max Weight", readonly=True)
    item_min_weight = fields.Float(string="Item Min Weight", readonly=True)
    item_max_volume = fields.Float(string="Item Max Volume", readonly=True)
    item_min_volume = fields.Float(string="Item Min Volume", readonly=True)
    item_max_height = fields.Float(string="Item Max Height", readonly=True)
    item_max_width = fields.Float(string="Item Max Width", readonly=True)
    item_max_length = fields.Float(string="Item Max Length", readonly=True)
    item_max_unit = fields.Char(string="Item Max Unit", readonly=True)
    product_id = fields.Many2one(comodel_name="product.product", string="Delivery Product", required=False,
                                 default=lambda self: self._get_default_product_id())

    @classmethod
    def _add_rec_mp_field_mapping(cls, mp_field_mappings=None):
        if not mp_field_mappings:
            mp_field_mappings = []

        marketplace = 'shopee'
        mp_field_mapping = {
            'logistics_channel_id': ('logistics_channel_list/logistics_channel_id', lambda env, r: str(r)),
            'logistics_channel_name': ('logistics_channel_list/logistics_channel_name', None),
            'item_max_weight': ('logistics_channel_list/weight_limit/item_max_weight', None),
            'item_min_weight': ('logistics_channel_list/weight_limit/item_min_weight', None),
            'item_max_volume': ('logistics_channel_list/volume_limit/item_max_volume', None),
            'item_min_volume': ('logistics_channel_list/volume_limit/item_min_volume', None),
            'item_max_height': ('logistics_channel_list/item_max_dimension/height', None),
            'item_max_width': ('logistics_channel_list/item_max_dimension/width', None),
            'item_max_length': ('logistics_channel_list/item_max_dimension/length', None),
            'item_max_unit': ('logistics_channel_list/item_max_dimension/unit', None),
        }

        def _set_logistic_parent(env, data):
            category_logistic_id = [8000, 8001, 8002, 8003, 8004, 8005, 80024, 80008, 80032, 80031, 80028, 80021]
            is_category = True if data in category_logistic_id else False
            return is_category

        def _parsing_logistic_description(env, data):
            if data:
                return html_fromstring(data).text_content()
            else:
                return None

        mp_field_mapping.update({
            'logistics_description': ('logistics_channel_list/logistics_description', _parsing_logistic_description),
            'is_category': ('logistics_channel_list/logistics_channel_id', _set_logistic_parent),
        })

        mp_field_mappings.append((marketplace, mp_field_mapping))
        super(MPShopeeLogistic, cls)._add_rec_mp_field_mapping(mp_field_mappings)

    @api.model
    def shopee_get_sanitizers(self, mp_field_mapping):
        default_sanitizer = self.get_default_sanitizer(mp_field_mapping, root_path='response')
        return {
            'logistic_list': default_sanitizer
        }

    @api.model
    def _get_default_product_id(self):
        mp_delivery_product_tmpl = self.env.ref('izi_marketplace.product_tmpl_mp_delivery', raise_if_not_found=False)
        if mp_delivery_product_tmpl:
            return mp_delivery_product_tmpl.product_variant_id.id
        return False

    @api.model
    def _finish_mapping_raw_data(self, sanitized_data, values):
        sanitized_data, values = super(MPShopeeLogistic, self)._finish_mapping_raw_data(sanitized_data, values)
        mp_account = self.get_mp_account_from_context()
        values.update({
            'shop_id': mp_account.sp_shop_id.id
        })
        return sanitized_data, values

    @api.multi
    def get_delivery_product(self):
        self.ensure_one()
        if self.product_id:
            return self.product_id
        if self.logistic_id.product_id:
            return self.logistic_id.product_id
        return self.env['product.product']
