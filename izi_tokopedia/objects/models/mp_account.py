# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models
from odoo.addons.izi_tokopedia.objects.utils.tokopedia.account import TokopediaAccount


class MarketplaceAccount(models.Model):
    _inherit = 'mp.account'

    marketplace = fields.Selection(selection_add=[('tokopedia', 'Tokopedia')])
    tp_client_id = fields.Char(string="Client ID", required_if_marketplace="tokopedia")
    tp_client_secret = fields.Char(string="Client Secret", required_if_marketplace="tokopedia")

    @api.multi
    def tokopedia_authenticate(self):
        mp_token_obj = self.env['mp.token']

        self.ensure_one()
        tp_account = TokopediaAccount(self.tp_client_id, self.tp_client_secret)
        raw_token = tp_account.authenticate()
        mp_token_obj.create_token(self, raw_token)
        self.write({'state': 'authenticated'})
