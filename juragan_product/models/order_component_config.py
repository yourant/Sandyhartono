from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class OrderComponentConfig(models.Model):
    _name = 'order.component.config'

    name = fields.Char('Name')
    mp_tokopedia_ids = fields.Many2many('mp.tokopedia', string='Tokopedia Accounts')
    mp_shopee_ids = fields.Many2many('mp.shopee', string='Shopee Accounts')
    mp_lazada_ids = fields.Many2many('mp.lazada', string='Lazada Accounts')
    mp_blibli_ids = fields.Many2many('mp.blibli', string='Blibli Accounts')
    line_ids = fields.One2many('order.component.config.line', 'config_id', 'Discount Details')
    date_start = fields.Datetime('Start Date')
    date_end = fields.Datetime('End Date')
    active = fields.Boolean('Active', default=False)

class OrderComponentConfigLine(models.Model):
    _name = 'order.component.config.line'

    name = fields.Char('Name')
    config_id = fields.Many2one('order.component.config')
    component_type = fields.Selection([
        ('add_product', 'Add Product'),
        ('remove_product', 'Remove Product'),
        ('discount_line', 'Add Discount Line'),
        ('tax_line', 'Add Tax Line (Included in Order Price)'),], string='Component Type', required=True)
    # remove_product
    remove_product_ids = fields.Many2many('product.product', relation='remove_product_rel', string='Products to Remove')
    remove_insurance = fields.Boolean('Remove Insurance')
    remove_delivery = fields.Boolean('Remove Delivery')
    remove_discount = fields.Boolean('Remove Discount')
    remove_adjustment = fields.Boolean('Remove Adjustment')
    # add_product
    additional_product_id = fields.Many2one('product.product', 'Additional Product')
    # discount_line
    discount_line_method = fields.Selection([
        ('input', 'Input Manually (Exclude from Price in Product)'),
        ('calculated', 'Calculated Order Price from Price in Product'),
        ('campaign', 'Get From Active Campaign'),], string='Discount Calculation')
    discount_line_product_type = fields.Selection([
        ('all', 'All Products'),
        ('specific', 'Specific Products'),], string='All / Specific Products')
    discount_line_product_ids = fields.Many2many('product.product', string='Apply to Products')
    # tax_line
    account_tax_id = fields.Many2one('account.tax', string='Sales Tax', domain=[('type_tax_use', '=', 'sale')])
    account_tax_ids = fields.Many2many('account.tax', string='Sales Taxes', domain=[('type_tax_use', '=', 'sale')]) # Deprecated

    percentage_value = fields.Float('Percentage (%)')
    fixed_value = fields.Float('Fixed Value')
