# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sequence_product_default_code = fields.Many2one(related="company_id.sequence_product_default_code", readonly=False)
