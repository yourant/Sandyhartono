# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import json

from odoo import api, fields, models

from odoo.addons.izi_marketplace.objects.utils.tools import mp
from odoo.addons.izi_shopee.objects.utils.shopee.account import ShopeeAccount
from odoo.addons.izi_shopee.objects.utils.shopee.logistic import ShopeeLogistic
from odoo.addons.izi_shopee.objects.utils.shopee.shop import ShopeeShop
from odoo.addons.izi_shopee.objects.utils.shopee.product import ShopeeProduct
from odoo.addons.izi_shopee.objects.utils.shopee.order import ShopeeOrder


class MarketplaceAccount(models.Model):
    _inherit = 'mp.account'

    READONLY_STATES = {
        'authenticated': [('readonly', True)],
        'authenticating': [('readonly', False)],
    }

    marketplace = fields.Selection(selection_add=[('shopee', 'Shopee')])
    sp_partner_id = fields.Char(string="Partner ID", required_if_marketplace="shopee", states=READONLY_STATES)
    sp_partner_key = fields.Char(string="Partner Key", required_if_marketplace="shopee", states=READONLY_STATES)
    sp_shop_id = fields.Many2one(comodel_name="mp.shopee.shop", string="Current Shop")

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
        self.write({'state': 'authenticated',
                    'auth_message': 'Congratulations, you have been successfully authenticated!'})

    @api.multi
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
                notif_sticky=True)
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

    @api.multi
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
                notif_sticky=True)
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

    @api.multi
    def shopee_get_active_logistics(self):
        mp_account_ctx = self.generate_context()
        self.ensure_one()
        self.sp_shop_id.with_context(mp_account_ctx).get_active_logistics()

    @api.multi
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

    @api.multi
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
                notif_sticky=True)
        sp_data_raw, sp_data_sanitized = sp_product.get_product_list(limit=mp_account_ctx.get('product_limit'))
        check_existing_records = mp_product_obj.with_context(mp_account_ctx).check_existing_records(
            'sp_product_id', sp_data_raw, sp_data_sanitized, isinstance(sp_data_sanitized, list))
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

    @api.multi
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
        mp_products = mp_product_obj.search([('sp_has_variant', '=', True)])
        for mp_product in mp_products:
            mp_product_raw = json.loads(mp_product.raw, strict=False)
            mp_product_variant_raw = mp_product_variant_obj.generate_variant_data(mp_product_raw)
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

    @api.multi
    def shopee_get_products(self):
        self.ensure_one()
        self.shopee_get_mp_product()
        self.shopee_get_mp_product_variant()
        return {
            'type': 'ir.actions.client',
            'tag': 'close_notifications'
        }

    @api.multi
    @mp.shopee.capture_error
    def shopee_get_sale_order(self, time_range, **kwargs):
        sale_order_obj = self.env['sale.order']
        mp_account_ctx = self.generate_context()
        _notify = self.env['mp.base']._notify
        account_params = {}
        order_params = {}
        if self.mp_token_id.state == 'valid':
            account_params = {'access_token': self.mp_token_id.name}
        sp_account = self.shopee_get_account(**account_params)
        sp_order = ShopeeOrder(sp_account, sanitizers=sale_order_obj.get_sanitizers(self.marketplace))
        _notify('info', 'Importing order from {} is started... Please wait!'.format(self.marketplace.upper()),
                notif_sticky=True)
        if kwargs.get('params') == 'by_date_range':
            order_params.update({
                'from_date': kwargs.get('from_date'),
                'to_date': kwargs.get('to_date'),
                'limit': mp_account_ctx.get('order_limit'),
                'time_range': time_range
            })
            sp_data_raw, sp_data_sanitized = sp_order.get_order_list(**order_params)
        elif kwargs.get('params') == 'by_mp_invoice_number':
            order_params.update({
                'order_id': kwargs.get('mp_invoice_number')
            })
            sp_data_raw, sp_data_sanitized = sp_order.get_order_detail(**order_params)

        check_existing_records_params = {
            'identifier_field': 'sp_order_id',
            'raw_data': sp_data_raw,
            'mp_data': sp_data_sanitized,
            'multi': isinstance(sp_data_sanitized, list)
        }
        check_existing_records = sale_order_obj.with_context(mp_account_ctx).check_existing_records(
            **check_existing_records_params)
        if time_range == 'create_time':
            check_existing_records.pop('need_update_records')
        elif time_range == 'update_time':
            check_existing_records.pop('need_create_records')
        sale_order_obj.with_context(mp_account_ctx).handle_result_check_existing_records(check_existing_records)

    @api.multi
    def shopee_get_orders(self, **kwargs):
        self.ensure_one()
        self.shopee_get_sale_order(time_range='create_time', **kwargs)
        self.shopee_get_sale_order(time_range='update_time', **kwargs)
        return {
            'type': 'ir.actions.client',
            'tag': 'close_notifications'
        }
