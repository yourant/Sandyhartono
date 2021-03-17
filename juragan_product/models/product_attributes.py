# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductAttributeUnit(models.Model):
    _name = 'product.attribute.unit'
    _description = 'Product Attribute Unit'

    name = fields.Char()
    attribute_id = fields.Many2one('product.attribute')
    mp_tokopedia_category_unit_id = fields.Many2one(
        'mp.tokopedia.category.unit', string='Tokopedia Category Unit')
    value_ids = fields.One2many('product.attribute.value', 'unit_id')

    izi_id = fields.Integer('Izi ID')
    izi_md5 = fields.Char()
