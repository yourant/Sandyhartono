# -*- coding: utf-8 -*-
from odoo import api, fields, models


class MPProductDiscount(models.Model):
    _inherit = 'mp.product.discount'

    SHOPEE_DISCOUNT_STATUS = [
        ('ongoing', 'ONGOING'),
        ('expired', 'EXPIRED'),
        ('upcoming', 'UPCOMING'),
    ]

    sp_discount_status = fields.Selection(SHOPEE_DISCOUNT_STATUS)
    mp_shopee_id = fields.Many2one('mp.shopee', string='Shopee Account')


class MPProductDiscountLine(models.Model):
    _inherit = 'mp.product.discount.line'

    sp_normal_stock = fields.Integer(string='Shopee Normal Stock')
