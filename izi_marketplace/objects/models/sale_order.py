# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models


class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = ['sale.order', 'mp.base']
    _rec_mp_order_statuses = {}
    _rec_mp_order_status_notes = {}

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

    mp_account_id = fields.Many2one(required=False)
    mp_order_status = fields.Selection(string="MP Order Status", selection=MP_ORDER_STATUSES, required=False,
                                       compute="_compute_mp_order_status")
    mp_order_status_notes = fields.Char(string="MP Order Status Notes", compute="_compute_mp_order_status")
    mp_invoice_number = fields.Char(string="MP Invoice Number", required=False)
    mp_payment_method_info = fields.Char(string='Payment Method', required=False, readonly=True)
    mp_awb_number = fields.Char(string='AWB Number', required=False)
    mp_awb_url = fields.Text(string='AWB URL', required=False, readonly=True)

    mp_buyer_id = fields.Integer(string="Buyer ID", readonly=True)
    mp_buyer_username = fields.Char(string='Buyer Username', readonly=True)
    mp_buyer_name = fields.Char(string='Buyer Name', readonly=True)
    mp_buyer_email = fields.Char(string='Buyer Email', readonly=True)
    mp_buyer_phone = fields.Char(string='Buyer Phone', readonly=True)
    mp_cancel_reason = fields.Char(string='Order Cancel Reason', readonly=True)

    mp_recipient_address_city = fields.Char(string='Recipient City', readonly=True)
    mp_recipient_address_name = fields.Char(string='Recipient Name', readonly=True)
    mp_recipient_address_district = fields.Char(string='Recipient District', readonly=True)
    mp_recipient_address_country = fields.Char(string='Recipient Country', readonly=True)
    mp_recipient_address_zipcode = fields.Char(string='Recipient Zipcode', readonly=True)
    mp_recipient_address_phone = fields.Char(string='Recipient Phone', readonly=True)
    mp_recipient_address_state = fields.Char(string='Recipient State', readonly=True)
    mp_recipient_address_full = fields.Text(string='Recipient Full Address', readonly=True)

    mp_delivery_carrier_name = fields.Char(string='Delivery Name', readonly=True)
    mp_delivery_carrier_type = fields.Char(string='Delivery Carrier Type', readonly=True)
    mp_delivery_type = fields.Selection([
        ('pickup', 'Pickup'),
        ('drop off', 'Drop Off'),
        ('both', 'Pickup & Drop Off'),
        ('send_to_warehouse', 'Send to Warehouse')])
    mp_accept_deadline = fields.Datetime(string='Maximum Confirmation Date', readonly=True)
    mp_shipping_deadline = fields.Datetime(string='Maximum Shpping Date', readonly=True)
    mp_delivery_weight = fields.Float(string='Weight (KG)', readonly=True)

    @classmethod
    def _build_model_attributes(cls, pool):
        super(SaleOrder, cls)._build_model_attributes(pool)
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
