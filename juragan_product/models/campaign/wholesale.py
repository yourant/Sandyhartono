# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ProductStagingWholesale(models.Model):
    _inherit = 'product.staging.wholesale'

    related_job_id = fields.Many2one(comodel_name="juragan.campaign.job", string="Related Job", required=False)
    initial_product_stg_id = fields.Many2one(comodel_name="product.staging", string="Initial Product Staging",
                                             required=False)
