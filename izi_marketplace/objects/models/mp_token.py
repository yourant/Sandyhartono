# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models


class MarketplaceToken(models.Model):
    _name = 'mp.token'
    _description = 'Marketplace Access Token'

    name = fields.Char(string="Token", required=True)
    expired_date = fields.Datetime(string="Expired Date", required=True)
    mp_account_id = fields.Many2one(comodel_name="mp.account", string="Marketplace Account", required=True)
    raw = fields.Text(string="Raw Data", required=True, default="{}")

    @api.model
    def create_token(self, mp_account, raw_token):
        if hasattr(self, '%s_create_token' % mp_account.marketplace):
            getattr(self, '%s_create_token' % mp_account.marketplace)(mp_account, raw_token)
