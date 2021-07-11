# -*- coding: utf-8 -*-
from odoo import api, fields, models

from odoo.addons import decimal_precision as dp


class ProductStagingPrice(models.Model):
    _name = 'product.staging.price'
    _description = 'Product Staging Price'

    product_stg_id = fields.Many2one(comodel_name="product.staging", string="Product Staging", required=True,
                                     ondelete="cascade")
    related_job_id = fields.Many2one(comodel_name="juragan.campaign.job", string="Related Job", required=True,
                                     ondelete="cascade")
    initial_list_price = fields.Float('Initial Sales Price', digits=dp.get_precision('Product Price'))


class ProductStaging(models.Model):
    _inherit = 'product.staging'

    # @api.multi
    def _create_price(self, related_job):
        product_stg_price_obj = self.env['product.staging.price']
        product_stg_prices = product_stg_price_obj
        for product_stg in self:
            product_stg_prices |= product_stg_price_obj.create({
                'product_stg_id': product_stg.id,
                'related_job_id': related_job.id,
                'initial_list_price': product_stg.list_price
            })
        return product_stg_prices
