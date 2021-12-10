# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
from odoo import api, fields, models

from odoo.addons.izi_marketplace.objects.utils.tools import json_digger


class MPShopeeShopAddress(models.Model):
    _name = 'mp.shopee.shop.address'
    _inherit = 'mp.base'
    _description = 'Marketplace Shopee Shop Address'
    _rec_name = 'address'

    shop_id = fields.Many2one(comodel_name='mp.shopee.shop', string="Shop ID")
    address_id = fields.Char(string="Address_id", readonly=True)
    region = fields.Char(string="Shop Region", readonly=True)
    state = fields.Char(string="Shop State", readonly=True)
    city = fields.Char(string="Shop City", readonly=True)
    district = fields.Char(string="Shop District", readonly=True)
    town = fields.Char(string='Shop Town', readonly=True)
    address = fields.Text(string='Shop Address', readonly=True)
    zipcode = fields.Char(string='Shop Zipcode', readonly=True)
    is_default_address = fields.Boolean(string='Is Default Address ?', readonly=True)
    is_return_address = fields.Boolean(string='Is Return Address ?', readonly=True)
    is_pickup_address = fields.Boolean(string='Is Pickup Address ?', readonly=True)

    @classmethod
    def _add_rec_mp_field_mapping(cls, mp_field_mappings=None):
        if not mp_field_mappings:
            mp_field_mappings = []

        marketplace = 'shopee'
        mp_field_mapping = {
            'shop_id': ('shop_id', None),
            'mp_external_id': ('address_id', None),
            'address_id': ('address_id', None),
            'region': ('region', None),
            'state': ('state', None),
            'city': ('city', None),
            'town': ('town', None),
            'address': ('address', None),
            'zipcode': ('zipcode', None),
            'is_default_address': ('default_address', None),
            'is_return_address': ('return_address', None),
            'is_pickup_address': ('pickup_address', None),
        }
        mp_field_mappings.append((marketplace, mp_field_mapping))
        super(MPShopeeShopAddress, cls)._add_rec_mp_field_mapping(mp_field_mappings)

    @api.model
    def shopee_get_sanitizers(self, mp_field_mapping):
        default_sanitizer = self.get_default_sanitizer(mp_field_mapping)
        return {
            'shop_address_info': default_sanitizer
        }

    @api.model
    def generate_shop_address_data(self, mp_account, sp_order_raw):
        shop_address_list = []

        address_list = json_digger(sp_order_raw, 'shipping_paramater/pickup/address_list')
        for address in address_list:
            address_dict = {
                'shop_id': mp_account.sp_shop_id.id,
                'address_id': address.get('address_id'),
                'region': address.get('region'),
                'state': address.get('state'),
                'city': address.get('city'),
                'district': address.get('district'),
                'town': address.get('town'),
                'address': address.get('address'),
                'zipcode': address.get('zipcode'),
                'is_default_address': False,
                'is_return_address': False,
                'is_pickup_address': False,
            }

            if 'default_address' in address['address_flag']:
                address_dict.update({
                    'is_default_address': True
                })
            if 'pickup_address' in address['address_flag']:
                address_dict.update({
                    'is_pickup_address': True
                })
            if 'return_address' in address['address_flag']:
                address_dict.update({
                    'is_return_address': True
                })

            shop_address_list.append(address_dict)

        return shop_address_list
