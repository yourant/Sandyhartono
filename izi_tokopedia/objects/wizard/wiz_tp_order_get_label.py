# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models

from odoo.addons.izi_marketplace.objects.utils.tools import mp
from odoo.addons.izi_tokopedia.objects.utils.tokopedia.order import TokopediaOrder


class WizardTokopediaOrderGetLabel(models.TransientModel):
    _name = 'wiz.tp_order_get_label'
    _description = 'Tokopedia Order Get Label Wizard'

    order_ids = fields.Many2many(comodel_name="sale.order", relation="rel_order_get_label",
                                 column1="order_get_label_id", column2="order_id", string="Order(s)", required=True)
    mark_printed = fields.Boolean(string="Mark as Printed?", default=False)

    @mp.tokopedia.capture_error
    def get_label(self):
        context = self._context
        orders = self.order_ids

        if not context.get('multi'):
            order = orders.ensure_one()

            tp_account = order.mp_account_id.tokopedia_get_account()
            tp_order = TokopediaOrder(tp_account, api_version="url")
            tp_order.endpoints.host = 'seller'
            label_url = tp_order.action_get_shipping_label(order_ids=[order.mp_external_id],
                                                           printed=int(self.mark_printed))
            return {
                'type': 'ir.actions.act_url',
                'url': label_url,
            }
