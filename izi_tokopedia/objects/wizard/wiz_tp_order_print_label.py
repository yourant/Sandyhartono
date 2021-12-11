# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models

from odoo.addons.izi_marketplace.objects.utils.tools import mp
from odoo.addons.izi_tokopedia.objects.utils.tokopedia.order import TokopediaOrder


class WizardTokopediaOrderPrintLabel(models.TransientModel):
    _name = 'wiz.tp_order_print_label'
    _description = 'Tokopedia Order Print Label Wizard'

    order_ids = fields.Many2many(comodel_name="sale.order", relation="rel_order_print_label",
                                 column1="order_print_label_id", column2="order_id", string="Order(s)", required=True)
    mark_printed = fields.Boolean(string="Mark as Printed?", default=False)

    @mp.tokopedia.capture_error
    def print_label(self):
        orders = self.order_ids
        order_list_exid = []
        for order in orders:
            order_list_exid.append(order.mp_external_id)

        tp_account = orders[0].mp_account_id.tokopedia_get_account()
        tp_order = TokopediaOrder(tp_account, api_version="url")
        tp_order.endpoints.host = 'seller'
        label_url = tp_order.action_print_shipping_label(order_ids=order_list_exid, printed=int(self.mark_printed))
        return {
            'type': 'ir.actions.act_url',
            'url': label_url,
        }
