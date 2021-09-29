# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
from odoo import fields, models, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta


class SetOpenWizard(models.TransientModel):

    _name = 'mp.get.order.wizard'

    order_start_date = fields.Datetime(string='Get Start Time Order', required=True,
                                       default=lambda self: fields.Datetime.to_string(
                                           datetime.now() - timedelta(days=3))
                                       )
    order_end_date = fields.Datetime(string='Get End Time Order', required=True, default=lambda self:
                                     fields.Datetime.to_string(datetime.now()))

    def get_order(self):
        mp_account_obj = self.env['mp.account']
        self.ensure_one()
        if self.order_end_date < self.order_start_date:
            raise UserError('End Datetime field must be higger from Start Datetime ..')
        else:
            if hasattr(mp_account_obj, '%s_get_orders' % self.env.context.get('marketplace')):
                getattr(mp_account_obj, '%s_get_orders' % self.env.context.get('marketplace'))()
