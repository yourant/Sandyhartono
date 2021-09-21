# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
from odoo import api, fields, models
from odoo.addons.izi_blibli.objects.utils.blibli.account import BlibliAccount
from odoo.addons.izi_blibli.objects.utils.blibli.logistic import BlibliLogistic


class MarketplaceAccount(models.Model):
    _inherit = 'mp.account'

    READONLY_STATES = {
        'authenticated': [('readonly', True)],
        'authenticating': [('readonly', False)],
    }

    marketplace = fields.Selection(selection_add=[('blibli', 'Blibli')])
    bli_usermail = fields.Char(string='User Email', required_if_marketplace="blibli", states=READONLY_STATES)
    bli_shop_name = fields.Char(string='Shop Name', required_if_marketplace="blibli", states=READONLY_STATES)
    bli_shop_code = fields.Char(string='Shop Code', required_if_marketplace="blibli", states=READONLY_STATES)
    bli_seller_key = fields.Char(string='Seller Key', required_if_marketplace="blibli", states=READONLY_STATES)
    bli_client_id = fields.Char('Client ID', required_if_marketplace="blibli", states=READONLY_STATES)
    bli_client_secret = fields.Char('Client Secret', required_if_marketplace="blibli", states=READONLY_STATES)
    bli_store_id = fields.Integer('Store ID', states=READONLY_STATES)

    @api.model
    def blibli_get_account(self):
        credentials = {
            'usermail': self.bli_usermail,
            'shop_name': self.bli_shop_name,
            'shop_code': self.bli_shop_code,
            'seller_key': self.bli_seller_key,
            'store_id': 10001,
            'client_id': self.bli_client_id,
            'client_secret': self.bli_client_secret
        }
        bli_account = BlibliAccount(**credentials)
        return bli_account

    @api.multi
    def blibli_authenticate(self):
        bli_account = self.blibli_get_account()
        result = bli_account.authenticate()
        if result:
            self.write({'state': 'authenticated'})

    @api.multi
    def blibli_get_logistic(self):
        mp_blibli_logistic_obj = self.env['mp.blibli.logistic']

        self.ensure_one()
        params = {}
        bli_account = self.blibli_get_account(**params)
        bli_logistic = BlibliLogistic(bli_account, sanitizers=mp_blibli_logistic_obj.get_sanitizers(self.marketplace))
        bli_data_raw, bli_data_sanitized = bli_logistic.get_logsitic_list()
        mp_blibli_logistic_obj.with_context({'mp_account_id': self.id}).create_records(
            bli_data_raw, bli_data_sanitized, isinstance(bli_data_sanitized, list))

    @api.multi
    def blibli_get_dependencies(self):
        self.ensure_one()
        self.blibli_get_logistic()
