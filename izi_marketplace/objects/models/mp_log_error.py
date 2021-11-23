# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class MPLogError(models.Model):
    _name = 'mp.log.error'
    _order = 'id desc'

    name = fields.Char(string='Marketplace Error Message')
    model_name = fields.Char(string='Model Name')
    mp_log_status = fields.Selection([("success", "Success"), ("failed", "Failed")],
                                     default='failed', string='Marketplace Log Status')
    mp_external_id = fields.Char(string='Marketplace External ID')
    mp_account_id = fields.Many2one(comodel_name='mp.account', string='Marketplace Account')
    notes = fields.Char(string='Notes')
    last_retry_time = fields.Datetime(string='Last Retry')

    def retry_get_record(self):
        for log in self:
            if log.mp_log_status == 'failed':
                if log.model_name == 'sale.order.line' or log.model_name == 'sale.order':
                    wiz_mp_order_obj = self.env['wiz.mp.order']
                    wiz_mp_order = wiz_mp_order_obj.create({
                        'mp_account_id': log.mp_account_id.id,
                        'params': 'by_mp_invoice_number',
                        'mp_invoice_number': log.mp_external_id
                    })
                    wiz_mp_order.get_order()
