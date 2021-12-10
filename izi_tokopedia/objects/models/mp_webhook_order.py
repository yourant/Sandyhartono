# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class MPWebhookOrder(models.Model):
    _inherit = 'mp.webhook.order'

    TP_ORDER_STATUSES = [
        ('0', 'Seller cancel order.'),
        ('2', 'Order Reject Replaced.'),
        ('3', 'Order Reject Due Empty Stock.'),
        ('4', 'Order Reject Approval.'),
        ('5', 'Order Canceled by Fraud'),
        ('6', 'Order Rejected (Auto Cancel Out of Stock)'),
        ('10', 'Order rejected by seller.'),
        ('11', 'Order Pending Replacement.'),
        ('15', 'Instant Cancel by Buyer.'),
        ('100', 'Pending order.'),
        ('103', 'Wait for payment confirmation from third party.'),
        ('200', 'Payment confirmation.'),
        ('220', 'Payment verified, order ready to process.'),
        ('221', 'Waiting for partner approval.'),
        ('400', 'Seller accept order.'),
        ('401', 'Buyer Request Cancel'),
        ('450', 'Waiting for pickup.'),
        ('500', 'Order shipment.'),
        ('501', 'Status changed to waiting resi have no input.'),
        ('520', 'Invalid shipment reference number (AWB).'),
        ('530', 'Requested by user to correct invalid entry of shipment reference number.'),
        ('540', 'Delivered to Pickup Point.'),
        ('550', 'Return to Seller.'),
        ('600', 'Order delivered.'),
        ('601', 'Buyer open a case to finish an order.'),
        ('690', 'Fraud Review'),
        ('691', 'Suspected Fraud'),
        ('695', 'Post Fraud Review'),
        ('698', 'Finish Fraud Review'),
        ('699', 'Order invalid or shipping more than 25 days and payment more than 5 days.'),
        ('700', 'Order finished.'),
        ('701', 'Order assumed as finished but the product not arrived yet to the buyer.')
    ]

    tp_order_id = fields.Char(string="Tokopedia Order ID", required_if_marketplace="tokopedia")
    tp_order_status = fields.Selection(string="Tokopedia Order Status", selection=TP_ORDER_STATUSES,
                                       required_if_marketplace="tokopedia")

    @classmethod
    def _add_rec_mp_order_status(cls, mp_order_statuses=None, mp_order_status_notes=None):
        if not mp_order_statuses:
            mp_order_statuses = []
        if not mp_order_status_notes:
            mp_order_status_notes = []

        marketplace, tp_order_status_field = 'tokopedia', 'tp_order_status'
        tp_order_statuses = {
            'waiting': ['11', '100', '103', '200'],
            'to_cancel': ['401'],
            'cancel': ['0', '2', '3', '4', '5', '10', '15', '690', '691', '695', '698', '699'],
            'to_process': ['220', '221'],
            'in_process': [],
            'to_ship': ['400'],
            'in_ship': ['450', '500', '501', '520', '530', '540'],
            'done': ['600', '601', '700', '701'],
            'return': ['550']
        }
        mp_order_statuses.append((marketplace, (tp_order_status_field, tp_order_statuses)))
        mp_order_status_notes.append((marketplace, dict(cls.TP_ORDER_STATUSES)))
        super(MPWebhookOrder, cls)._add_rec_mp_order_status(mp_order_statuses, mp_order_status_notes)

    # @api.multi
    @api.depends('tp_order_status')
    def _compute_mp_order_status(self):
        super(MPWebhookOrder, self)._compute_mp_order_status()

    # @classmethod
    # def _add_rec_mp_external_id(cls, mp_external_id_fields=None):
    #     if not mp_external_id_fields:
    #         mp_external_id_fields = []

    #     mp_external_id_fields.append(('tokopedia', 'tp_order_id'))
    #     super(MPWebhookOrder, cls)._add_rec_mp_external_id(mp_external_id_fields)
