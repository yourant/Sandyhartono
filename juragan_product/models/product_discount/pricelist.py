# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

from ..campaign.campaign import JuraganCampaign as BaseJuraganCampaign

from .campaign import JuraganCampaign


class ProductPricelistItem(models.Model):
    _inherit = 'product.pricelist.item'

    campaign_purpose = fields.Selection(selection_add=JuraganCampaign.CAMPAIGN_PURPOSE)
    discount_line_id = fields.Many2one(comodel_name="mp.product.discount.line", string="Marketplace Discount",
                                       required=False)
    discount_line_data_md5 = fields.Char()
    reserved_stock = fields.Integer(string='Reserved Quantity')
    max_order = fields.Integer(string='Purchase Limit')

    def _prepare_discount_line_values_from_campaign_rule(self):
        self.ensure_one()

        # Get product stagings based on product tmpl and mp account
        product_stgs = self.product_tmpl_id.product_staging_ids
        if not product_stgs:
            raise UserError("This product doesn't have product staging!")

        if self.mp_id._name == 'mp.tokopedia':
            product_stgs = product_stgs.filtered(lambda ps: ps.mp_tokopedia_id == self.mp_id)
        elif self.mp_id._name == 'mp.shopee':
            product_stgs = product_stgs.filtered(lambda ps: ps.mp_shopee_id == self.mp_id)
        else:
            raise UserError(
                "This marketplace account is not supported yet: %s" % BaseJuraganCampaign.MP_TYPES[
                    self.mp_id._name])

        if not product_stgs:
            raise UserError(
                "No marketplace account match with this product staging: %s" % product_stgs.mapped('name'))

        # NEED SOLUTION: How to handle multiple product staging with same marketplace account in one product tmpl?
        product_stg = product_stgs[0]

        discounted_price = self.fixed_price
        if self.compute_price == 'percentage':
            discount_amount = (self.percent_price / 100) * product_stg.list_price
            discounted_price = product_stg.list_price - discount_amount

        discount_line_value = {
            'product_stg_id': product_stg.id,
            'discount_id': self.campaign_id.discount_id.id,
            'discounted_price': discounted_price,
            'reserved_stock': self.reserved_stock,
            'max_order': self.max_order
        }

        return discount_line_value

    def _create_discount_lines(self):

        product_discount_line_obj = self.env['mp.product.discount.line']

        for pli in self:
            discount_line_value = pli._prepare_discount_line_values_from_campaign_rule()
            discount_line = product_discount_line_obj.create(discount_line_value)
            pli.write({'discount_line_id': discount_line.id})

        return self.mapped('discount_line_id')
