# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models


class MarketplaceProductWholesale(models.Model):
    _name = 'mp.product.wholesale'
    _inherit = 'mp.base'
    _description = 'Marketplace Product Wholesale'

    min_qty = fields.Integer(string="Minimal Qty")
    max_qty = fields.Integer(string="Maximal Qty")
    price = fields.Float(string="Sales Price", default=1.0, digits='Product Price')
    mp_product_id = fields.Many2one(comodel_name="mp.product", string="Marketplace Product", readonly=True,
                                    ondelete="cascade")
