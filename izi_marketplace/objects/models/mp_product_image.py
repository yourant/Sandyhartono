# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models


class MarketplaceProductImage(models.Model):
    _name = 'mp.product.image'
    _inherit = 'mp.base'
    _description = 'Marketplace Product Image'
    _rec_mp_external_id = {}

    sequence = fields.Integer(string="Sequence", default=1)
    name = fields.Char(string="Image URL", readonly=True)
    image = fields.Binary('Image', attachment=True)
    mp_product_id = fields.Many2one(comodel_name="mp.product", string="Marketplace Product", readonly=True,
                                    ondelete="restrict")
