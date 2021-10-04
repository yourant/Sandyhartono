# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
from odoo import fields, models, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta


class MPOrderWizard(models.TransientModel):

    _name = 'wiz.mp.get.order'

    mp_account_id = fields.Many2one(comodel_name='mp.account', string='MP Account')
    order_start_date = fields.Datetime(string='Get Start Time Order', required=True,
                                       default=lambda self: fields.Datetime.to_string(
                                           datetime.now() - timedelta(days=3))
                                       )
    order_end_date = fields.Datetime(string='Get End Time Order', required=True, default=lambda self:
                                     fields.Datetime.to_string(datetime.now()))

    def get_order(self):
        self.ensure_one()
        if self.order_end_date < self.order_start_date:
            raise UserError('End Datetime field must be higger from Start Datetime ..')
        else:
            if hasattr(self.mp_account_id, '%s_get_orders' % self.env.context.get('marketplace')):
                getattr(self.mp_account_id, '%s_get_orders' % self.env.context.get('marketplace'))(
                    date_from=self.order_start_date, date_to=self.order_end_date)
