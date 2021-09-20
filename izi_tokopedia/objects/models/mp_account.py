# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models
from odoo.addons.izi_tokopedia.objects.utils.tokopedia.account import TokopediaAccount
from odoo.addons.izi_tokopedia.objects.utils.tokopedia.product import TokopediaProduct
from odoo.addons.izi_tokopedia.objects.utils.tokopedia.shop import TokopediaShop


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
    tp_shop_ids = fields.One2many(comodel_name="mp.tokopedia.shop", inverse_name="mp_account_id", string="Shop(s)")
    tp_shop_id = fields.Many2one(comodel_name="mp.tokopedia.shop", string="Current Shop")

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

    @api.multi
    def tokopedia_get_shop(self):
        mp_tokopedia_shop_obj = self.env['mp.tokopedia.shop']

        self.ensure_one()

        tp_account = self.tokopedia_get_account()
        tp_shop = TokopediaShop(tp_account)
        tp_data = tp_shop.get_shop_info()
        mp_tokopedia_shop_obj.with_context({'mp_account_id': self.id}).create_shop(tp_data, isinstance(tp_data, list))

    @api.multi
    def tokopedia_get_dependencies(self):
        self.ensure_one()
        self.tokopedia_get_shop()

    @api.multi
    def tokopedia_get_mp_product(self):
        mp_product_obj = self.env['mp.product']

        self.ensure_one()

        tp_account = self.tokopedia_get_account()
        tp_product = TokopediaProduct(tp_account, sanitizers=mp_product_obj.get_sanitizers(self.marketplace))
        tp_data_raw, tp_data_sanitized = tp_product.get_product_info(self.tp_shop_id.shop_id)
        mp_product_obj.with_context({'mp_account_id': self.id}).create_records(tp_data_raw, tp_data_sanitized,
                                                                               isinstance(tp_data_sanitized, list))

    @api.multi
    def tokopedia_get_products(self):
        self.ensure_one()
        self.tokopedia_get_mp_product()
