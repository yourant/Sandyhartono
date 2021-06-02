# -*- coding: utf-8 -*-

from odoo import models, fields, api


class JuraganCampaignInit(models.AbstractModel):
    _name = 'juragan.campaign.init'
    _description = 'Juragan Campaign Init'
    
    @api.model
    def run(self):
        set_obj = self.env['res.config.settings']
        
        set_obj.create({
            'group_product_pricelist': True,
            'group_product_variant': True,
            'product_pricelist_setting': 'basic',
        }).execute()

        
class JuraganCampaign(models.Model):
    _name = 'juragan.campaign'
    _description = 'Campaign'
    
    name = fields.Char('Campaign Name', required=True)
    pricelist_ids = fields.Many2many('product.pricelist', string='Target Pricelist', default=lambda self:[(6, 0, self.env.ref('product.list0').ids)])
    currency_id = fields.Many2one('res.currency', 'Currency', default=lambda self:self.env.company.currency_id.id, required=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self:self.env.company.id)
    datetime_start = fields.Datetime('Start Date', required=True)
    datetime_end = fields.Datetime('End Date', required=True)
    compute_price = fields.Selection([
        ('fixed', 'Fixed Price'),
        ('percentage', 'Percentage (discount)'),
    ], default='percentage', required=True)
    fixed_price = fields.Float('Fixed Price', digits='Product Price')
    percent_price = fields.Float('Percentage Price')
    state = fields.Selection([
        ('draft', 'Planned'),
        ('done', 'Scheduled'),
        ('cancel', 'Canceled'),
    ], string='Status', default='draft', required=True)
    item_ids = fields.One2many('juragan.campaign.item', 'campaign_id', string='Line')
    mp_ids = fields.One2many('juragan.campaign.mp', 'campaign_id', string='Marketplace')
    
    def change_state(self):
        for rec in self.filtered(lambda r:r._context.get('state')):
            rec.write({'state': rec._context.get('state')})


class JuraganCampaignItem(models.Model):
    _name = 'juragan.campaign.item'
    _description = 'Campaign Item'
    
    campaign_id = fields.Many2one('juragan.campaign', string='Campaign')
    product_tmpl_id = fields.Many2one('product.template', 'Product', ondelete='cascade', check_company=True)
    product_id = fields.Many2one('product.product', 'Product Variant', ondelete='cascade', check_company=True)
    min_quantity = fields.Integer('Min. Quantity', default=0)
    max_quantity = fields.Integer('Max. Quantity', default=0)
    company_id = fields.Many2one('res.company', 'Company', readonly=True, related='campaign_id.company_id', store=True)
    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True, related='campaign_id.currency_id', store=True)
    compute_price = fields.Selection([
        ('global', 'Global Price'),
        ('fixed', 'Fixed Price'),
        ('percentage', 'Percentage (discount)'),
    ], default='global', required=True)
    fixed_price = fields.Float('Fixed Price', digits='Product Price')
    percent_price = fields.Float('Percentage Price')

    
class JuraganCampaignMP(models.Model):
    _name = 'juragan.campaign.mp'
    _description = 'Campaign Marketplace'
    
    campaign_id = fields.Many2one('juragan.campaign', string='Campaign')
    mp_id = fields.Reference([
        ('mp.tokopedia', 'Tokopedia'),
        ('mp.shopee', 'Shopee'),
        ('mp.lazada', 'Lazada'),
    ], string='Marketplace')
