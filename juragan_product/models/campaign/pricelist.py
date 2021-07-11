# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

from .campaign import JuraganCampaign


class ProductPricelistItem(models.Model):
    _inherit = 'product.pricelist.item'

    campaign_id = fields.Many2one("juragan.campaign", 'Campaign', index=True, ondelete='cascade')
    mp_id = fields.Reference(JuraganCampaign.MP_TYPES, string='Marketplace')
    price_campaign = fields.Char('Price', compute='_get_pricelist_item_name_price_campaign',
                                 help="Explicit rule name for this pricelist line.")
    campaign_purpose = fields.Selection(string="Campaign Purpose", selection=JuraganCampaign.CAMPAIGN_PURPOSE)

    # @api.one
    @api.depends('categ_id', 'product_tmpl_id', 'product_id', 'compute_price', 'fixed_price', 'campaign_id',
                 'percent_price', 'price_discount', 'price_surcharge')
    def _get_pricelist_item_name_price_campaign(self):
        self.ensure_one()
        if self.compute_price == 'fixed':
            self.price_campaign = "%s %s" % (self.fixed_price, self.campaign_id.currency_id.name)
        elif self.compute_price == 'percentage':
            self.price_campaign = _("%s %% discount") % self.percent_price
        else:
            self.price_campaign = _("%s %% discount and %s surcharge") % (self.price_discount, self.price_surcharge)
