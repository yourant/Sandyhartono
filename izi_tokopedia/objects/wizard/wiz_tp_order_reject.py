# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.izi_marketplace.objects.utils.tools import mp
from odoo.addons.izi_tokopedia.objects.utils.tokopedia.order import TokopediaOrder


class WizardTokopediaOrderReject(models.TransientModel):
    _name = 'wiz.tp_order_reject'
    _description = 'Tokopedia Order Reject Wizard'

    REJECT_REASONS = [
        ('1', 'Product(s) out of stock'),
        ('2', 'Product variant unavailable'),
        ('3', 'Wrong price or weight'),
        ('4', 'Shop closed.'),
        ('5', 'Others'),
        ('7', 'Courier problem'),
        ('8', "Buyer's request")
    ]

    order_ids = fields.Many2many(comodel_name="sale.order", relation="rel_order_reject_sale_order",
                                 column1="order_reject_id", column2="order_id", string="Order(s)", required=True)
    reason_code = fields.Selection(string="Tokopedia Reason Code", selection=REJECT_REASONS, required=True)
    reason = fields.Text(string="Tokopedia Reason", required=True)
    shop_close_end_date = fields.Date(string="Shop Close End Date", required=False)
    shop_close_note = fields.Text(string="Shop Close Note", required=False)

    @api.constrains('reason')
    def _check_reason_length(self):
        """ If the reason code is "Courier problem" or "Buyer’s request", then the reason max length is 490 char(s)."""
        if self.reason_code in ['7', '8'] and len(self.reason) > 490:
            raise ValidationError("Reason max length is 490 char(s), you've %d char(s)" % len(self.reason))

    @mp.tokopedia.capture_error
    def confirm(self):
        for order in self.order_ids:
            tp_account = order.mp_account_id.tokopedia_get_account()
            tp_order = TokopediaOrder(tp_account)

            kwargs = {
                'order_id': order.mp_external_id,
                'reason_code': self.reason_code,
                'reason': self.reason
            }

            if self.reason_code == '4':
                kwargs.update({
                    'shop_close_end_date': fields.Date.from_string(self.shop_close_end_date).strftime("%d/%m/%Y"),
                    'shop_close_note': self.shop_close_note
                })

            action_status = tp_order.action_reject_order(**kwargs)
            if action_status == "success":
                order.action_cancel()
                order.tokopedia_fetch_order()
