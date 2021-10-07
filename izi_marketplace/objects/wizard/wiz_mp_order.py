# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from dateutil.relativedelta import relativedelta
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class WizardMPOrder(models.TransientModel):
    _name = 'wiz.mp.order'
    _description = 'Wizard Marketplace Order'

    INTERVAL_TYPES = [
        ('days', 'Day(s)'),
        ('weeks', 'Week(s)'),
        ('months', 'Month(s)'),
    ]

    mp_account_id = fields.Many2one(comodel_name="mp.account", string="MP Account", required=True)
    use_interval = fields.Boolean(string="Use Interval?", default=True)
    interval = fields.Integer(string="Interval", required=False, default=3)
    interval_type = fields.Selection(string="Interval Type", selection=INTERVAL_TYPES, required=False, default="days")
    from_date = fields.Datetime(string="From Date", required=True)
    to_date = fields.Datetime(string="To Date", required=True)

    @api.onchange('interval', 'interval_type')
    def onchange_interval(self):
        interval = dict([(self.interval_type, self.interval)])
        time_delta = relativedelta(**interval)
        now = fields.Datetime.from_string(fields.Datetime.now())
        self.from_date = fields.Datetime.to_string(now - time_delta)
        self.to_date = fields.Datetime.to_string(now)

    def get_order(self):
        from_date = fields.Datetime.from_string(self.from_date)
        to_date = fields.Datetime.from_string(self.to_date)
        if from_date > to_date:
            raise ValidationError("Invalid date range, from_date higher than to_date. Please input correct date range!")
        if hasattr(self.mp_account_id, '%s_get_orders' % self.mp_account_id.marketplace):
            getattr(self.mp_account_id, '%s_get_orders' % self.mp_account_id.marketplace)(from_date=from_date,
                                                                                          to_date=to_date)

        return {
            'type': 'ir.actions.client',
            'tag': 'close_notifications',
            'params': {
                'force_show_number': 1
            }
        }
