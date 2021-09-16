# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import json

from odoo import api, fields, models


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
            rec.mp_external_id = getattr(rec, rec._rec_mp_external_id, False)

    @api.model
    def format_raw_data(self, raw, indent=4):
        return json.dumps(raw, indent=indent)
