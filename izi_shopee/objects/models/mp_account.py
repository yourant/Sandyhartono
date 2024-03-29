# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
from datetime import datetime, timedelta
import json

from odoo import api, fields, models

from odoo.exceptions import UserError

from odoo.addons.izi_marketplace.objects.utils.tools import mp
from odoo.addons.izi_shopee.objects.utils.shopee.account import ShopeeAccount
from odoo.addons.izi_shopee.objects.utils.shopee.logistic import ShopeeLogistic
from odoo.addons.izi_shopee.objects.utils.shopee.shop import ShopeeShop
from odoo.addons.izi_shopee.objects.utils.shopee.product import ShopeeProduct
from odoo.addons.izi_shopee.objects.utils.shopee.order import ShopeeOrder
from odoo.addons.izi_shopee.objects.utils.shopee.webhook import ShopeeWebhook


class MarketplaceAccount(models.Model):
    _inherit = 'mp.account'

    READONLY_STATES = {
        'authenticated': [('readonly', True)],
        'authenticating': [('readonly', False)],
    }

    # marketplace = fields.Selection(selection_add=[('shopee', 'Shopee')], ondelete={'shopee': 'cascade'})
    sp_partner_id = fields.Char(string="Partner ID", required_if_marketplace="shopee", states=READONLY_STATES)
    sp_partner_key = fields.Char(string="Partner Key", required_if_marketplace="shopee", states=READONLY_STATES)
    sp_shop_id = fields.Many2one(comodel_name="mp.shopee.shop", string="Shopee Current Shop")
    sp_coins_product_id = fields.Many2one(comodel_name="product.product",
                                          string="Default Shopee Coins Product",
                                          default=lambda self: self._get_default_sp_coins_product_id())
    sp_log_token_ids = fields.One2many(comodel_name='mp.shopee.log.token',
                                       inverse_name='mp_account_id', string='Shopee Log Token')
    sp_is_webhook_order = fields.Boolean(string='Shopee Order Webhook', default=False)

    @api.model
    def _get_default_sp_coins_product_id(self):
        sp_coins_product_tmpl = self.env.ref('izi_shopee.product_tmpl_shopee_coins', raise_if_not_found=False)
        if sp_coins_product_tmpl:
            return sp_coins_product_tmpl.product_variant_id.id
        return False

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
            'access_token': kwargs.get('access_token', None),
            'shop_id': kwargs.get('shop_id', self.mp_token_id.sp_shop_id)
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
        mp_shopee_log_token = self.env['mp.shopee.log.token']
        current_token = False
        if self.mp_token_ids:
            current_token = self.mp_token_ids.sorted('expired_date', reverse=True)[0]
        if current_token:
            if current_token.refresh_token:
                request_params = {
                    'refresh_token': current_token.refresh_token,
                    'shop_id': current_token.sp_shop_id
                }
                try:
                    self.shopee_get_token(**request_params)
                except Exception as e:
                    request_params.update({'partner_id': self.sp_partner_id})
                    mp_shopee_log_token.create_log_token(self, e.args[0], request_params, status='fail')
                    raise UserError(str(e.args[0]))

    # @api.multi
    def shopee_get_token(self, **kwargs):
        mp_token_obj = self.env['mp.token']
        mp_shopee_log_token = self.env['mp.shopee.log.token']

        sp_account = self.shopee_get_account(**kwargs)
        shop_id = kwargs.get('shop_id', None)
        raw_token, request_json = sp_account.get_token()
        if shop_id:
            raw_token['shop_id'] = shop_id
        mp_token = mp_token_obj.create_token(self, raw_token)
        mp_shopee_log_token.create_log_token(self, raw_token, request_json, status='success', mp_token=mp_token)
        time_now = str((datetime.now() + timedelta(hours=7)).strftime("%Y-%m-%d %H:%M:%S"))
        auth_message = 'Congratulations, you have been successfully authenticated! from: %s' % (time_now)
        self.write({'state': 'authenticated',
                    'auth_message': auth_message})

    # @api.multi
    @mp.shopee.capture_error
    def shopee_register_webhooks(self):
        _logger = self.env['mp.base']._logger
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        self.ensure_one()
        params = {}
        if self.mp_token_id.state == 'valid':
            params = {'access_token': self.mp_token_id.name}

        webhook_args = {
            'callback_url': base_url+'/api/izi/webhook/sp/order',
            'push_config': {}
        }

        if self.sp_is_webhook_order:
            webhook_args['push_config'].update({
                'order_status': 1,
                'order_tracking_no': 1
            })
        if len(webhook_args.get('push_config')) > 1:
            sp_account = self.shopee_get_account(**params)
            sp_webhook = ShopeeWebhook(sp_account)
            response = sp_webhook.register_webhook(**webhook_args)
            if response.status_code == 200:
                if response.json().get('status') == 'success':
                    notif_msg = "Register webhook is successfully.."
                    self.write({
                        'mp_webhook_state': 'registered'
                    })
                else:
                    notif_msg = "Register webhook is failure.."
                    self.write({
                        'mp_webhook_state': 'no_register'
                    })
            else:
                notif_msg = "Register webhook is failure.."
                self.write({
                    'mp_webhook_state': 'no_register'
                })
            _logger(self.marketplace, notif_msg, notify=True, notif_sticky=False)
        else:
            raise UserError('Select at least 1 feature for register webhook')

    # @api.multi
    @mp.shopee.capture_error
    def shopee_unregister_webhooks(self):
        _logger = self.env['mp.base']._logger
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        self.ensure_one()
        params = {}
        if self.mp_token_id.state == 'valid':
            params = {'access_token': self.mp_token_id.name}

        webhook_args = {
            'callback_url': base_url+'/api/izi/webhook/sp/order',
            'push_config': {}
        }

        if not self.sp_is_webhook_order:
            webhook_args['push_config'].update({
                'order_status': 0,
                'order_tracking_no': 0
            })
        if len(webhook_args.get('push_config')) > 1:
            sp_account = self.shopee_get_account(**params)
            sp_webhook = ShopeeWebhook(sp_account)
            response = sp_webhook.register_webhook(**webhook_args)
            if response.status_code == 200:
                if response.json().get('status') == 'success':
                    notif_msg = "Unregister webhook is successfully.."
                    self.write({
                        'mp_webhook_state': 'no_register'
                    })
            _logger(self.marketplace, notif_msg, notify=True, notif_sticky=False)
        else:
            raise UserError('Select at least 1 feature for register webhook')

    # @api.multi
    @mp.shopee.capture_error
    def shopee_get_shop(self):
        self.ensure_one()
        mp_account_ctx = self.generate_context()
        _notify = self.env['mp.base']._notify
        mp_shopee_shop_obj = self.env['mp.shopee.shop'].with_context(mp_account_ctx)
        params = {}
        if self.mp_token_id.state == 'valid':
            params = {'access_token': self.mp_token_id.name}
        sp_account = self.shopee_get_account(**params)
        sp_shop = ShopeeShop(sp_account, sanitizers=mp_shopee_shop_obj.get_sanitizers(self.marketplace))
        _notify('info', 'Importing shop from {} is started... Please wait!'.format(self.marketplace.upper()),
                notif_sticky=False)
        sp_shop_raw = sp_shop.get_shop_info()
        sp_data_raw, sp_data_sanitized = mp_shopee_shop_obj.with_context(
            mp_account_ctx)._prepare_mapping_raw_data(raw_data=sp_shop_raw)
        check_existing_records_params = {
            'identifier_field': 'shop_id',
            'raw_data': sp_data_raw,
            'mp_data': sp_data_sanitized,
            'multi': isinstance(sp_data_sanitized, list)
        }
        check_existing_records = mp_shopee_shop_obj.with_context(
            mp_account_ctx).check_existing_records(**check_existing_records_params)
        mp_shopee_shop_obj.with_context(mp_account_ctx).handle_result_check_existing_records(check_existing_records)

    # @api.multi
    @mp.shopee.capture_error
    def shopee_get_logistic(self):
        self.ensure_one()
        mp_account_ctx = self.generate_context()
        _notify = self.env['mp.base']._notify
        mp_shopee_logistic_obj = self.env['mp.shopee.logistic'].with_context(mp_account_ctx)
        params = {}
        if self.mp_token_id.state == 'valid':
            params = {'access_token': self.mp_token_id.name}
        sp_account = self.shopee_get_account(**params)
        sp_logistic = ShopeeLogistic(sp_account, sanitizers=mp_shopee_logistic_obj.get_sanitizers(self.marketplace))
        _notify('info', 'Importing logistic from {} is started... Please wait!'.format(self.marketplace.upper()),
                notif_sticky=False)
        sp_data_raw, sp_data_sanitized = sp_logistic.get_logsitic_list()
        check_existing_records_params = {
            'identifier_field': 'logistics_channel_id',
            'raw_data': sp_data_raw['logistics_channel_list'],
            'mp_data': sp_data_sanitized,
            'multi': isinstance(sp_data_sanitized, list)
        }
        check_existing_records = mp_shopee_logistic_obj.with_context(
            mp_account_ctx).check_existing_records(**check_existing_records_params)
        mp_shopee_logistic_obj.with_context(mp_account_ctx).handle_result_check_existing_records(check_existing_records)

    # @api.multi
    def shopee_get_active_logistics(self):
        mp_account_ctx = self.generate_context()
        self.ensure_one()
        self.sp_shop_id.with_context(mp_account_ctx).get_active_logistics()

    # @api.multi
    def shopee_get_dependencies(self):
        self.ensure_one()
        self.shopee_get_shop()
        self.shopee_get_logistic()
        self.shopee_get_active_logistics()
        return {
            'type': 'ir.actions.client',
            'tag': 'close_notifications',
            'params': {
                'force_show_number': 1
            }
        }

    # @api.multi
    @mp.shopee.capture_error
    def shopee_get_mp_product(self):
        mp_product_obj = self.env['mp.product']
        mp_account_ctx = self.generate_context()
        _notify = self.env['mp.base']._notify
        self.ensure_one()
        params = {}
        if self.mp_token_id.state == 'valid':
            params = {'access_token': self.mp_token_id.name}
        sp_account = self.shopee_get_account(**params)
        sp_product = ShopeeProduct(sp_account, sanitizers=mp_product_obj.get_sanitizers(self.marketplace))
        _notify('info', 'Importing product from {} is started... Please wait!'.format(self.marketplace.upper()),
                notif_sticky=False)
        sp_data_raw, sp_data_sanitized = sp_product.get_product_list(limit=mp_account_ctx.get('product_limit'))

        sp_product_exid = list(map(lambda x: str(x['item_id']), sp_data_raw))
        existing_mp_products = mp_product_obj.search([('mp_account_id', '=', self.id)])
        mp_product_need_to_deleted = []
        for mp_product in existing_mp_products:
            if mp_product.mp_external_id not in sp_product_exid:
                mp_product_need_to_deleted.append(mp_product.mp_external_id)

        check_existing_records_params = {
            'identifier_field': 'sp_product_id',
            'raw_data': sp_data_raw,
            'mp_data': sp_data_sanitized,
            'multi': isinstance(sp_data_sanitized, list)
        }
        check_existing_records = mp_product_obj.with_context(
            mp_account_ctx).check_existing_records(**check_existing_records_params)
        if check_existing_records['need_update_records']:
            mp_product_obj.with_context({'mp_account_id': self.id}).update_records(
                check_existing_records['need_update_records'])

        if check_existing_records['need_create_records']:
            sp_data_raw, sp_data_sanitized = mp_product_obj.with_context(mp_account_ctx)._prepare_create_records(
                check_existing_records['need_create_records'])
            mp_product_obj.with_context(mp_account_ctx).create_records(sp_data_raw, sp_data_sanitized,
                                                                       isinstance(sp_data_sanitized, list))
        if check_existing_records['need_skip_records']:
            mp_product_obj.with_context(mp_account_ctx).log_skip(
                self.marketplace, check_existing_records['need_skip_records'])

        # deleted mp_product if doesnt exists in marketplace
        existing_mp_products.filtered(lambda r: r.mp_external_id in mp_product_need_to_deleted).unlink()

    # @api.multi
    @mp.shopee.capture_error
    def shopee_get_mp_product_variant(self):
        mp_product_obj = self.env['mp.product']
        mp_product_variant_obj = self.env['mp.product.variant']
        self.ensure_one()

        mp_account_ctx = self.generate_context()

        params = {}
        if self.mp_token_id.state == 'valid':
            params = {'access_token': self.mp_token_id.name}
        sp_account = self.shopee_get_account(**params)
        sp_product_variant = ShopeeProduct(sp_account, sanitizers=mp_product_obj.get_sanitizers(self.marketplace))
        mp_products = mp_product_obj.search([('sp_has_variant', '=', True), ('mp_account_id', '=', self.id)])
        for mp_product in mp_products:
            variant_need_to_remove = []
            mp_product_raw = json.loads(mp_product.raw, strict=False)
            mp_product_variant_raw = mp_product_variant_obj.generate_variant_data(mp_product_raw)
            mp_variant_exid_list = [variant_id['sp_variant_id'] for variant_id in mp_product_variant_raw]
            sp_data_raw, sp_data_sanitized = mp_product_variant_obj.with_context(
                mp_account_ctx)._prepare_mapping_raw_data(raw_data=mp_product_variant_raw)

            check_existing_records_params = {
                'identifier_field': 'sp_variant_id',
                'raw_data': sp_data_raw,
                'mp_data': sp_data_sanitized,
                'multi': isinstance(sp_data_sanitized, list)
            }
            check_existing_records = mp_product_variant_obj.with_context(mp_account_ctx).check_existing_records(
                **check_existing_records_params)
            mp_product_variant_obj.with_context(mp_account_ctx).handle_result_check_existing_records(
                check_existing_records)

            for variant_obj in mp_product.mp_product_variant_ids:
                if int(variant_obj.sp_variant_id) not in mp_variant_exid_list:
                    variant_need_to_remove.append(variant_obj.sp_variant_id)

            mp_product.mp_product_variant_ids.filtered(lambda r: r.sp_variant_id in variant_need_to_remove).unlink()

        # clean variant
        mp_products = mp_product_obj.search([('mp_product_variant_ids', '!=', False),
                                            ('sp_has_variant', '=', False),
                                            ('mp_account_id', '=', self.id)])
        for product in mp_products:
            for variant in product.mp_product_variant_ids:
                variant.unlink()

    # @api.multi
    def shopee_get_products(self):
        self.ensure_one()
        self.shopee_get_mp_product()
        self.shopee_get_mp_product_variant()
        return {
            'type': 'ir.actions.client',
            'tag': 'close_notifications'
        }

    # @api.multi
    @mp.shopee.capture_error
    def shopee_get_sale_order(self, time_mode=False, **kwargs):
        mp_account_ctx = self.generate_context()
        if kwargs.get('force_update'):
            mp_account_ctx.update({'force_update': kwargs.get('force_update')})
        order_obj = self.env['sale.order'].with_context(dict(mp_account_ctx, **self._context.copy()))
        _notify = self.env['mp.base']._notify
        _logger = self.env['mp.base']._logger
        account_params = {}
        order_params = {}
        if self.mp_token_id.state == 'valid':
            account_params = {'access_token': self.mp_token_id.name}
        sp_account = self.shopee_get_account(**account_params)
        sp_order_v2 = ShopeeOrder(sp_account, sanitizers=order_obj.get_sanitizers(self.marketplace))
        sp_order_v1 = ShopeeOrder(sp_account, api_version="v1")
        _notify('info', 'Importing order from {} is started... Please wait!'.format(self.marketplace.upper()),
                notif_sticky=False)

        skipped = 0
        force_update_ids = []
        sp_order_list = []
        sp_order_raws = False
        sp_order_sanitizeds = False
        sp_orders_by_mpexid = {}
        sp_orders = order_obj.search([('mp_account_id', '=', self.id)])
        for sp_order in sp_orders:
            sp_orders_by_mpexid[sp_order.mp_invoice_number] = sp_order

        def get_order_income(sp_data_raws):
            sp_order_raws, sp_order_sanitizeds = [], []
            for index, data in enumerate(sp_data_raws):
                sp_order_invoice = data.get('order_sn')
                notif_msg = "(%s/%d) Getting order detail of %s... Please wait!" % (
                    str(index + 1), len(sp_data_raws), sp_order_invoice
                )
                _logger(self.marketplace, notif_msg, notify=True, notif_sticky=False)
                # get_income
                income_data = sp_order_v1.get_income(**{'order_sn': data['order_sn']})
                data.update({'order_income': income_data.get('order_income', False)})
                sp_order_data_raw, sp_order_data_sanitized = order_obj.with_context(
                    mp_account_ctx)._prepare_mapping_raw_data(raw_data=data)
                sp_order_raws.append(sp_order_data_raw)
                sp_order_sanitizeds.append(sp_order_data_sanitized)
            return sp_order_raws, sp_order_sanitizeds

        if kwargs.get('params') == 'by_date_range':

            order_params.update({
                'from_date': kwargs.get('from_date'),
                'to_date': kwargs.get('to_date'),
                'limit': mp_account_ctx.get('order_limit'),
                'time_mode': time_mode,
            })
            sp_order_list = sp_order_v2.get_order_list(**order_params)
            order_list = []
            sp_data_raws = []
            for sp_data_order in sp_order_list:
                sp_order_invoice = sp_data_order.get('order_sn')
                if sp_order_invoice in sp_orders_by_mpexid:
                    existing_order = sp_orders_by_mpexid[sp_order_invoice]
                    mp_status_changed = existing_order.sp_order_status != str(sp_data_order['order_status'])
                else:
                    existing_order = False
                    mp_status_changed = False
                no_existing_order = not existing_order
                if no_existing_order or mp_status_changed or mp_account_ctx.get('force_update'):
                    if sp_data_order['order_status'] == 'CANCELLED' and no_existing_order:
                        if not self.get_cancelled_orders:
                            skipped += 1
                            continue
                    if existing_order and mp_account_ctx.get('force_update'):
                        force_update_ids.append(existing_order.id)
                    if not self.get_unpaid_orders:
                        if sp_data_order['order_status'] != 'UNPAID':
                            order_list.append({'order_sn': sp_order_invoice})
                    else:
                        order_list.append({'order_sn': sp_order_invoice})
                else:
                    skipped += 1

            if order_list:
                sp_data_raws = sp_order_v2.get_order_detail(sp_data=order_list)
                sp_order_raws, sp_order_sanitizeds = get_order_income(sp_data_raws)

        elif kwargs.get('params') == 'by_mp_invoice_number':
            shopee_invoice_number = kwargs.get('mp_invoice_number')
            shopee_order_status = kwargs.get('order_status', False)
            sp_order_list.append(shopee_invoice_number)
            if shopee_order_status:
                if shopee_invoice_number in sp_orders_by_mpexid:
                    existing_order = sp_orders_by_mpexid[shopee_invoice_number]
                    mp_status_changed = existing_order.sp_order_status != shopee_order_status
                else:
                    existing_order = False
                    mp_status_changed = False
                no_existing_order = not existing_order
                if no_existing_order or mp_status_changed or mp_account_ctx.get('force_update'):
                    if shopee_order_status == 'CANCELLED' and no_existing_order:
                        if not self.get_cancelled_orders:
                            skipped += 1
                    elif shopee_order_status == 'UNPAID' and no_existing_order:
                        if not self.get_unpaid_orders:
                            skipped += 1
                    else:
                        order_params.update({
                            'order_id': shopee_invoice_number
                        })

                    if existing_order and mp_account_ctx.get('force_update'):
                        force_update_ids.append(existing_order.id)
                else:
                    skipped += 1

                if len(order_params) != 0:
                    sp_data_raws = sp_order_v2.get_order_detail(**order_params)
                    sp_order_raws, sp_order_sanitizeds = get_order_income(sp_data_raws)
                else:
                    sp_data_raws = {}
            else:
                order_params.update({
                    'order_id': shopee_invoice_number
                })
                sp_data_raws = sp_order_v2.get_order_detail(**order_params)
                sp_order_raws, sp_order_sanitizeds = get_order_income(sp_data_raws)

        _logger(self.marketplace, 'Processed %s order(s) from %s of total orders imported!' % (
                len(sp_data_raws), len(sp_order_list)
                ), notify=True, notif_sticky=False)

        if force_update_ids:
            order_obj = order_obj.with_context(dict(order_obj._context.copy(), **{
                'force_update_ids': force_update_ids
            }))

        if sp_order_raws and sp_order_sanitizeds:
            check_existing_records_params = {
                'identifier_field': 'sp_order_id',
                'raw_data': sp_order_raws,
                'mp_data': sp_order_sanitizeds,
                'multi': isinstance(sp_order_sanitizeds, list)
            }
            check_existing_records = order_obj.with_context(mp_account_ctx).check_existing_records(
                **check_existing_records_params)
            order_obj.with_context(mp_account_ctx).handle_result_check_existing_records(check_existing_records)
        else:
            _logger(self.marketplace, 'There is no update, skipped %s order(s)!' % skipped, notify=True,
                    notif_sticky=False)

    # @api.multi
    def shopee_get_orders(self, **kwargs):
        rec = self
        if kwargs.get('id', False):
            rec = self.browse(kwargs.get('id'))
        rec.ensure_one()
        # self.shopee_get_sale_order(time_range='create_time', **kwargs)
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
        rec.shopee_get_sale_order(time_mode='update_time', **kwargs)
        return {
            'type': 'ir.actions.client',
            'tag': 'close_notifications'
        }
