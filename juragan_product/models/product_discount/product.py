# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ProductStaging(models.Model):
    _inherit = 'product.staging'

    product_discount_ids = fields.One2many('mp.product.discount.line', 'product_stg_id', string='Product Discount')
