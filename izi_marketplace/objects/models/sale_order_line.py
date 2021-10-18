# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SaleOrderLine(models.Model):
    _name = 'sale.order.line'
    _inherit = ['sale.order.line', 'mp.base']

    mp_account_id = fields.Many2one(required=False)
    is_insurance = fields.Boolean(string="Is a Insurance", default=False)
    is_global_discount = fields.Boolean(string="Is a Global Discount", default=False)
    is_adjustment = fields.Boolean(string="Is a Adjustment", default=False)

    @api.model
    def _finish_mapping_raw_data(self, sanitized_data, values):
        sanitized_data, values = super(SaleOrderLine, self)._finish_mapping_raw_data(sanitized_data, values)

        if not values.get('product_id'):
            err_msg = 'Could not find matched record for MP Product "%s", please make sure this MP Product is mapped!'
            raise ValidationError(err_msg % values['name'])

        return sanitized_data, values
