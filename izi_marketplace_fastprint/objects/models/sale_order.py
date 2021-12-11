# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    mp_order_weight = fields.Float(string="MP Order Weight (KG)", digits='Stock Weight',
                                   help="The weight of the contents in Kg, not including any packaging, etc.",
                                   compute='_calculate_product_weight')

    def _calculate_product_weight(self):
        for rec in self:
            rec.mp_order_weight = sum(rec.order_line.mapped('mp_product_weight'))

    @api.model
    def _finish_mapping_raw_data(self, sanitized_data, values):
        sanitized_data, values = super(SaleOrder, self)._finish_mapping_raw_data(sanitized_data, values)
        mp_account = self.get_mp_account_from_context()
        if mp_account.payment_term_id:
            values.update({
                'payment_term_id': mp_account.payment_term_id.id,
            })
        if mp_account.pricelist_id:
            values.update({
                'pricelist_id': mp_account.pricelist_id.id,
            })

        return sanitized_data, values

    @api.model
    def _finish_create_records(self, records):
        mp_account = self.get_mp_account_from_context()
        records = super(SaleOrder, self)._finish_create_records(records)
        for record in records:
            notes = []
            notes.append('- PAID VIA %s %s' % (mp_account.marketplace.upper(),
                                               mp_account.company_id.name.upper()))
            notes.append('- %s' % (record.mp_invoice_number))
            for delivery in record.order_line:
                if delivery.is_delivery:
                    price = "Rp{:,.0f}".format(delivery.price_unit)
                    delivery_text = '- Ongkos Kirim (%s kg) %s' % (str(record.mp_order_weight), price)
                    notes.append(delivery_text)

            note = '\n'.join(notes)
            record.write({'note': note})

        return records
