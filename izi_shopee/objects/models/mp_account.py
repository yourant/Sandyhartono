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


    def shopee_authenticate(self):

        self.ensure_one()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        sp_account = ShopeeAccount(self.sp_partner_id, self.sp_partner_key, base_url, self.id)
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': sp_account.get_auth_url_v2()
        }
       
    @api.multi
    def get_token_shopee(self, **kwargs):
        mp_token_obj = self.env['mp.token']

        code = kwargs.get('code')
        shop_id = kwargs.get('shop_id')
        refresh_token = kwargs.get('refresh_token')
        last_code_id = kwargs.get('last_code_id')

        sp_account = ShopeeAccount(partner_id=self.sp_partner_id, partner_key=self.sp_partner_key, shop_id=shop_id, code=code, refresh_token=refresh_token)
        raw_token = sp_account.get_token()
        mp_token_obj.create_token(self, raw_token)
        self.write({'state': 'authenticated'})
