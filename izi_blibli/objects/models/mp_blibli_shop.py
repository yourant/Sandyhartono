# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.izi_marketplace.objects.utils.tools import json_digger
from odoo.addons.izi_blibli.objects.utils.blibli.logistic import BlibliLogistic


class MPBlibliShop(models.Model):
    _name = 'mp.blibli.shop'
    _inherit = 'mp.base'
    _description = 'Marketplace Blibli Shop'
    _rec_name = 'shop_name'
    _rec_mp_external_id = 'shop_id'

    shop_id = fields.Char(string="Shop ID", readonly=True)
    shop_name = fields.Char(string="Shop Name", readonly=True)
    shop_logistic_ids = fields.One2many(comodel_name="mp.blibli.shop.logistic", inverse_name="shop_id",
                                        string="Active Logistics", required=False)

    @classmethod
    def _add_rec_mp_field_mapping(cls, mp_field_mappings=None):
        if not mp_field_mappings:
            mp_field_mappings = []

        marketplace = 'blibli'
        mp_field_mapping = {
            'shop_name': ('shop_name', None),
            'shop_id': ('shop_id', None),
        }
        mp_field_mappings.append((marketplace, mp_field_mapping))
        super(MPBlibliShop, cls)._add_rec_mp_field_mapping(mp_field_mappings)

    @api.model
    def blibli_get_sanitizers(self, mp_field_mapping):
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

        records = super(MPBlibliShop, self)._finish_create_records(records)
        mp_account.write({'bli_shop_id': records[0].id})
        return records

    @api.multi
    def get_active_logistics(self):
        mp_blibli_logistic_obj = self.env['mp.blibli.logistic']
        mp_blibli_shop_logistic_obj = self.env['mp.blibli.shop.logistic']

        for shop in self:
            mp_account = shop.mp_account_id
            params = {}
            # if mp_account.mp_token_id.state == 'valid':
            #     params = {'access_token': mp_account.mp_token_id.name}
            bli_account = mp_account.blibli_get_account(**params)
            bli_logistic = BlibliLogistic(bli_account)
            bli_raw_data = bli_logistic.get_logsitic_list()
            logistic_list_raws = bli_raw_data['content']
            for active_logistic_raw in logistic_list_raws:
                bli_logistic = mp_blibli_logistic_obj.search_mp_records(shop.marketplace,
                                                                        active_logistic_raw['code'])
                existing_shop_logistic = mp_blibli_shop_logistic_obj.search([
                    ('shop_id', '=', shop.id), ('logistic_id', '=', bli_logistic.id)
                ])
                shop_logistic_values = {
                    'shop_id': shop.id,
                    'logistic_id': bli_logistic.id,
                    'mp_account_id': mp_account.id,
                    'is_selected': active_logistic_raw['selected'],
                    'geolocation': active_logistic_raw['geolocation'],
                }
                if not existing_shop_logistic.exists():
                    shop_logistic = mp_blibli_shop_logistic_obj.create(shop_logistic_values)
                    shop.write({'shop_logistic_ids': [(4, shop_logistic.id)]})
                else:
                    existing_shop_logistic.write(shop_logistic_values)


class MPShopeeShopLogistic(models.Model):
    _name = 'mp.blibli.shop.logistic'
    _inherit = 'mp.base'
    _description = 'Marketplace Blibli Shop Logistic'
    _sql_constraints = [
        ('unique_shop_logistic', 'UNIQUE(shop_id,logistic_id)', 'Please select one logistic per shop!')
    ]

    shop_id = fields.Many2one(comodel_name="mp.blibli.shop", string="Shop", required=True, ondelete="restrict")
    logistic_id = fields.Many2one(comodel_name="mp.blibli.logistic", string="Logistic", required=True,
                                  ondelete="restrict")
    name = fields.Char(related="logistic_id.logistics_name")
    is_selected = fields.Boolean(string="Selected")
    geolocation = fields.Boolean(string='Need Geolocation Information', readonly=True)
