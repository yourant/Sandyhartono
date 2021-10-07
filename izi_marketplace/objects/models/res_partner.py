# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models


class SaleOrder(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner']

    buyer_id = fields.Integer(string="Buyer ID", readonly=True) 
    buyer_username = fields.Char(string='Buyer Username', readonly=True)
