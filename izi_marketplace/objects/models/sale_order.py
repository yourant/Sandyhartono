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

    MP_DELIVERY_TYPES = [
        ('pickup', 'Pickup'),
        ('drop off', 'Drop Off'),
        ('both', 'Pickup & Drop Off'),
        ('send_to_warehouse', 'Send to Warehouse')
    ]

    # MP Account
    mp_account_id = fields.Many2one(required=False)

    # MP Order Status
    mp_order_status = fields.Selection(string="MP Order Status", selection=MP_ORDER_STATUSES, required=False,
                                       store=True, compute="_compute_mp_order_status")
    mp_order_status_notes = fields.Char(string="MP Order Status Notes", compute="_compute_mp_order_status")

    # MP Order Transaction & Payment
    mp_invoice_number = fields.Char(string="MP Invoice Number", required=False)
    mp_payment_method_info = fields.Char(string="Payment Method", required=False, readonly=True)
    mp_payment_date = fields.Datetime(string="Order Payment Date", readonly=True)
    mp_order_date = fields.Datetime(string="Order Date", readonly=True)
    mp_order_last_update_date = fields.Datetime(string="Order Last Update Date", readonly=True)
    mp_accept_deadline = fields.Datetime(string="Maximum Confirmation Date", readonly=True)
    mp_cancel_reason = fields.Char(string='Order Cancel Reason', readonly=True)
    mp_order_notes = fields.Text(string='Order Notes', readonly=True)

    # MP Order Shipment
    mp_awb_number = fields.Char(string="AWB Number", required=False)
    mp_awb_url = fields.Text(string="AWB URL", required=False, readonly=True)
    mp_delivery_carrier_name = fields.Char(string="Delivery Carrier Name", readonly=True)
    mp_delivery_carrier_type = fields.Char(string="Delivery Carrier Type", readonly=True)
    mp_delivery_type = fields.Selection(string="Delivery Type", selection=MP_DELIVERY_TYPES, required=False)
    mp_shipping_deadline = fields.Datetime(string="Maximum Shpping Date", readonly=True)
    mp_delivery_weight = fields.Float(string="Weight (KG)", readonly=True)

    # MP Buyer Info
    mp_buyer_id = fields.Integer(string="Buyer ID", readonly=True)
    mp_buyer_username = fields.Char(string="Buyer Username", readonly=True)
    mp_buyer_name = fields.Char(string="Buyer Name", readonly=True)
    mp_buyer_email = fields.Char(string="Buyer Email", readonly=True)
    mp_buyer_phone = fields.Char(string="Buyer Phone", readonly=True)

    # MP Recipient Info
    mp_recipient_address_name = fields.Char(string="Recipient Name", readonly=True)
    mp_recipient_address_phone = fields.Char(string="Recipient Phone", readonly=True)
    mp_recipient_address_full = fields.Text(string="Recipient Full Address", readonly=True)
    mp_recipient_address_district = fields.Char(string="Recipient District", readonly=True)
    mp_recipient_address_city = fields.Char(string="Recipient City", readonly=True)
    mp_recipient_address_state = fields.Char(string="Recipient State", readonly=True)
    mp_recipient_address_country = fields.Char(string="Recipient Country", readonly=True)
    mp_recipient_address_zip = fields.Char(string="Recipient ZIP", readonly=True)

    # MP Amounts
    mp_amount_total = fields.Monetary(string="MP Total", readonly=True)
    mp_amount_total_info = fields.Char(string="MP Total Info", compute="_compute_mp_amount_total_info")

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

    @api.model
    def _finish_mapping_raw_data(self, sanitized_data, values):
        sanitized_data, values = super(SaleOrder, self)._finish_mapping_raw_data(sanitized_data, values)
        mp_account = self.get_mp_account_from_context()
        partner_shipping, customer = self.get_mp_order_customer(mp_account, values)
        values.update({
            'partner_id': customer.id,
            'partner_invoice_id': partner_shipping.id,
            'partner_shipping_id': partner_shipping.id
        })
        if mp_account.warehouse_id:
            values.update({
                'warehouse_id': mp_account.warehouse_id.id,
            })
        return sanitized_data, values

    @api.model
    def _finish_create_records(self, records):
        records = super(SaleOrder, self)._finish_create_records(records)
        records.generate_delivery_line()
        records.generate_insurance_line()
        records.generate_global_discount_line()
        records.generate_adjusment_line()
        return records

    @api.model
    def _finish_update_records(self, records):
        records = super(SaleOrder, self)._finish_update_records(records)
        records.generate_delivery_line()
        records.generate_insurance_line()
        records.generate_global_discount_line()
        records.generate_adjusment_line()
        return records

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

    @api.multi
    def _compute_mp_amount_total_info(self):
        for order in self:
            order.mp_amount_total_info = False
            if order.amount_total != order.mp_amount_total:
                order.mp_amount_total_info = "WARNING: Amount total of Sale Order is different with amount total of " \
                                             "marketplace order! "

    @api.model
    def lookup_partner_shipping(self, order_values, default_customer=None):
        partner_obj = self.env['res.partner']

        if not default_customer:
            default_customer = partner_obj
        partner_shipping = partner_obj
        partner_shipping_values = {
            'name': order_values.get('mp_recipient_address_name'),
            'phone': order_values.get('mp_recipient_address_phone'),
            'street': order_values.get('mp_recipient_address_full'),
            'zip': order_values.get('mp_recipient_address_zip')
        }

        if default_customer.exists():  # Then look for child partner (delivery address) of default customer
            if order_values.get('mp_recipient_address_phone'):
                partner_shipping = partner_obj.search([
                    ('parent_id', '=', default_customer.id),
                    ('phone', '=', order_values.get('mp_recipient_address_phone'))
                ], limit=1)
            if not partner_shipping.exists():  # Then create new child partner of default customer
                partner_shipping_values.update({'parent_id': default_customer.id, 'type': 'delivery'})
                partner_shipping = partner_obj.create(partner_shipping_values)
        else:  # Then look for child partner (delivery address) first
            if order_values.get('mp_recipient_address_phone'):
                partner_shipping = partner_obj.search([
                    ('parent_id', '!=', False),
                    ('type', '=', 'delivery'),
                    ('phone', '=', order_values.get('mp_recipient_address_phone'))
                ], limit=1)
                if not partner_shipping.exists():  # Then look for parent partner
                    partner = partner_obj.search([
                        ('parent_id', '=', False),
                        ('type', '=', 'contact'),
                        ('phone', '=', order_values.get('mp_recipient_address_phone'))
                    ], limit=1)
                    if not partner.exists():  # Then create partner
                        partner_values = partner_shipping_values.copy()
                        partner_values.update({'type': 'contact'})
                        partner = partner_obj.create(partner_values)
                    # Then pass it to this method recursively
                    return self.lookup_partner_shipping(order_values, default_customer=partner)
        # Finally return the partner shipping
        return partner_shipping

    @api.model
    def get_mp_order_customer(self, mp_account, values):
        partner_shipping = self.lookup_partner_shipping(values, default_customer=mp_account.partner_id)
        # Finally return the partner shipping and its parent as customer
        return partner_shipping, partner_shipping.parent_id

    @api.multi
    def generate_delivery_line(self):
        for order in self:
            if hasattr(order, '%s_generate_delivery_line' % order.marketplace):
                getattr(order, '%s_generate_delivery_line' % order.marketplace)()

    @api.multi
    def generate_insurance_line(self):
        for order in self:
            if hasattr(order, '%s_generate_insurance_line' % order.marketplace):
                getattr(order, '%s_generate_insurance_line' % order.marketplace)()

    @api.multi
    def generate_global_discount_line(self):
        for order in self:
            if hasattr(order, '%s_generate_global_discount_line' % order.marketplace):
                getattr(order, '%s_generate_global_discount_line' % order.marketplace)()

    @api.multi
    def generate_adjusment_line(self):
        for order in self:
            if hasattr(order, '%s_generate_adjusment_line' % order.marketplace):
                getattr(order, '%s_generate_adjusment_line' % order.marketplace)()
