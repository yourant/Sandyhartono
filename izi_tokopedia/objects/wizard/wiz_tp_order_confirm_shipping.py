# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models

from odoo.addons.izi_marketplace.objects.utils.tools import mp
from odoo.addons.izi_tokopedia.objects.utils.tokopedia.order import TokopediaOrder


class WizardTokopediaOrderConfirmShipping(models.TransientModel):
    _name = 'wiz.tp_order_confirm_shipping'
    _description = 'Tokopedia Order Confirm Shipping Wizard'

    order_ids = fields.Many2many(comodel_name="sale.order",
                                 relation="rel_order_confirm_shipping",
                                 column1="order_confirm_shipping_id",
                                 column2="order_id",
                                 string="Order(s)", required=True)
    awb_number = fields.Char(string='AWB Number', required=True)

    @mp.tokopedia.capture_error
    def confirm(self):
        for order in self.order_ids:
            tp_account = order.mp_account_id.tokopedia_get_account()
            tp_order = TokopediaOrder(tp_account)

            kwargs = {
                'order_id': order.mp_external_id,
                'order_status': 500,
                'shipping_ref_num': self.awb_number
            }

            action_status = tp_order.action_confirm_shipping(**kwargs)
            if action_status == "Success":
                order.tokopedia_fetch_order()
