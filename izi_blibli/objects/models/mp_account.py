# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import json

from odoo import api, fields, models

from odoo.addons.izi_blibli.objects.utils.blibli.account import BlibliAccount
from odoo.addons.izi_blibli.objects.utils.blibli.logistic import BlibliLogistic
from odoo.addons.izi_blibli.objects.utils.blibli.shop import BlibliShop
from odoo.addons.izi_blibli.objects.utils.blibli.product import BlibliProduct
from odoo.addons.izi_marketplace.objects.utils.tools import json_digger, mp
from odoo.addons.izi_blibli.objects.utils.blibli.order import BlibliOrder


class MarketplaceAccount(models.Model):
    _inherit = 'mp.account'

    READONLY_STATES = {
        'authenticated': [('readonly', True)],
        'authenticating': [('readonly', False)],
    }

    # marketplace = fields.Selection(selection_add=[('blibli', 'Blibli')], ondelete={'blibli': 'cascade'})
    bli_usermail = fields.Char(string='User Email', required_if_marketplace="blibli", states=READONLY_STATES)
    bli_shop_name = fields.Char(string='Shop Name', required_if_marketplace="blibli", states=READONLY_STATES)
    bli_shop_code = fields.Char(string='Shop Code', required_if_marketplace="blibli", states=READONLY_STATES)
    bli_seller_key = fields.Char(string='Seller Key', required_if_marketplace="blibli", states=READONLY_STATES)
    bli_client_id = fields.Char('Blibli Client ID', required_if_marketplace="blibli", states=READONLY_STATES)
    bli_client_secret = fields.Char('Blibli Client Secret', required_if_marketplace="blibli", states=READONLY_STATES)
    bli_store_id = fields.Integer('Store ID', states=READONLY_STATES)
    bli_shop_id = fields.Many2one(comodel_name="mp.blibli.shop", string="Blibli Current Shop")

    @api.model
    def blibli_get_account(self, **kwargs):
        credentials = dict({
            'usermail': self.bli_usermail,
            'shop_name': self.bli_shop_name,
            'shop_code': self.bli_shop_code,
            'seller_key': self.bli_seller_key,
            'store_id': 10001,
            'client_id': self.bli_client_id,
            'client_secret': self.bli_client_secret
        }, **kwargs)
        bli_account = BlibliAccount(**credentials)
        return bli_account

    # @api.multi
    def blibli_authenticate(self):
        bli_account = self.blibli_get_account()
        result = bli_account.authenticate()
        if result:
            self.write({
                'state': 'authenticated',
                'auth_message': 'Congratulations, you have been successfully authenticated!'
            })

    # @api.multi
    @mp.blibli.capture_error
    def blibli_get_logistic(self):
        mp_account_ctx = self.generate_context()
        mp_blibli_logistic_obj = self.env['mp.blibli.logistic'].with_context(mp_account_ctx)

        self.ensure_one()
        params = {}
        bli_account = self.blibli_get_account(**params)
        bli_logistic = BlibliLogistic(bli_account, sanitizers=mp_blibli_logistic_obj.get_sanitizers(self.marketplace))
        bli_data_raw, bli_data_sanitized = bli_logistic.get_logsitic_list()
        check_existing_records_params = {
            'identifier_field': 'logistics_code',
            'raw_data': bli_data_raw,
            'mp_data': bli_data_sanitized,
            'multi': isinstance(bli_data_sanitized, list)
        }
        check_existing_records = mp_blibli_logistic_obj.with_context(
            mp_account_ctx).check_existing_records(**check_existing_records_params)
        mp_blibli_logistic_obj.with_context(mp_account_ctx).handle_result_check_existing_records(check_existing_records)
        # mp_blibli_logistic_obj.with_context({'mp_account_id': self.id}).create_records(
        #     bli_data_raw, bli_data_sanitized, isinstance(bli_data_sanitized, list))

    # @api.multi
    @mp.blibli.capture_error
    def blibli_get_shop(self):
        self.ensure_one()
        mp_account_ctx = self.generate_context()
        _notify = self.env['mp.base']._notify
        mp_blibli_shop_obj = self.env['mp.blibli.shop'].with_context(mp_account_ctx)
        params = {}
        # if self.mp_token_id.state == 'valid':
        #     params = {'access_token': self.mp_token_id.name}
        bli_account = self.blibli_get_account(**params)
        bli_shop = BlibliShop(bli_account, sanitizers=mp_blibli_shop_obj.get_sanitizers(self.marketplace))
        _notify('info', 'Importing shop from {} is started... Please wait!'.format(self.marketplace.upper()),
                notif_sticky=False)
        bli_shop_raw = bli_shop.get_shop_info()
        bli_data_raw, bli_data_sanitized = mp_blibli_shop_obj.with_context(
            mp_account_ctx)._prepare_mapping_raw_data(raw_data=bli_shop_raw)
        check_existing_records_params = {
            'identifier_field': 'shop_id',
            'raw_data': bli_data_raw,
            'mp_data': bli_data_sanitized,
            'multi': isinstance(bli_data_sanitized, list)
        }
        check_existing_records = mp_blibli_shop_obj.with_context(
            mp_account_ctx).check_existing_records(**check_existing_records_params)
        mp_blibli_shop_obj.with_context(mp_account_ctx).handle_result_check_existing_records(check_existing_records)

    # @api.multi
    def blibli_get_active_logistics(self):
        mp_account_ctx = self.generate_context()
        self.ensure_one()
        self.bli_shop_id.with_context(mp_account_ctx).get_active_logistics()

    # @api.multi
    def blibli_get_dependencies(self):
        self.ensure_one()
        self.blibli_get_shop()
        self.blibli_get_logistic()
        self.blibli_get_active_logistics()
        return {
            'type': 'ir.actions.client',
            'tag': 'close_notifications',
            'params': {
                'force_show_number': 1
            }
        }

    # @api.multi
    @mp.blibli.capture_error
    def blibli_get_mp_product(self):
        mp_product_obj = self.env['mp.product']

        self.ensure_one()

        mp_account_ctx = self.generate_context()

        bli_account = self.blibli_get_account()
        bli_product = BlibliProduct(bli_account, sanitizers=mp_product_obj.get_sanitizers(self.marketplace))
        bli_data_raw, bli_data_sanitized = bli_product.get_product_list()
        check_existing_records_params = {
            'identifier_field': 'bli_product_id',
            'raw_data': bli_data_raw,
            'mp_data': bli_data_sanitized,
            'multi': isinstance(bli_data_sanitized, list)
        }
        check_existing_records = mp_product_obj.with_context(
            mp_account_ctx).check_existing_records(**check_existing_records_params)
        if check_existing_records['need_update_records']:
            mp_product_obj.with_context({'mp_account_id': self.id}).update_records(
                check_existing_records['need_update_records'])

        if check_existing_records['need_create_records']:
            bli_data_raw, bli_data_sanitized = mp_product_obj._prepare_create_records(
                check_existing_records['need_create_records'])
            mp_product_obj.with_context({'mp_account_id': self.id}).create_records(bli_data_raw, bli_data_sanitized,
                                                                                   isinstance(bli_data_sanitized, list))

        if check_existing_records['need_skip_records']:
            mp_product_obj.log_skip(self.marketplace, check_existing_records['need_skip_records'])

    # @api.multi
    @mp.blibli.capture_error
    def blibli_get_mp_product_variant(self):
        mp_product_obj = self.env['mp.product']
        mp_product_variant_obj = self.env['mp.product.variant']
        self.ensure_one()

        mp_account_ctx = self.generate_context()

        bli_account = self.blibli_get_account()
        bli_product_variant = BlibliProduct(bli_account,
                                            sanitizers=mp_product_variant_obj.get_sanitizers(self.marketplace))

        mp_products = mp_product_obj.search([('bli_has_variant', '=', True)])
        for mp_product in mp_products:
            if mp_product['mp_account_id']['bli_shop_code'] != bli_account.shop_code:
                continue
            mp_product_raw = json.loads(mp_product.raw, strict=False)
            bli_variant_ids = json_digger(mp_product_raw, 'bli_variant_ids')
            for bli_variant_id in bli_variant_ids:
                bli_data_raw, bli_data_sanitized = bli_product_variant.get_product_variant(product_id=bli_variant_id)
                check_existing_records_params = {
                    'identifier_field': 'bli_variant_id',
                    'raw_data': bli_data_raw,
                    'mp_data': bli_data_sanitized,
                    'multi': isinstance(bli_data_sanitized, list)
                }
                check_existing_records = mp_product_variant_obj.with_context(mp_account_ctx).check_existing_records(
                    **check_existing_records_params)
                mp_product_variant_obj.with_context(mp_account_ctx).handle_result_check_existing_records(
                    check_existing_records)

    # @api.multi
    def blibli_get_products(self):
        self.ensure_one()
        self.blibli_get_mp_product()
        self.blibli_get_mp_product_variant()
        return {
            'type': 'ir.actions.client',
            'tag': 'close_notifications'
        }

    # @api.multi
    @mp.blibli.capture_error
    def blibli_get_sale_order(self, **kwargs):
        sale_order_obj = self.env['sale.order']
        mp_account_ctx = self.generate_context()
        _notify = self.env['mp.base']._notify
        params = {}
        bli_account = self.blibli_get_account(**params)
        bli_order = BlibliOrder(bli_account, sanitizers=sale_order_obj.get_sanitizers(self.marketplace))
        _notify('info', 'Importing order from {} is started... Please wait!'.format(self.marketplace.upper()),
                notif_sticky=False)
        if kwargs.get('params') == 'by_date_range':
            params.update({
                'from_date': kwargs.get('from_date'),
                'to_date': kwargs.get('to_date'),
                'limit': mp_account_ctx.get('order_limit')
            })
            bli_data_raw = bli_order.get_order_list(**params)
        elif kwargs.get('params') == 'by_mp_invoice_number':
            pass
            # params.update({
            #     'order_id': kwargs.get('mp_invoice_number')
            # })
            # bli_data_raw, bli_data_sanitized = bli_order.get_order_detail(**params)

        bli_order_raws, bli_data_sanitized = [], []
        for data in bli_data_raw:
            bli_order_data_raw, bli_order_data_sanitized = sale_order_obj.with_context(
                mp_account_ctx)._prepare_mapping_raw_data(raw_data=data)
            bli_order_raws.append(bli_order_data_raw)
            bli_data_sanitized.append(bli_order_data_sanitized)

        check_existing_records_params = {
            'identifier_field': 'bli_order_id',
            'raw_data': bli_data_raw,
            'mp_data': bli_data_sanitized,
            'multi': isinstance(bli_data_sanitized, list)
        }
        check_existing_records = sale_order_obj.with_context(mp_account_ctx).check_existing_records(
            **check_existing_records_params)
        sale_order_obj.with_context(mp_account_ctx).handle_result_check_existing_records(check_existing_records)

    # @api.multi
    def blibli_get_orders(self, **kwargs):
        self.ensure_one()
        self.blibli_get_sale_order(**kwargs)
        return {
            'type': 'ir.actions.client',
            'tag': 'close_notifications'
        }
