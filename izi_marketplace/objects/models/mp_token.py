# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
from datetime import datetime

from odoo import api, fields, models


class MarketplaceToken(models.Model):
    _name = 'mp.token'
    _inherit = 'mp.base'
    _description = 'Marketplace Access Token'

    TOKEN_STATES = [
        ('valid', 'Valid'),
        ('expired', 'Expired')
    ]

    name = fields.Char(string="Token", readonly=True, required=True)
    expired_date = fields.Datetime(string="Expired Date", readonly=True, required=True)
    mp_account_id = fields.Many2one(readonly=True)
    state = fields.Selection(string="Status", selection=TOKEN_STATES, compute="_compute_state")
    refresh_token = fields.Char(string="Refresh Token")

    @api.multi
    def _compute_state(self):
        for token in self:
            if datetime.now() > fields.Datetime.from_string(token.expired_date):
                token.state = 'expired'
            else:
                token.state = 'valid'

    @api.model
    def create_token(self, mp_account, raw_token):
        if hasattr(self, '%s_create_token' % mp_account.marketplace):
            getattr(self, '%s_create_token' % mp_account.marketplace)(mp_account, raw_token)

    @api.multi
    def validate_current_token(self):
        self.ensure_one()
        if hasattr(self, '%s_validate_current_token' % self.marketplace):
            return getattr(self, '%s_validate_current_token' % self.marketplace)()
        return self.env['mp.token']
