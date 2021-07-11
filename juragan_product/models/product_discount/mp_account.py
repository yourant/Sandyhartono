# -*- coding: utf-8 -*-
from odoo import api, fields, models


class MPTokopedia(models.Model):
    _inherit = 'mp.tokopedia'

    product_discount_ids = fields.One2many('mp.product.discount', 'mp_tokopedia_id', string='Product Discount')


class MPShopee(models.Model):
    _inherit = 'mp.shopee'

    product_discount_ids = fields.One2many('mp.product.discount', 'mp_shopee_id', string='Product Discount')
