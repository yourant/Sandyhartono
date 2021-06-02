# -*- coding: utf-8 -*-

from odoo import api, fields, models


class Company(models.Model):
    _inherit = 'res.company'

    sequence_product_default_code = fields.Many2one(comodel_name="ir.sequence", string="Product Default Code Sequence")
