# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models


class MarketplaceAccount(models.Model):
    _inherit = 'mp.account'

    payment_term_id = fields.Many2one('account.payment.term', string='Default Payment Terms', oldname='payment_term')
    pricelist_id = fields.Many2one('product.pricelist', string='Default Pricelist')
