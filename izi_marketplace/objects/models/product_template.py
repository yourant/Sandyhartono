# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    map_line_ids = fields.One2many(comodel_name="mp.map.product.line", inverse_name="product_tmpl_id",
                                   string="Mapped Lines", readonly=True)
