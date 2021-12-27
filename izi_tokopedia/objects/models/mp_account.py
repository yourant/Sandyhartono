# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import json
from datetime import datetime, timedelta
import io
import time

from Cryptodome.PublicKey import RSA
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models
from odoo.exceptions import UserError

from odoo.addons.izi_marketplace.objects.utils.tools import mp, json_digger
from odoo.addons.izi_tokopedia.objects.utils.tokopedia.account import TokopediaAccount
from odoo.addons.izi_tokopedia.objects.utils.tokopedia.encryption import TokopediaEncryption
from odoo.addons.izi_tokopedia.objects.utils.tokopedia.logistic import TokopediaLogistic
from odoo.addons.izi_tokopedia.objects.utils.tokopedia.order import TokopediaOrder
from odoo.addons.izi_tokopedia.objects.utils.tokopedia.product import TokopediaProduct
from odoo.addons.izi_tokopedia.objects.utils.tokopedia.shop import TokopediaShop
from odoo.addons.izi_tokopedia.objects.utils.tokopedia.webhook import TokopediaWebhook


class MarketplaceAccount(models.Model):
    _inherit = 'mp.account'
    _sql_constraints = [
        ('unique_tp_shop_url', 'UNIQUE(tp_shop_url)', 'This URL is already registered, please try another shop URL!')
    ]

    READONLY_STATES = {
        'authenticated': [('readonly', True)],
        'authenticating': [('readonly', False)],
    }

    # marketplace = fields.Selection(selection_add=[('tokopedia', 'Tokopedia')], ondelete={'tokopedia': 'cascade'})
    tp_client_id = fields.Char(string="Tokopedia Client ID",
                               required_if_marketplace="tokopedia", states=READONLY_STATES)
    tp_client_secret = fields.Char(string="Tokopedia Client Secret",
                                   required_if_marketplace="tokopedia", states=READONLY_STATES)
    tp_fs_id = fields.Char(string="Fulfillment Service ID", required_if_marketplace="tokopedia", states=READONLY_STATES)
    tp_shop_url = fields.Char(string="Shop URL", required_if_marketplace="tokopedia", states=READONLY_STATES)
    tp_shop_id = fields.Many2one(comodel_name="mp.tokopedia.shop", string="Tokopedia Current Shop",
                                 readonly=True, ondelete='set null')
    tp_private_key_file = fields.Text(string="Secret Key File")
    # tp_private_key_file_name = fields.Char(string="Secret Key File Name")
    tp_private_key = fields.Char(string="Secret Key", compute="_compute_tp_private_key")
    tp_public_key_file = fields.Text(string="Public Key File")
    # tp_public_key_file_name = fields.Char(string="Public Key File Name")
    tp_public_key = fields.Char(string="Public Key", compute="_compute_tp_public_key")

    tp_webhook_secret = fields.Char(string='Tokopedia Webhook Secret')
    tp_is_webhook_order = fields.Boolean(string='Tokopedia Order Webhook', default=True)

    @api.onchange('marketplace')
    def onchange_marketplace_tokopedia(self):
        if self.marketplace == 'tokopedia':
            self.partner_id = self.env.ref('izi_tokopedia.res_partner_tokopedia', raise_if_not_found=False).id

    # @api.multi
    def _compute_tp_private_key(self):
        self.tp_private_key = None
        for rec in self.filtered(lambda r: (r.marketplace == 'tokopedia') and r.tp_private_key_file):
            rec.tp_private_key = rec.with_context({'bin_size': False}).tp_private_key_file

    # @api.multi
    def _compute_tp_public_key(self):
        self.tp_public_key = None
        for rec in self.filtered(lambda r: (r.marketplace == 'tokopedia') and r.tp_public_key_file):
            rec.tp_public_key = rec.with_context({'bin_size': False}).tp_public_key_file

    # @api.multi
    def generate_rsa_key(self):
        _notify = self.env['mp.base']._notify

        self.ensure_one()
        key = RSA.generate(2048)
        private_key, public_key = key.export_key().decode('utf-8'), key.publickey().export_key().decode('utf-8')
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

    # @api.multi
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

    # @api.multi
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

    # @api.multi
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

    # @api.multi
    @mp.tokopedia.capture_error
    def tokopedia_register_webhooks(self):
        _logger = self.env['mp.base']._logger
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        self.ensure_one()

        if not self.tp_webhook_secret:
            raise UserError('Webhook secret must be filled')

        webhook_args = {
            'webhook_secret': self.tp_webhook_secret
        }

        if self.fields_get().get('tp_is_webhook_order', False):
            if self.tp_is_webhook_order:
                webhook_args.update({
                    'order_notification_url': base_url+'/api/izi/webhook/tp/order/notification',
                    'order_request_cancellation_url': base_url+'/api/izi/webhook/tp/order/request/cancel',
                    'order_status_url': base_url+'/api/izi/webhook/tp/order/status'
                })
        if len(webhook_args) > 1:
            tp_account = self.tokopedia_get_account()
            tp_webhook = TokopediaWebhook(tp_account)
            response = tp_webhook.register_webhook(**webhook_args)
            if response.status_code == 200:
                notif_msg = "Register webhook is successfully.."
                self.write({
                    'mp_webhook_state': 'registered'
                })
            else:
                notif_msg = "Register webhook is failure.."
                self.write({
                    'mp_webhook_state': 'no_register'
                })
            _logger(self.marketplace, notif_msg, notify=True, notif_sticky=False)
        else:
            raise UserError('Select at least 1 feature for register webhook')

    @mp.tokopedia.capture_error
    def tokopedia_unregister_webhooks(self):
        _logger = self.env['mp.base']._logger
        notif_msg = "Unregister webhook is Success.."
        self.write({
            'mp_webhook_state': 'no_register'
        })
        _logger(self.marketplace, notif_msg, notify=True, notif_sticky=False)

    # @api.multi
    @mp.tokopedia.capture_error
    def tokopedia_get_shop(self):
        mp_account_ctx = self.generate_context()
        _notify = self.env['mp.base']._notify
        mp_tokopedia_shop_obj = self.env['mp.tokopedia.shop'].with_context(mp_account_ctx)

        self.ensure_one()

        tp_account = self.tokopedia_get_account()
        tp_shop = TokopediaShop(tp_account, sanitizers=mp_tokopedia_shop_obj.get_sanitizers(self.marketplace))
        _notify('info', 'Importing shop from {} is started... Please wait!'.format(self.marketplace.upper()),
                notif_sticky=False)
        tp_data_raw, tp_data_sanitized = tp_shop.get_shop_info()
        check_existing_records_params = {
            'identifier_field': 'shop_id',
            'raw_data': tp_data_raw,
            'mp_data': tp_data_raw,
            'multi': isinstance(tp_data_raw, list)
        }
        check_existing_records = mp_tokopedia_shop_obj.check_existing_records(**check_existing_records_params)
        mp_tokopedia_shop_obj.handle_result_check_existing_records(check_existing_records)

    # @api.multi
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
                notif_sticky=False)
        tp_data_raw, tp_data_sanitized = tp_logistic.get_logistic_info(shop_id=self.tp_shop_id.shop_id)
        check_existing_records_params = {
            'identifier_field': 'shipper_id',
            'raw_data': tp_data_raw,
            'mp_data': tp_data_sanitized,
            'multi': isinstance(tp_data_sanitized, list)
        }
        check_existing_records = mp_tokopedia_logistic_obj.check_existing_records(**check_existing_records_params)
        mp_tokopedia_logistic_obj.handle_result_check_existing_records(check_existing_records)

    # @api.multi
    @mp.tokopedia.capture_error
    def tokopedia_get_active_logistics(self):
        mp_account_ctx = self.generate_context()
        self.ensure_one()
        self.tp_shop_id.with_context(mp_account_ctx).get_active_logistics()

    # @api.multi
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

    # @api.multi
    @mp.tokopedia.capture_error
    def tokopedia_get_mp_product(self):
        _notify = self.env['mp.base']._notify
        mp_product_obj = self.env['mp.product']

        self.ensure_one()

        mp_account_ctx = self.generate_context()

        tp_account = self.tokopedia_get_account()
        tp_product = TokopediaProduct(tp_account, sanitizers=mp_product_obj.get_sanitizers(self.marketplace))
        _notify('info', 'Importing product from {} is started... Please wait!'.format(self.marketplace.upper()),
                notif_sticky=False)
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

    # @api.multi
    @mp.tokopedia.capture_error
    def tokopedia_get_mp_product_variant(self):
        mp_product_obj = self.env['mp.product']
        mp_product_variant_obj = self.env['mp.product.variant']
        self.ensure_one()

        mp_account_ctx = self.generate_context()

        tp_account = self.tokopedia_get_account()
        tp_product_variant = TokopediaProduct(tp_account,
                                              sanitizers=mp_product_variant_obj.get_sanitizers(self.marketplace))

        mp_products = mp_product_obj.search([('tp_has_variant', '=', True), ('mp_account_id', '=', self.id)])
        tp_data_raws, tp_data_sanitizeds = [], []
        tp_variant_ids = []
        for mp_product in mp_products:
            variant_need_to_remove = []
            mp_product_raw = json.loads(mp_product.raw, strict=False)
            tp_variant_ids.extend(json_digger(mp_product_raw, 'variant/childrenID'))
            mp_variant_exid_list = json_digger(mp_product_raw, 'variant/childrenID')

            for variant_obj in mp_product.mp_product_variant_ids:
                if int(variant_obj.tp_variant_id) not in mp_variant_exid_list:
                    variant_need_to_remove.append(variant_obj.tp_variant_id)

            mp_product.mp_product_variant_ids.filtered(lambda r: r.tp_variant_id in variant_need_to_remove).unlink()

        tp_variant_ids_splited = mp_product_variant_obj.create_chunks(tp_variant_ids, 500)
        for tp_variant_ids in tp_variant_ids_splited:
            tp_data_raw, tp_data_sanitized = tp_product_variant.get_product_info(product_id=tp_variant_ids)
            tp_data_raws.extend(tp_data_raw)
            tp_data_sanitizeds.extend(tp_data_sanitized)

        check_existing_records_params = {
            'identifier_field': 'tp_variant_id',
            'raw_data': tp_data_raws,
            'mp_data': tp_data_sanitizeds,
            'multi': isinstance(tp_data_sanitizeds, list)
        }
        check_existing_records = mp_product_variant_obj.with_context(mp_account_ctx).check_existing_records(
            **check_existing_records_params)
        mp_product_variant_obj.with_context(mp_account_ctx).handle_result_check_existing_records(
            check_existing_records)

    # @api.multi
    def tokopedia_get_products(self):
        self.ensure_one()
        self.tokopedia_get_mp_product()
        self.tokopedia_get_mp_product_variant()
        return {
            'type': 'ir.actions.client',
            'tag': 'close_notifications'
        }

    # @api.multi
    @mp.tokopedia.capture_error
    def tokopedia_get_sale_order(self, **kwargs):
        mp_account_ctx = self.generate_context()
        order_obj = self.env['sale.order'].with_context(dict(mp_account_ctx, **self._context.copy()))
        _notify = self.env['mp.base']._notify
        _logger = self.env['mp.base']._logger
        datetime_convert_tz = self.env['mp.base'].datetime_convert_tz

        self.ensure_one()

        self.tokopedia_register_public_key()

        tp_account = self.tokopedia_get_account()
        tp_order = TokopediaOrder(tp_account, api_version="v2")
        _notify('info', 'Importing order from {} is started... Please wait!'.format(self.marketplace.upper()),
                notif_sticky=False)

        skipped = 0
        force_update_ids = []
        params, tp_data_detail_orders = {}, []
        tp_data_raws, tp_data_sanitizeds = [], []
        if kwargs.get('params') == 'by_date_range':
            tp_orders_by_mpexid = {}
            tp_orders = order_obj.search([('mp_account_id', '=', self.id)])
            for rec_tp_order in tp_orders:
                tp_orders_by_mpexid[rec_tp_order.tp_order_id] = rec_tp_order
            params.update({
                'from_date': kwargs.get('from_date'),
                'to_date': kwargs.get('to_date'),
                'shop_id': self.tp_shop_id.shop_id,
                'limit': mp_account_ctx.get('order_limit')
            })
            tp_data_orders = tp_order.get_order_list(**params)
            for index, tp_data_order in enumerate(tp_data_orders):
                tp_invoice_number = tp_data_order.get('invoice_ref_num')
                tp_order_id = tp_data_order.get('order_id')
                if tp_order_id in tp_orders_by_mpexid:
                    existing_order = tp_orders_by_mpexid[tp_order_id]
                    mp_status_changed = existing_order.tp_order_status != str(tp_data_order['order_status'])
                else:
                    existing_order = False
                    mp_status_changed = False
                # If no existing order OR mp status changed on existing order, then fetch new detail order
                no_existing_order = not existing_order
                if no_existing_order or mp_status_changed or mp_account_ctx.get('force_update'):
                    tp_status_cancel = ['0', '2', '3', '4', '5', '10', '15', '690', '691', '695', '698', '699']
                    if str(tp_data_order['order_status']) in tp_status_cancel and no_existing_order:
                        if not self.get_cancelled_orders:
                            skipped += 1
                            continue
                    if existing_order:
                        force_update_ids.append(existing_order.id)
                    notif_msg = "(%s/%d) Getting order detail of %s... Please wait!" % (
                        str(index + 1), len(tp_data_orders), tp_invoice_number
                    )
                    _logger(self.marketplace, notif_msg, notify=True, notif_sticky=False)
                    time.sleep(0.02)
                    tp_data_detail_order = tp_order.get_order_detail(order_id=tp_order_id)
                    tp_data_detail_order.update({'order_summary': tp_data_order})
                    tp_data_detail_orders.append(tp_data_detail_order)
                    tp_data_raw, tp_data_sanitized = order_obj._prepare_mapping_raw_data(
                        raw_data=tp_data_detail_order, endpoint_key='sanitize_decrypt')
                    tp_data_raws.extend(tp_data_raw)
                    tp_data_sanitizeds.extend(tp_data_sanitized)
                else:
                    skipped += 1

            _logger(self.marketplace, 'Processed %s order(s) from %s of total orders imported!' % (
                len(tp_data_detail_orders), len(tp_data_orders)
            ), notify=True, notif_sticky=False)
        elif kwargs.get('params') == 'by_mp_invoice_number':
            mp_invoice_number = kwargs.get('mp_invoice_number', False)
            mp_order_id = kwargs.get('mp_order_id', False)
            params.update({'invoice_num': mp_invoice_number, 'order_id': mp_order_id})
            tp_data_detail_order = tp_order.get_order_detail(**params)

            # Get order summary
            tp_order_create_time = datetime.fromisoformat(tp_data_detail_order['payment_date'][:-1].split('.')[0])
            tp_order_create_time_utc = datetime_convert_tz(tp_order_create_time, 'Asia/Jakarta', 'UTC')
            order_summary_params = {
                'from_date': tp_order_create_time_utc.replace(tzinfo=None) - relativedelta(minutes=1),
                'to_date': tp_order_create_time_utc.replace(tzinfo=None) + relativedelta(minutes=1),
                'shop_id': self.tp_shop_id.shop_id,
                'limit': mp_account_ctx.get('order_limit'),
            }
            tp_data_orders = tp_order.get_order_list(**order_summary_params)
            if mp_invoice_number:
                tp_data_order = list(filter(lambda o: o['invoice_ref_num'] == mp_invoice_number, tp_data_orders))[0]
            elif mp_order_id:
                tp_data_order = list(filter(lambda o: o['order_id'] == mp_order_id, tp_data_orders))[0]
            tp_data_detail_order.update({'order_summary': tp_data_order})

            tp_data_raw, tp_data_sanitized = order_obj._prepare_mapping_raw_data(
                raw_data=tp_data_detail_order, endpoint_key='sanitize_decrypt')
            tp_data_raws.extend(tp_data_raw)
            tp_data_sanitizeds.extend(tp_data_sanitized)

            _logger(self.marketplace, 'Processed order %s!' %
                    tp_data_order.get('invoice_ref_num'), notify=True, notif_sticky=False)

        if force_update_ids:
            order_obj = order_obj.with_context(dict(order_obj._context.copy(), **{
                'force_update_ids': force_update_ids
            }))

        if tp_data_raws:
            check_existing_records_params = {
                'identifier_field': 'tp_order_id',
                'raw_data': tp_data_raws,
                'mp_data': tp_data_sanitizeds,
                'multi': isinstance(tp_data_sanitizeds, list)
            }
            check_existing_records = order_obj.check_existing_records(**check_existing_records_params)
            if kwargs.get('skip_create', False):
                check_existing_records.pop('need_create_records')
            order_obj.handle_result_check_existing_records(check_existing_records)
        else:
            _logger(self.marketplace, 'There is no update, skipped %s order(s)!' % skipped, notify=True,
                    notif_sticky=False)

    # @api.multi
    def tokopedia_get_orders(self, **kwargs):
        rec = self
        if kwargs.get('id', False):
            rec = self.browse(kwargs.get('id'))
        rec.ensure_one()
        time_range = kwargs.get('time_range', False)
        if time_range:
            if time_range == 'last_hour':
                from_time = datetime.now() - timedelta(hours=1)
                to_time = datetime.now()
            elif time_range == 'last_3_days':
                from_time = datetime.now() - timedelta(days=3)
                to_time = datetime.now()
            kwargs.update({
                'from_date': from_time,
                'to_date': to_time
            })
        rec.tokopedia_get_sale_order(**kwargs)
        return {
            'type': 'ir.actions.client',
            'tag': 'close_notifications'
        }
