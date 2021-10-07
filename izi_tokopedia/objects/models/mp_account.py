# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import json

from Cryptodome.PublicKey import RSA
from odoo import api, fields, models
from odoo.exceptions import UserError
from requests import HTTPError

from odoo.addons.izi_marketplace.objects.utils.tools import mp, json_digger
from odoo.addons.izi_tokopedia.objects.utils.tokopedia.account import TokopediaAccount
from odoo.addons.izi_tokopedia.objects.utils.tokopedia.encryption import TokopediaEncryption
from odoo.addons.izi_tokopedia.objects.utils.tokopedia.exception import TokopediaAPIError
from odoo.addons.izi_tokopedia.objects.utils.tokopedia.logistic import TokopediaLogistic
from odoo.addons.izi_tokopedia.objects.utils.tokopedia.order import TokopediaOrder
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
    tp_private_key_file = fields.Binary(string="Secret Key File")
    tp_private_key_file_name = fields.Char(string="Secret Key File Name")
    tp_private_key = fields.Char(string="Secret Key", compute="_compute_tp_private_key")
    tp_public_key_file = fields.Binary(string="Public Key File")
    tp_public_key_file_name = fields.Char(string="Public Key File Name")
    tp_public_key = fields.Char(string="Public Key", compute="_compute_tp_public_key")

    @api.onchange('marketplace')
    def onchange_marketplace_tokopedia(self):
        if self.marketplace == 'tokopedia':
            self.partner_id = self.env.ref('izi_tokopedia.res_partner_tokopedia', raise_if_not_found=False).id

    @api.multi
    def _compute_tp_private_key(self):
        self.ensure_one()
        if self.tp_private_key_file:
            self.tp_private_key = self.with_context({'bin_size': False}).tp_private_key_file

    @api.multi
    def _compute_tp_public_key(self):
        self.ensure_one()
        if self.tp_public_key_file:
            self.tp_public_key = self.with_context({'bin_size': False}).tp_public_key_file

    @api.multi
    def generate_rsa_key(self):
        _notify = self.env['mp.base']._notify

        self.ensure_one()

        key = RSA.generate(2048)
        self.tp_private_key_file = key.export_key()
        self.tp_public_key_file = key.publickey().export_key()

        _notify('info', "New RSA key generated successfully, don't forget to register it to Tokopedia!")

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
    def tokopedia_register_public_key(self):
        _notify = self.env['mp.base']._notify

        self.ensure_one()

        tp_account = self.tokopedia_get_account()
        tp_encryption = TokopediaEncryption(tp_account)
        try:
            response = tp_encryption.register_public_key(self.tp_public_key_file)
            if response.status_code == 200:
                _notify('info', 'Public key registered successfully!')
        except TokopediaAPIError as tp_error:
            raise UserError(tp_error.args)
        except HTTPError as http_error:
            raise UserError(http_error.args)

    @api.multi
    def tokopedia_get_shop(self):
        mp_account_ctx = self.generate_context()
        _notify = self.env['mp.base']._notify
        mp_tokopedia_shop_obj = self.env['mp.tokopedia.shop'].with_context(mp_account_ctx)

        self.ensure_one()

        tp_account = self.tokopedia_get_account()
        tp_shop = TokopediaShop(tp_account, sanitizers=mp_tokopedia_shop_obj.get_sanitizers(self.marketplace))
        _notify('info', 'Importing shop from {} is started... Please wait!'.format(self.marketplace.upper()),
                notif_sticky=True)
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
    def tokopedia_get_logistics(self):
        mp_account_ctx = self.generate_context()
        _notify = self.env['mp.base']._notify
        mp_tokopedia_logistic_obj = self.env['mp.tokopedia.logistic'].with_context(mp_account_ctx)

        self.ensure_one()

        tp_account = self.tokopedia_get_account()
        tp_logistic = TokopediaLogistic(tp_account, api_version="v2",
                                        sanitizers=mp_tokopedia_logistic_obj.get_sanitizers(self.marketplace))
        _notify('info', 'Importing logistic from {} is started... Please wait!'.format(self.marketplace.upper()),
                notif_sticky=True)
        tp_data_raw, tp_data_sanitized = tp_logistic.get_logistic_info(shop_id=self.tp_shop_id.shop_id)
        check_existing_records_params = {
            'identifier_field': 'shipper_id',
            'raw_data': tp_data_raw,
            'mp_data': tp_data_sanitized,
            'multi': isinstance(tp_data_sanitized, list)
        }
        check_existing_records = mp_tokopedia_logistic_obj.check_existing_records(**check_existing_records_params)
        mp_tokopedia_logistic_obj.handle_result_check_existing_records(check_existing_records)

    @api.multi
    def tokopedia_get_active_logistics(self):
        mp_account_ctx = self.generate_context()
        self.ensure_one()
        self.tp_shop_id.with_context(mp_account_ctx).get_active_logistics()

    @api.multi
    def tokopedia_get_dependencies(self):
        self.ensure_one()
        self.tokopedia_get_shop()
        self.tokopedia_get_logistics()
        self.tokopedia_get_active_logistics()
        return {
            'type': 'ir.actions.client',
            'tag': 'close_notifications',
            'params': {
                'force_show_number': 1
            }
        }

    @api.multi
    def tokopedia_get_mp_product(self):
        _notify = self.env['mp.base']._notify
        mp_product_obj = self.env['mp.product']

        self.ensure_one()

        mp_account_ctx = self.generate_context()

        tp_account = self.tokopedia_get_account()
        tp_product = TokopediaProduct(tp_account, sanitizers=mp_product_obj.get_sanitizers(self.marketplace))
        _notify('info', 'Importing product from {} is started... Please wait!'.format(self.marketplace.upper()),
                notif_sticky=True)
        tp_data_raw, tp_data_sanitized = tp_product.get_product_info(shop_id=self.tp_shop_id.shop_id,
                                                                     limit=mp_account_ctx.get('product_limit'))
        check_existing_records_params = {
            'identifier_field': 'tp_product_id',
            'raw_data': tp_data_raw,
            'mp_data': tp_data_sanitized,
            'multi': isinstance(tp_data_sanitized, list)
        }
        check_existing_records = mp_product_obj.with_context(mp_account_ctx).check_existing_records(
            **check_existing_records_params)
        mp_product_obj.with_context(mp_account_ctx).handle_result_check_existing_records(check_existing_records)

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
        tp_variant_ids = []
        for mp_product in mp_products:
            mp_product_raw = json.loads(mp_product.raw, strict=False)
            tp_variant_ids.extend(json_digger(mp_product_raw, 'variant/childrenID'))
        tp_data_raw, tp_data_sanitized = tp_product_variant.get_product_info(product_id=tp_variant_ids)
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
        return {
            'type': 'ir.actions.client',
            'tag': 'close_notifications'
        }

    @api.multi
    @mp.tokopedia.capture_error
    def tokopedia_get_sale_order(self, from_date, to_date):
        mp_account_ctx = self.generate_context()
        order_obj = self.env['sale.order'].with_context(mp_account_ctx)
        _notify = self.env['mp.base']._notify

        self.ensure_one()

        self.tokopedia_register_public_key()

        tp_account = self.tokopedia_get_account()
        tp_order = TokopediaOrder(tp_account, api_version="v2")
        _notify('info', 'Importing order from {} is started... Please wait!'.format(self.marketplace.upper()),
                notif_sticky=True)
        tp_data_raw = tp_order.get_order_list(from_date=from_date, to_date=to_date, shop_id=self.tp_shop_id.shop_id,
                                              limit=mp_account_ctx.get('order_limit'))
        tp_data_raw, tp_data_sanitized = order_obj._prepare_mapping_raw_data(raw_data=tp_data_raw,
                                                                             endpoint_key='sanitize_decrypt')
        check_existing_records_params = {
            'identifier_field': 'tp_order_id',
            'raw_data': tp_data_raw,
            'mp_data': tp_data_sanitized,
            'multi': isinstance(tp_data_sanitized, list)
        }
        check_existing_records = order_obj.with_context(mp_account_ctx).check_existing_records(
            **check_existing_records_params)
        order_obj.with_context(mp_account_ctx).handle_result_check_existing_records(check_existing_records)

    @api.multi
    def tokopedia_get_orders(self, from_date, to_date):
        self.ensure_one()
        self.tokopedia_get_sale_order(from_date, to_date)
