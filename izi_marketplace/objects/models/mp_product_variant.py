# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models
from odoo.addons import decimal_precision as dp


class MarketplaceProductVariant(models.Model):
    _name = 'mp.product.variant'
    _inherit = 'mp.base'
    _description = 'Marketplace Product Variant'
    _rec_mp_external_id = {}

    name = fields.Char(string="Product Variant Name", readonly=True)
    default_code = fields.Char(string="Internal Reference")
    list_price = fields.Float(string="Sales Price", default=1.0, digits=dp.get_precision('Product Price'),
                              help="Base price to compute the customer price. Sometimes called the catalog price.")
    mp_product_id = fields.Many2one(comodel_name="mp.product", string="Marketplace Product", readonly=True)
