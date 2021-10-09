# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import json

from Cryptodome.PublicKey import RSA
from odoo import api, fields, models

from odoo.addons.izi_marketplace.objects.utils.tools import mp, json_digger
from odoo.addons.izi_tokopedia.objects.utils.tokopedia.account import TokopediaAccount
from odoo.addons.izi_tokopedia.objects.utils.tokopedia.encryption import TokopediaEncryption
from odoo.addons.izi_tokopedia.objects.utils.tokopedia.logistic import TokopediaLogistic
from odoo.addons.izi_tokopedia.objects.utils.tokopedia.order import TokopediaOrder
from odoo.addons.izi_tokopedia.objects.utils.tokopedia.product import TokopediaProduct
from odoo.addons.izi_tokopedia.objects.utils.tokopedia.shop import TokopediaShop


class MarketplaceAccount(models.Model):
    _inherit = 'mp.account'
    _sql_constraints = [
        ('unique_tp_shop_url', 'UNIQUE(tp_shop_url)', 'This URL is already registered, please try another shop URL!')
    ]

    READONLY_STATES = {
        'authenticated': [('readonly', True)],
        'authenticating': [('readonly', False)],
    }

    marketplace = fields.Selection(selection_add=[('tokopedia', 'Tokopedia')])
    tp_client_id = fields.Char(string="Client ID", required_if_marketplace="tokopedia", states=READONLY_STATES)
    tp_client_secret = fields.Char(string="Client Secret", required_if_marketplace="tokopedia", states=READONLY_STATES)
    tp_fs_id = fields.Char(string="Fulfillment Service ID", required_if_marketplace="tokopedia", states=READONLY_STATES)
    tp_shop_url = fields.Char(string="Shop URL", required_if_marketplace="tokopedia", states=READONLY_STATES)
    tp_shop_id = fields.Many2one(comodel_name="mp.tokopedia.shop", string="Current Shop", readonly=True)
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
        private_key, public_key = key.export_key(), key.publickey().export_key()
        self.write({
            'tp_private_key_file': private_key,
            'tp_public_key_file': public_key
        })
        _notify('info', "New RSA key generated successfully!")
        if self._context.get('get_private_key'):
            return private_key
        if self._context.get('get_public_key'):
            return public_key
        if self._context.get('get_pair_key'):
            return private_key, public_key

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
    def tokopedia_upload_public_key(self):
        return {
            'name': 'Upload Key Pair',
            'view_mode': 'form',
            'res_model': 'wiz.upload_public_key',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {
                'default_mp_account_id': self.id,
            },
        }

    @api.multi
    @mp.tokopedia.capture_error
    def tokopedia_register_public_key(self):
        _notify = self.env['mp.base']._notify

        self.ensure_one()

        public_key = self.with_context({'bin_size': False}).tp_public_key_file
        if not public_key:
            public_key = self.with_context({'get_public_key': True}).generate_rsa_key()

        tp_account = self.tokopedia_get_account()
        tp_encryption = TokopediaEncryption(tp_account)
        response = tp_encryption.register_public_key(public_key)
        if response.status_code == 200:
            _notify('info', 'Public key registered successfully!')

    @api.multi
    @mp.tokopedia.capture_error
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
    @mp.tokopedia.capture_error
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
    @mp.tokopedia.capture_error
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
    @mp.tokopedia.capture_error
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
    @mp.tokopedia.capture_error
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
    def tokopedia_get_sale_order(self, **kwargs):
        mp_account_ctx = self.generate_context()
        order_obj = self.env['sale.order'].with_context(mp_account_ctx)
        _notify = self.env['mp.base']._notify
        _logger = self.env['mp.base']._logger

        self.ensure_one()

        self.tokopedia_register_public_key()

        tp_account = self.tokopedia_get_account()
        tp_order = TokopediaOrder(tp_account, api_version="v2")
        _notify('info', 'Importing order from {} is started... Please wait!'.format(self.marketplace.upper()),
                notif_sticky=True)

        params, tp_data_detail_orders = {}, []
        tp_data_raws, tp_data_sanitizeds = [], []
        if kwargs.get('params') == 'by_date_range':
            params.update({
                'from_date': kwargs.get('from_date'),
                'to_date': kwargs.get('to_date'),
                'shop_id': self.tp_shop_id.shop_id,
                'limit': mp_account_ctx.get('order_limit')
            })
            tp_data_orders = tp_order.get_order_list(**params)
            for tp_data_order in tp_data_orders:
                tp_invoice_number = tp_data_order.get('invoice_ref_num')
                tp_order_id = tp_data_order.get('order_id')
                existing_order = order_obj.search_mp_records('tokopedia', str(tp_order_id))

                # If no existing order OR mp status changed on existing order, then fetch new detail order
                if not existing_order.exists() or (existing_order.exists() and (
                        existing_order.mp_order_status != str(tp_data_order['order_status']))):
                    notif_msg = "(%s/%d) Getting order detail of %s... Please wait!" % (
                        str(len(tp_data_detail_orders) + 1), len(tp_data_orders), tp_invoice_number
                    )
                    _logger(self.marketplace, notif_msg, notify=True, notif_sticky=True)
                    tp_data_detail_order = tp_order.get_order_detail(order_id=tp_order_id)
                    tp_data_detail_orders.append(tp_data_detail_order)
                    tp_data_raw, tp_data_sanitized = order_obj._prepare_mapping_raw_data(
                        raw_data=tp_data_detail_order, endpoint_key='sanitize_decrypt')
                    tp_data_raws.extend(tp_data_raw)
                    tp_data_sanitizeds.extend(tp_data_sanitized)

            _logger(self.marketplace, 'Processed %s order(s) from %s of total orders imported!' % (
                len(tp_data_detail_orders), len(tp_data_orders)
            ), notify=True, notif_sticky=True)
        elif kwargs.get('params') == 'by_mp_invoice_number':
            mp_invoice_number = kwargs.get('mp_invoice_number')
            params.update({'invoice_num': mp_invoice_number})
            tp_data_detail_order = tp_order.get_order_detail(**params)
            tp_data_raw, tp_data_sanitized = order_obj._prepare_mapping_raw_data(
                raw_data=tp_data_detail_order, endpoint_key='sanitize_decrypt')
            tp_data_raws.extend(tp_data_raw)
            tp_data_sanitizeds.extend(tp_data_sanitized)

            _logger(self.marketplace, 'Processed order %s!' % mp_invoice_number, notify=True, notif_sticky=True)

        check_existing_records_params = {
            'identifier_field': 'tp_order_id',
            'raw_data': tp_data_raws,
            'mp_data': tp_data_sanitizeds,
            'multi': isinstance(tp_data_sanitizeds, list)
        }
        check_existing_records = order_obj.with_context(mp_account_ctx).check_existing_records(
            **check_existing_records_params)
        order_obj.with_context(mp_account_ctx).handle_result_check_existing_records(check_existing_records)

    @api.multi
    def tokopedia_get_orders(self, **kwargs):
        self.ensure_one()
        self.tokopedia_get_sale_order(**kwargs)
