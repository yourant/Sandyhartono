# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models


class MPShopeeLogistic(models.Model):
    _name = 'mp.shopee.logistic'
    _inherit = 'mp.base'
    _description = 'Marketplace Shopee Logistic'
    _rec_name = 'logistics_channel_name'
    _rec_mp_external_id = 'logistics_channel_id'

    logistics_channel_id = fields.Char(string="Logistic ID", readonly=True)
    logistics_channel_name = fields.Char(string="Logistic Name", readonly=True)
    logistics_description = fields.Char(string="Logistic Description", readonly=True)
    enabled = fields.Boolean(string='Logistic Enabled', readonly=True)
    cod_enabled = fields.Boolean(string='COD Enabled', readonly=True)
    is_parent = fields.Boolean(string='Logistic Parent', readonly=True)
    item_max_weight = fields.Float(string="Item Max Weight", readonly=True)
    item_min_weight = fields.Float(string="Item Min Weight", readonly=True)
    item_max_volume = fields.Float(string="Item Max Volume", readonly=True)
    item_min_volume = fields.Float(string="Item Min Volume", readonly=True)
    item_max_height = fields.Float(string="Item Max Height", readonly=True)
    item_max_width = fields.Float(string="Item Max Width", readonly=True)
    item_max_length = fields.Float(string="Item Max Length", readonly=True)
    item_max_unit = fields.Char(string="Item Max Unit", readonly=True)

    @classmethod
    def _build_model_attributes(cls, pool):

        def _set_logistic_parent(data):
            parent_logistic_id = [8000, 8001, 8002, 8003, 8004, 8005, 80024, 80008]
            is_parent = True if data in parent_logistic_id else False
            return is_parent

        cls._rec_mp_field_mapping = dict(cls._rec_mp_field_mapping, **{
            'shopee': {
                'logistics_channel_id': ('logistics_channel_list/logistics_channel_id', lambda r: str(r)),
                'logistics_channel_name': ('logistics_channel_list/logistics_channel_name', None),
                'logistics_description': ('logistics_channel_list/logistics_description', None),
                'enabled': ('logistics_channel_list/enabled', None),
                'cod_enabled': ('logistics_channel_list/cod_enabled', None),
                'item_max_weight': ('logistics_channel_list/weight_limit/item_max_weight', None),
                'item_min_weight': ('logistics_channel_list/weight_limit/item_min_weight', None),
                'item_max_volume': ('logistics_channel_list/volume_limit/item_max_volume', None),
                'item_min_volume': ('logistics_channel_list/volume_limit/item_min_volume', None),
                'item_max_height': ('logistics_channel_list/item_max_dimension/height', None),
                'item_max_width': ('logistics_channel_list/item_max_dimension/width', None),
                'item_max_length': ('logistics_channel_list/item_max_dimension/length', None),
                'item_max_unit': ('logistics_channel_list/item_max_dimension/unit', None),
                'is_parent': ('logistics_channel_list/logistics_channel_id', _set_logistic_parent),
            }
        })
        super(MPShopeeLogistic, cls)._build_model_attributes(pool)

    @api.model
    def shopee_get_sanitizers(self, mp_field_mapping):
        default_sanitizer = self.get_default_sanitizer(mp_field_mapping, root_path='response')
        return {
            'logistic_list': default_sanitizer
        }