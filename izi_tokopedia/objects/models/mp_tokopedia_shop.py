# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.izi_marketplace.objects.utils.tools import json_digger
from odoo.addons.izi_tokopedia.objects.utils.tokopedia.logistic import TokopediaLogistic


class MPTokopediaShop(models.Model):
    _name = 'mp.tokopedia.shop'
    _inherit = 'mp.base'
    _description = 'Marketplace Tokopedia Shop'
    _rec_name = 'shop_name'
    _rec_mp_external_id = 'shop_id'

    SHOP_STATES = [
        ('0', 'Deleted'),
        ('1', 'Open'),
        ('2', 'Closed'),
        ('3', 'Moderated'),
        ('4', 'Inactive'),
        ('5', 'Moderated Permanently'),
        ('6', 'Incubate'),
        ('7', 'Schedule Active'),
    ]

    mp_account_id = fields.Many2one(readonly=True)
    shop_id = fields.Char(string="Shop ID", readonly=True, mp_raw=True, mp_raw_handler=lambda env, r: str(r))
    user_id = fields.Char(string="User ID", readonly=True, mp_raw=True, mp_raw_handler=lambda env, r: str(r))
    shop_name = fields.Char(string="Shop Name", readonly=True, mp_raw=True)
    shop_url = fields.Char(string="Shop URL", readonly=True, mp_raw=True)
    logo = fields.Char(string="Logo", readonly=True, mp_raw=True)
    is_open = fields.Boolean(string="Is Open?", readonly=True, mp_raw=True, mp_raw_handler=lambda env, r: bool(r))
    status = fields.Selection(string="Status", selection=SHOP_STATES, readonly=True, mp_raw=True,
                              mp_raw_handler=lambda env, r: str(r))
    date_shop_created = fields.Date(string="Date Shop Created", readonly=True, mp_raw=True)
    domain = fields.Char(string="Domain", readonly=True, mp_raw=True)
    shop_logistic_ids = fields.One2many(comodel_name="mp.tokopedia.shop.logistic", inverse_name="shop_id",
                                        string="Active Logistics", required=False)

    @api.model
    def tokopedia_get_sanitizers(self, mp_field_mapping):
        default_sanitizer = self.get_default_sanitizer(mp_field_mapping, root_path='data')
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

        records = super(MPTokopediaShop, self)._finish_create_records(records)
        mp_account.write({'tp_shop_id': records[0].id})
        return records

    @api.multi
    def get_active_logistics(self):
        mp_tokopedia_logistic_obj = self.env['mp.tokopedia.logistic']
        mp_tokopedia_logistic_service_obj = self.env['mp.tokopedia.logistic.service']
        mp_tokopedia_shop_logistic_obj = self.env['mp.tokopedia.shop.logistic']

        for shop in self:
            mp_account = shop.mp_account_id
            tp_account = mp_account.tokopedia_get_account()
            tp_logistic = TokopediaLogistic(tp_account)
            tp_raw_data = tp_logistic.get_logistic_active_info(shop.shop_id)
            active_logistic_raws = json_digger(tp_raw_data, 'Shops/ShipmentInfos')[0]
            for active_logistic_raw in active_logistic_raws:
                tp_logistic = mp_tokopedia_logistic_obj.search_mp_records(shop.marketplace,
                                                                          active_logistic_raw['ShipmentID'])
                active_logistic_service_ids = json_digger(active_logistic_raw, 'ShipmentPackages/ShippingProductID')
                tp_logistic_service_ids = [
                    mp_tokopedia_logistic_service_obj.search_mp_records(shop.marketplace, active_logistic_service_id).id
                    for active_logistic_service_id in active_logistic_service_ids]
                existing_shop_logistic = mp_tokopedia_shop_logistic_obj.search([
                    ('shop_id', '=', shop.id), ('logistic_id', '=', tp_logistic.id)
                ])
                shop_logistic_values = {
                    'shop_id': shop.id,
                    'logistic_id': tp_logistic.id,
                    'service_ids': [(6, 0, tp_logistic_service_ids)],
                    'mp_account_id': mp_account.id
                }
                if not existing_shop_logistic.exists():
                    shop_logistic = mp_tokopedia_shop_logistic_obj.create(shop_logistic_values)
                    shop.write({'shop_logistic_ids': [(4, shop_logistic.id)]})
                else:
                    existing_shop_logistic.write(shop_logistic_values)


class MPTokopediaShopLogistic(models.Model):
    _name = 'mp.tokopedia.shop.logistic'
    _inherit = 'mp.base'
    _description = 'Marketplace Tokopedia Shop Logistic'
    _sql_constraints = [
        ('unique_shop_logistic', 'UNIQUE(shop_id,logistic_id)', 'Please select one logistic per shop!')
    ]

    shop_id = fields.Many2one(comodel_name="mp.tokopedia.shop", string="Shop", required=True, ondelete="restrict")
    logistic_id = fields.Many2one(comodel_name="mp.tokopedia.logistic", string="Logistic", required=True,
                                  ondelete="restrict")
    service_ids = fields.Many2many(comodel_name="mp.tokopedia.logistic.service",
                                   relation="rel_tp_shop_logistic_service", column1="shop_logistic_id",
                                   column2="service_id", string="Active Service(s)")
    name = fields.Char(related="logistic_id.shipper_name")
    logo = fields.Char(related="logistic_id.logo")

    @api.onchange('service_ids')
    def onchange_shop_id(self):
        logistic_ids = self.shop_id.shop_logistic_ids.mapped('logistic_id').ids
        return {'domain': {'logistic_id': [('id', 'not in', logistic_ids)]}}

