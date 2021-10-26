# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import fields, models


class ProductBonus(models.Model):
    _name = 'product.bonus.config'
    _description = 'Product Bonus'

    name = fields.Char(string="Name")
    active = fields.Boolean(string="Active")
    date_start = fields.Datetime('Start Date')
    date_end = fields.Datetime('End Date')
    mp_tokopedia_ids = fields.Many2many(comodel_name="mp.tokopedia", string="Tokopedia Accounts")
    mp_shopee_ids = fields.Many2many(comodel_name="mp.shopee", string="Shopee Accounts")
    mp_lazada_ids = fields.Many2many(comodel_name="mp.lazada", string="Lazada Accounts")
    mp_blibli_ids = fields.Many2many(comodel_name="mp.blibli", string="Blibli Accounts")
    product_ref_id = fields.Many2one(comodel_name="product.product", string="Product Reference")
    min_qty = fields.Integer(string="Minimum Quantity", default=1)
    product_line_ids = fields.One2many(comodel_name="product.bonus.line", inverse_name="product_bonus_config_id", string="Product Bonus Lines")    


class ProductBonusLine(models.Model):
    _name = 'product.bonus.line'
    _description = 'Product Bonus Line'

    product_bonus_config_id = fields.Many2one(comodel_name="product.bonus.config", string="Product Bonus Config")
    quantity = fields.Integer(string="Quantity", default=1)
    product_id = fields.Many2one(comodel_name="product.product", string="Product Line")


class ProductProduct(models.Model):
    _inherit = 'product.product'

    product_bonus_config_id = fields.One2many(comodel_name="product.bonus.config", inverse_name="product_ref_id", string="Product Reference")
    product_bonus_line_id = fields.One2many(comodel_name="product.bonus.line", inverse_name="product_id", string="Product Bonus Line")