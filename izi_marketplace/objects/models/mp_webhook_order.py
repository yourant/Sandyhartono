# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class MPWebhookOrder(models.Model):
    _name = 'mp.webhook.order'
    _description = 'Marketplace Account'
    _inherit = ['mp.base']
    _rec_mp_order_statuses = {}
    _rec_mp_order_status_notes = {}
    _rec_name = 'mp_invoice_number'

    MP_ORDER_STATUSES = [
        ('new', 'New'),
        ('waiting', 'Waiting Payment'),
        ('to_cancel', 'To Cancel'),
        ('cancel', 'Cancelled'),
        ('to_process', 'To Process'),
        ('in_process', 'In Process'),
        ('to_ship', 'To Ship'),
        ('in_ship', 'In Shipping'),
        ('done', 'Done'),
        ('return', 'Returned'),
    ]

    mp_invoice_number = fields.Char(string='Marketplace Invoice Number')
    mp_account_id = fields.Many2one(comodel_name='mp.account', string='Marketplace Account')
    order_create_time = fields.Datetime(string='Order Create Time')
    order_update_time = fields.Datetime(string='Order Update Time')
    mp_order_status = fields.Selection(string="MP Order Status", selection=MP_ORDER_STATUSES, required=False,
                                       store=True, compute="_compute_mp_order_status")
    mp_order_status_notes = fields.Char(string="MP Order Status Notes", compute="_compute_mp_order_status")

    @classmethod
    def _build_model_attributes(cls, pool):
        super(MPWebhookOrder, cls)._build_model_attributes(pool)
        cls._add_rec_mp_order_status()

    @classmethod
    def _add_rec_mp_order_status(cls, mp_order_statuses=None, mp_order_status_notes=None):
        if mp_order_statuses:
            cls._rec_mp_order_statuses = dict(cls._rec_mp_order_statuses, **dict(mp_order_statuses))
        if mp_order_status_notes:
            cls._rec_mp_order_status_notes = dict(cls._rec_mp_order_status_notes, **dict(mp_order_status_notes))

    @api.multi
    def _compute_mp_order_status(self):
        for order in self:
            if order.marketplace not in order._rec_mp_order_statuses.keys():
                order.mp_order_status = False
            else:
                mp_order_status_field, mp_order_statuses = order._rec_mp_order_statuses[order.marketplace]
                mp_order_status_value = 'new'
                for mp_order_status, mp_order_status_codes in mp_order_statuses.items():
                    if getattr(order, mp_order_status_field) in mp_order_status_codes:
                        mp_order_status_value = mp_order_status
                        break
                order.mp_order_status = mp_order_status_value

            if order.marketplace not in order._rec_mp_order_status_notes.keys():
                order.mp_order_status_notes = False
            else:
                mp_order_status_notes = order._rec_mp_order_status_notes[order.marketplace]
                if order.mp_order_status:
                    default_notes = 'Status code "%s" is not registered in our apps, it may be new status code added ' \
                                    'by %s. Please report this to our developer team! ' % (
                                        order.mp_order_status, order.marketplace.upper())
                    order.mp_order_status_notes = mp_order_status_notes.get(order.mp_order_status, default_notes)
                else:
                    order.mp_order_status_notes = False
