# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    mp_product_weight = fields.Float(string="MP Product Weight", digits='Stock Weight',
                                     help="The weight of the contents in Kg, not including any packaging, etc.")
