# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
from datetime import datetime
from odoo import api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.izi_shopee.objects.utils.shopee.logistic import ShopeeLogistic


class MPShopeeShop(models.Model):
    _name = 'mp.shopee.shop'
    _inherit = 'mp.base'
    _description = 'Marketplace Shopee Shop'
    _rec_name = 'shop_name'
    _rec_mp_external_id = 'shop_id'

    shop_id = fields.Char(string="Shop ID", readonly=True)
    shop_name = fields.Char(string="Shop Name", readonly=True)
    shop_description = fields.Char(string="Shop Description", readonly=True)
    shop_logo = fields.Char(string="Shop Logo", readonly=True)
    shop_region = fields.Char(string="Shop Region", readonly=True)
    shop_status = fields.Char(string="Shop Status", readonly=True)
    is_cb = fields.Boolean(string='Shop is CB ?', readonly=True)
    is_cnsc = fields.Boolean(string='Shop is CNSC ?', readonly=True)
    auth_time = fields.Datetime(string='Shop Authentication Time', readonly=True)
    expire_time = fields.Datetime(string='Shop Expired Authentication Time', readonly=True)
    shop_logistic_ids = fields.One2many(comodel_name="mp.shopee.shop.logistic", inverse_name="shop_id",
                                        string="Logistics",
                                        required=False)

    @classmethod
    def _add_rec_mp_field_mapping(cls, mp_field_mappings=None):
        if not mp_field_mappings:
            mp_field_mappings = []

        marketplace = 'shopee'
        mp_field_mapping = {
            'shop_id': ('shop_id', lambda env, r: str(r)),
            'shop_name': ('shop_name', None),
            'shop_description': ('description', None),
            'shop_region': ('region', None),
            'shop_status': ('status', None),
            'shop_logo': ('shop_logo', None),
            'is_cb': ('is_cb', None),
            'is_cnsc': ('is_cnsc', None),
            'auth_time': ('auth_time', lambda env, r: datetime.fromtimestamp(r) if r else False),
            'expire_time': ('expire_time', lambda env, r: datetime.fromtimestamp(r) if r else False),

        }
        mp_field_mappings.append((marketplace, mp_field_mapping))
        super(MPShopeeShop, cls)._add_rec_mp_field_mapping(mp_field_mappings)

    @api.model
    def shopee_get_sanitizers(self, mp_field_mapping):
        default_sanitizer = self.get_default_sanitizer(mp_field_mapping)
        return {
            'shop_info': default_sanitizer
        }

    @api.model
    def _finish_create_records(self, records):
        mp_account_obj = self.env['mp.account']

        context = self._context
        if not context.get('mp_account_id'):
            raise ValidationError("Please define mp_account_id in context!")

        mp_account = mp_account_obj.browse(context.get('mp_account_id'))

        records = super(MPShopeeShop, self)._finish_create_records(records)
        mp_account.write({'sp_shop_id': records[0].id})
        return records

    @api.multi
    def get_active_logistics(self):
        mp_shopee_logistic_obj = self.env['mp.shopee.logistic']
        mp_shopee_shop_logistic_obj = self.env['mp.shopee.shop.logistic']

        for shop in self:
            mp_account = shop.mp_account_id
            if mp_account.mp_token_id.state == 'valid':
                params = {'access_token': mp_account.mp_token_id.name}
            sp_account = mp_account.shopee_get_account(**params)
            sp_logistic = ShopeeLogistic(sp_account)
            sp_raw_data = sp_logistic.get_logsitic_list()
            logistic_list_raws = sp_raw_data['logistics_channel_list']
            for active_logistic_raw in logistic_list_raws:
                sp_logistic = mp_shopee_logistic_obj.search_mp_records(shop.marketplace,
                                                                       active_logistic_raw['logistics_channel_id'])
                existing_shop_logistic = mp_shopee_shop_logistic_obj.search([
                    ('shop_id', '=', shop.id), ('logistic_id', '=', sp_logistic.id)
                ])
                shop_logistic_values = {
                    'shop_id': shop.id,
                    'logistic_id': sp_logistic.id,
                    'mp_account_id': mp_account.id,
                    'cod_enabled': active_logistic_raw['cod_enabled'],
                    'enabled': active_logistic_raw['enabled'],
                }
                if not existing_shop_logistic.exists():
                    shop_logistic = mp_shopee_shop_logistic_obj.create(shop_logistic_values)
                    shop.write({'shop_logistic_ids': [(4, shop_logistic.id)]})
                else:
                    existing_shop_logistic.write(shop_logistic_values)


class MPShopeeShopLogistic(models.Model):
    _name = 'mp.shopee.shop.logistic'
    _inherit = 'mp.base'
    _description = 'Marketplace Shopee Shop Logistic'
    _sql_constraints = [
        ('unique_shop_logistic', 'UNIQUE(shop_id,logistic_id)', 'Please select one logistic per shop!')
    ]

    shop_id = fields.Many2one(comodel_name="mp.shopee.shop", string="Shop", required=True, ondelete="restrict")
    logistic_id = fields.Many2one(comodel_name="mp.shopee.logistic", string="Logistic", required=True,
                                  ondelete="restrict")
    name = fields.Char(related="logistic_id.logistics_channel_name")
    enabled = fields.Boolean(string="Logistic is Enable ? ")
    cod_enabled = fields.Boolean(string='COD Enabled', readonly=True)
