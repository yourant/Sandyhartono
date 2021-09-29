# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import json

from odoo import api, fields, models

from odoo.addons.izi_blibli.objects.utils.blibli.account import BlibliAccount
from odoo.addons.izi_blibli.objects.utils.blibli.logistic import BlibliLogistic
from odoo.addons.izi_blibli.objects.utils.blibli.product import BlibliProduct
from odoo.addons.izi_marketplace.objects.utils.tools import json_digger


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
    partner_id = fields.Many2one(default=lambda self:
                                 self.env.ref('izi_blibli.res_partner_blibli',
                                              raise_if_not_found=False).id
                                 )

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
            self.write({
                'state': 'authenticated',
                'auth_message': 'Congratulations, you have been successfully authenticated!'
            })

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

    @api.multi
    def blibli_get_mp_product(self):
        mp_product_obj = self.env['mp.product']

        self.ensure_one()

        mp_account_ctx = self.generate_context()

        bli_account = self.blibli_get_account()
        bli_product = BlibliProduct(bli_account, sanitizers=mp_product_obj.get_sanitizers(self.marketplace))
        bli_data_raw, bli_data_sanitized = bli_product.get_product_list()
        check_existing_records = mp_product_obj.with_context(mp_account_ctx). \
            check_existing_records('bli_product_id', bli_data_raw, bli_data_sanitized,
                                   isinstance(bli_data_sanitized, list))
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

    @api.multi
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

    @api.multi
    def blibli_get_products(self):
        self.ensure_one()
        self.blibli_get_mp_product()
        self.blibli_get_mp_product_variant()
