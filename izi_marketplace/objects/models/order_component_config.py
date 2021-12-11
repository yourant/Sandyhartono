# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class OrderComponentConfig(models.Model):
    _name = 'order.component.config'
    _description = 'Marketplace Order Component Config'

    name = fields.Char('Name')
    mp_account_ids = fields.Many2many('mp.account', string='Marketplace Accounts')
    line_ids = fields.One2many('order.component.config.line', 'config_id', 'Discount Details')
    active = fields.Boolean('Active', default=False)


class OrderComponentConfigLine(models.Model):
    _name = 'order.component.config.line'
    _description = 'Marketplace Order Component Config Line'

    name = fields.Char('Name')
    config_id = fields.Many2one('order.component.config')
    component_type = fields.Selection([
        ('add_product', 'Add Product'),
        ('remove_product', 'Remove Product'),
        ('tax_line', 'Add Tax Line (Included in Order Price)')], string='Component Type', required=True)
    # remove_product
    remove_product_ids = fields.Many2many('product.product', string='Products to Remove')
    remove_insurance = fields.Boolean('Remove Insurance')
    remove_delivery = fields.Boolean('Remove Delivery')
    remove_discount = fields.Boolean('Remove Discount')
    remove_adjustment = fields.Boolean('Remove Adjustment')
    # add_product
    additional_product_id = fields.Many2one('product.product', 'Additional Product')
    # tax_line
    account_tax_id = fields.Many2one('account.tax', string='Sales Tax', domain=[('type_tax_use', '=', 'sale')])
    account_tax_ids = fields.Many2many('account.tax', string='Sales Taxes', domain=[
                                       ('type_tax_use', '=', 'sale')])  # Deprecated

    percentage_value = fields.Float('Percentage (%)')
    fixed_value = fields.Float('Fixed Value')
