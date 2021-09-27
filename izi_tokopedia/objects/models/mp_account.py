# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import json

from odoo import api, fields, models

from odoo.addons.izi_marketplace.objects.utils.tools import json_digger
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
    def tokopedia_get_account(self, **kwargs):
        credentials = dict({
            'client_id': self.tp_client_id,
            'client_secret': self.tp_client_secret,
            'fs_id': int(self.tp_fs_id),
            'access_token': self.access_token,
            'expired_date': fields.Datetime.from_string(self.access_token_expired_date),
            'token_type': self.mp_token_id.tp_token_type
        }, **kwargs)
        tp_account = TokopediaAccount(**credentials)
        return tp_account

    @api.multi
    def tokopedia_authenticate(self):
        mp_token_obj = self.env['mp.token']

        self.ensure_one()
        tp_account = self.tokopedia_get_account()
        raw_token = tp_account.authenticate()
        mp_token_obj.create_token(self, raw_token)
        self.write({
            'state': 'authenticated',
            'auth_message': 'Congratulations, you have been successfully authenticated!'
        })

    @api.multi
    def tokopedia_get_shop(self):
        mp_account_ctx = self.generate_context()
        mp_tokopedia_shop_obj = self.env['mp.tokopedia.shop'].with_context(mp_account_ctx)

        self.ensure_one()

        tp_account = self.tokopedia_get_account()
        tp_shop = TokopediaShop(tp_account, sanitizers=mp_tokopedia_shop_obj.get_sanitizers(self.marketplace))
        tp_data_raw, tp_data_sanitized = tp_shop.get_shop_info()
        check_existing_records_params = {
            'identifier_field': 'shop_id',
            'raw_data': tp_data_raw,
            'mp_data': tp_data_raw,
            'multi': isinstance(tp_data_raw, list)
        }
        check_existing_records = mp_tokopedia_shop_obj.check_existing_records(**check_existing_records_params)
        mp_tokopedia_shop_obj.handle_result_check_existing_records(check_existing_records)

    @api.multi
    def tokopedia_get_dependencies(self):
        self.ensure_one()
        self.tokopedia_get_shop()

    @api.multi
    def tokopedia_get_mp_product(self):
        mp_product_obj = self.env['mp.product']

        self.ensure_one()

        mp_account_ctx = self.generate_context()

        tp_account = self.tokopedia_get_account()
        tp_product = TokopediaProduct(tp_account, sanitizers=mp_product_obj.get_sanitizers(self.marketplace))
        tp_data_raw, tp_data_sanitized = tp_product.get_product_info(shop_id=self.tp_shop_id.shop_id, limit=10)
        check_existing_records = mp_product_obj.with_context(mp_account_ctx). \
            check_existing_records('tp_product_id', tp_data_raw, tp_data_sanitized, isinstance(tp_data_sanitized, list))
        if check_existing_records['need_update_records']:
            mp_product_obj.with_context({'mp_account_id': self.id}).update_records(
                check_existing_records['need_update_records'])

        if check_existing_records['need_create_records']:
            tp_data_raw, tp_data_sanitized = mp_product_obj._prepare_create_records(
                check_existing_records['need_create_records'])
            mp_product_obj.with_context({'mp_account_id': self.id}).create_records(tp_data_raw, tp_data_sanitized,
                                                                                   isinstance(tp_data_sanitized, list))

        if check_existing_records['need_skip_records']:
            mp_product_obj.log_skip(self.marketplace, check_existing_records['need_skip_records'])

    @api.multi
    def tokopedia_get_mp_product_variant(self):
        mp_product_obj = self.env['mp.product']
        mp_product_variant_obj = self.env['mp.product.variant']
        self.ensure_one()

        mp_account_ctx = self.generate_context()

        tp_account = self.tokopedia_get_account()
        tp_product_variant = TokopediaProduct(tp_account,
                                              sanitizers=mp_product_variant_obj.get_sanitizers(self.marketplace))

        mp_products = mp_product_obj.search([('tp_has_variant', '=', True)])
        for mp_product in mp_products:
            mp_product_raw = json.loads(mp_product.raw, strict=False)
            tp_variant_ids = json_digger(mp_product_raw, 'variant/childrenID')
            for tp_variant_id in tp_variant_ids:
                tp_data_raw, tp_data_sanitized = tp_product_variant.get_product_info(product_id=tp_variant_id)
                check_existing_records_params = {
                    'identifier_field': 'tp_variant_id',
                    'raw_data': tp_data_raw,
                    'mp_data': tp_data_sanitized,
                    'multi': isinstance(tp_data_sanitized, list)
                }
                check_existing_records = mp_product_variant_obj.with_context(mp_account_ctx).check_existing_records(
                    **check_existing_records_params)
                mp_product_variant_obj.with_context(mp_account_ctx).handle_result_check_existing_records(
                    check_existing_records)

    @api.multi
    def tokopedia_get_products(self):
        self.ensure_one()
        self.tokopedia_get_mp_product()
        self.tokopedia_get_mp_product_variant()
