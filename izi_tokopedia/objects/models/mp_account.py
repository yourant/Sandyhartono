# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models
from odoo.addons.izi_tokopedia.objects.utils.tokopedia.account import TokopediaAccount


class MarketplaceAccount(models.Model):
    _inherit = 'mp.account'

    READONLY_STATES = {
        'authenticated': [('readonly', True)],
        'authenticating': [('readonly', False)],
    }

    marketplace = fields.Selection(selection_add=[('tokopedia', 'Tokopedia')])
    tp_client_id = fields.Char(string="Client ID", required_if_marketplace="tokopedia", states=READONLY_STATES)
    tp_client_secret = fields.Char(string="Client Secret", required_if_marketplace="tokopedia", states=READONLY_STATES)
    tp_fs_id = fields.Char(string="Fulfillment Service ID", required_if_marketplace="tokopedia", states=READONLY_STATES)

    @api.model
    def tokopedia_get_account(self):
        credentials = {
            'client_id': self.tp_client_id,
            'client_secret': self.tp_client_secret,
            'fs_id': int(self.tp_fs_id),
            'access_token': self.access_token,
            'expired_date': fields.Datetime.from_string(self.access_token_expired_date),
            'token_type': self.mp_token_id.tp_token_type
        }
        tp_account = TokopediaAccount(**credentials)
        return tp_account

    @api.multi
    def tokopedia_authenticate(self):
        mp_token_obj = self.env['mp.token']

        self.ensure_one()
        tp_account = self.tokopedia_get_account()
        raw_token = tp_account.authenticate()
        mp_token_obj.create_token(self, raw_token)
        self.write({'state': 'authenticated'})
