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

    @api.model
    def shopee_get_account(self, **kwargs):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        credentials = {
            'partner_id': self.sp_partner_id,
            'partner_key': self.sp_partner_key,
            'mp_id': self.id,
            'base_url': base_url,
            'code': kwargs.get('code', None),
            'refresh_token': kwargs.get('refresh_token', None),
            'shop_id': kwargs.get('shop_id', None)
        }
        sp_account = ShopeeAccount(**credentials)
        return sp_account

    def shopee_authenticate(self):
        self.ensure_one()
        sp_account = self.shopee_get_account()
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': sp_account.get_auth_url_v2()
        }

    def shopee_renew_token(self):
        self.ensure_one()
        current_token = False
        if self.mp_token_ids:
            current_token = self.mp_token_ids.sorted('expired_date', reverse=True)[0]
        if current_token:
            if current_token.refresh_token:
                self.shopee_get_token(**{'refresh_token': current_token.refresh_token,
                                         'shop_id': current_token.sp_shop_id})

    @api.multi
    def shopee_get_token(self, **kwargs):
        mp_token_obj = self.env['mp.token']
        sp_account = self.shopee_get_account(**kwargs)
        shop_id = kwargs.get('shop_id', None)
        raw_token = sp_account.get_token()
        if shop_id:
            raw_token['shop_id'] = shop_id
        mp_token_obj.create_token(self, raw_token)
        self.write({'state': 'authenticated'})
