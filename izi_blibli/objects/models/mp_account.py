# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import uuid
import requests
from requests.auth import HTTPBasicAuth
from odoo import api, fields, models
from odoo.addons.izi_blibli.objects.utils.blibli.account import BlibliAccount


class MarketplaceAccount(models.Model):
    _inherit = 'mp.account'

    READONLY_STATES = {
        'authenticated': [('readonly', True)],
        'authenticating': [('readonly', False)],
    }

    marketplace = fields.Selection(selection_add=[('blibli', 'Blibli')])
    bli_usermail =  fields.Char(string='User Email', required_if_marketplace="blibli", states=READONLY_STATES)
    bli_shop_name = fields.Char(string='Shop Name', required_if_marketplace="blibli", states=READONLY_STATES)
    bli_shop_code = fields.Char(string='Shop Code', required_if_marketplace="blibli", states=READONLY_STATES)
    bli_seller_key = fields.Char(string='Seller Key', required_if_marketplace="blibli", states=READONLY_STATES)
    bli_client_id = fields.Char('Client ID', required_if_marketplace="blibli", states=READONLY_STATES)
    bli_client_secret = fields.Char('Client Secret', required_if_marketplace="blibli", states=READONLY_STATES)
    bli_store_id = fields.Integer('Store ID', states=READONLY_STATES)

    api.model
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
        







        
