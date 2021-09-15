# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models
from odoo.addons.izi_shopee.objects.utils.shopee.account import ShopeeAccount



class MarketplaceAccount(models.Model):
    _inherit = 'mp.account'

    READONLY_STATES = {
        'authenticated': [('readonly', True)],
        'authenticating': [('readonly', False)],
    }

    marketplace = fields.Selection(selection_add=[('shopee', 'Shopee')])
    sp_partner_id = fields.Char(string="Partner ID", required_if_marketplace="shopee", states=READONLY_STATES)
    sp_partner_key = fields.Char(string="Partner Key", required_if_marketplace="shopee", states=READONLY_STATES)

    @api.multi
    def shopee_authenticate(self):
        mp_token_obj = self.env['mp.token']

        self.ensure_one()
        sp_account = ShopeeAccount(self.sp_partner_id, self.sp_partner_key)
        raw_token = sp_account.get_auth_url_v2()
        self.write({'state': 'authenticated'})
