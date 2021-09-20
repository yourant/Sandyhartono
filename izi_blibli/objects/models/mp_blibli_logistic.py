# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models


class MPBlibliLogistic(models.Model):
    _name = 'mp.blibli.logistic'
    _inherit = 'mp.base'
    _description = 'Marketplace Blibli Logistic'
    _rec_mp_external_id = 'logistics_channel_id'

    logistics_channel_id = fields.Char(string="Logistic ID", readonly=True, mp_raw=True)
    logistics_channel_name = fields.Char(string="Logistic Name", readonly=True, mp_raw=True)
    logistics_description = fields.Char(string="Logistic Description", readonly=True, mp_raw=True)
    enabled = fields.Boolean(string='Logistic Enabled', readonly=True, mp_raw=True)
    cod_enabled = fields.Boolean(string='COD Enabled', readonly=True, mp_raw=True)
    is_parent = fields.Boolean(string='Logistic Parent', readonly=True)
    item_max_weight = fields.Float(string="Item Max Weight", readonly=True)
    item_min_weight = fields.Float(string="Item Min Weight", readonly=True)
    item_max_volume = fields.Float(string="Item Max Volume", readonly=True)
    item_min_volume = fields.Float(string="Item Min Volume", readonly=True)
    item_max_height = fields.Float(string="Item Max Height", readonly=True)
    item_max_width = fields.Float(string="Item Max Width", readonly=True)
    item_max_length = fields.Float(string="Item Max Length", readonly=True)
    item_max_unit = fields.Char(string="Item Max Unit", readonly=True)

    @api.model
    def mapping_raw_data(self, raw_data=None, values=None):
        raw_data, values = super(MPBlibliLogistic, self).mapping_raw_data(raw_data=raw_data, values=values)
        parent_logistic_id = [8000, 8001, 8002, 8003, 8004, 8005, 80024, 80008]
        values.update({
            'logistics_channel_id': str(raw_data['logistics_channel_id']),
            'item_max_weight': raw_data['weight_limit']['item_max_weight'],
            'item_min_weight': raw_data['weight_limit']['item_min_weight'],
            'item_max_volume': raw_data['volume_limit']['item_max_volume'],
            'item_min_volume': raw_data['volume_limit']['item_min_volume'],
            'item_max_height': raw_data['item_max_dimension']['height'],
            'item_max_width': raw_data['item_max_dimension']['width'],
            'item_max_length': raw_data['item_max_dimension']['length'],
            'item_max_unit': raw_data['item_max_dimension']['unit'],
            'is_parent': True if raw_data['logistics_channel_id'] in parent_logistic_id else False
        })

        return raw_data, values

    @api.model
    def create_logistic(self, bli_data, multi=False):
        mp_blibli_logistic_obj = self.env['mp.blibli.logistic']

        if multi:
            sp_datas = bli_data
            mp_blibli_logistics = mp_blibli_logistic_obj

            for sp_data in sp_datas:
                mp_blibli_logistics |= self.create_logistic(bli_data)

            return mp_blibli_logistics

        logistic_data = bli_data['logistics_channel_list']
        for data in logistic_data:
            raw_data, values = self.mapping_raw_data(raw_data=data)
            mp_blibli_logistic_obj.create(values)
