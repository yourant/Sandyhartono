# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    mp_product_weight = fields.Float(string="MP Product Weight", digits='Stock Weight',
                                     help="The weight of the contents in Kg, not including any packaging, etc.")

    @api.model
    def _finish_create_records(self, records):
        records = super(SaleOrderLine, self)._finish_create_records(records)
        for record in records:
            record.mp_product_weight = record.mp_product_weight * record.product_uom_qty

        return records

    @api.model
    def _finish_update_records(self, records):
        records = super(SaleOrderLine, self)._finish_update_records(records)
        for record in records:
            record.mp_product_weight = record.mp_product_weight * record.product_uom_qty

        return records
