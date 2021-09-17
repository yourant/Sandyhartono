# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import json

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class MarketplaceBase(models.AbstractModel):
    _name = 'mp.base'
    _description = 'Marketplace Base Model'
    _rec_mp_external_id = None

    mp_account_id = fields.Many2one(comodel_name="mp.account", string="Marketplace Account", required=True)
    marketplace = fields.Selection(related="mp_account_id.marketplace", readonly=True)
    raw = fields.Text(string="Raw Data", readonly=True, required=True, default="{}")
    mp_external_id = fields.Integer(string="Marketplace External ID", compute="_compute_mp_external_id")

    @api.multi
    def _compute_mp_external_id(self):
        for rec in self:
            if isinstance(rec._rec_mp_external_id, str):
                rec.mp_external_id = getattr(rec, rec._rec_mp_external_id, False)
            elif isinstance(rec._rec_mp_external_id, dict):
                rec.mp_external_id = getattr(rec, rec._rec_mp_external_id.get(rec.marketplace), False)
            else:
                rec.mp_external_id = False

    @api.model
    def _get_mp_raw_fields(self):
        raw_data_fields = []
        for field_name, field in self._fields.items():
            if getattr(field, 'mp_raw', False):
                raw_data_fields.append((field_name, getattr(field, 'mp_raw_handler', None)))
        return raw_data_fields

    @api.model
    def mapping_raw_data(self, raw_data=None, values=None):
        """Please inherit this method for each marketplace data model to define data handling method!"""

        if not isinstance(raw_data, dict):
            raise ValidationError(
                "raw_data should be in dictionary format! You may need iteration to handling multiple data.")

        context = self._context
        if not context.get('mp_account_id'):
            raise ValidationError("Please define mp_account_id in context!")

        if not raw_data:
            raw_data = {}

        if not values:
            values = {}

        raw_data_fields = self._get_mp_raw_fields()
        for raw_data_field in raw_data_fields:
            field_name, mp_raw_handler = raw_data_field
            if not mp_raw_handler:
                values[field_name] = raw_data[field_name]
                continue
            values[field_name] = mp_raw_handler(raw_data[field_name])

        values.update({
            'mp_account_id': context.get('mp_account_id'),
            'raw': self.format_raw_data(raw_data)
        })

        return raw_data, values

    @api.model
    def format_raw_data(self, raw, indent=4):
        return json.dumps(raw, indent=indent)
