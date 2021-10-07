# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from datetime import datetime, timezone
import time

from odoo import api, fields, models
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    SP_ORDER_STATUSES = [
        ('UNPAID', 'Unpaid'),
        ('READY_TO_SHIP', 'Ready to Ship'),
        ('PROCESSED', 'Processed'),
        ('SHIPPED', 'Shipped'),
        ('COMPLETED', 'Completed'),
        ('TO_CONFIRM_RECEIVE', 'In Confirm Receive'),
        ('IN_CANCEL', 'In Cancel'),
        ('CANCELLED', 'Cancelled'),
        ('TO_RETURN', 'To Return'),
    ]

    sp_order_status = fields.Selection(string="Shopee Order Status", selection=SP_ORDER_STATUSES, required=False)
    sp_order_id = fields.Char(string="Shopee Order ID", readonly=True)

    @classmethod
    def _add_rec_mp_order_status(cls, mp_order_statuses=None, mp_order_status_notes=None):
        if not mp_order_statuses:
            mp_order_statuses = []
        if not mp_order_status_notes:
            mp_order_status_notes = []

        marketplace, sp_order_status_field = 'shopee', 'sp_order_status'
        sp_order_statuses = {
            'waiting': ['UNPAID'],
            'to_cancel': ['IN_CANCEL'],
            'cancel': ['CANCELLED'],
            'to_process': [],
            'in_process': ['READY_TO_SHIP'],
            'to_ship': ['PROCESSED'],
            'in_ship': ['SHIPPED'],
            'done': ['TO_CONFIRM_RECEIVE', 'COMPLETED'],
            'return': ['TO_RETURN']
        }
        mp_order_statuses.append((marketplace, (sp_order_status_field, sp_order_statuses)))
        mp_order_status_notes.append((marketplace, dict(cls.SP_ORDER_STATUSES)))
        super(SaleOrder, cls)._add_rec_mp_order_status(mp_order_statuses, mp_order_status_notes)

    @api.multi
    @api.depends('sp_order_status')
    def _compute_mp_order_status(self):
        super(SaleOrder, self)._compute_mp_order_status()

    @classmethod
    def _add_rec_mp_external_id(cls, mp_external_id_fields=None):
        if not mp_external_id_fields:
            mp_external_id_fields = []

        mp_external_id_fields.append(('shopee', 'sp_order_id'))
        super(SaleOrder, cls)._add_rec_mp_external_id(mp_external_id_fields)

    @classmethod
    def _add_rec_mp_field_mapping(cls, mp_field_mappings=None):
        if not mp_field_mappings:
            mp_field_mappings = []

        marketplace = 'shopee'
        mp_field_mapping = {
            'mp_invoice_number': ('order_list/order_sn', None),
            'sp_order_id': ('order_list/order_sn', None),
            'sp_order_status': ('order_list/order_status', None),
            'mp_buyer_id': ('order_list/buyer_user_id', lambda env, r: str(r)),
            'mp_buyer_username': ('order_list/buyer_username', None),
            'mp_payment_method_info': ('order_list/payment_method', None),
            'mp_delivery_carrier_name': ('order_list/shipping_carrier', None),
            'mp_order_notes': ('order_list/note', None),
            'mp_cancel_reason': ('order_list/cancel_reason', None),
            'mp_recipient_address_city': ('order_list/recipient_address/city', None),
            'mp_recipient_address_name': ('order_list/recipient_address/name', None),
            'mp_recipient_address_district': ('order_list/recipient_address/district', None),
            'mp_recipient_address_country': ('order_list/recipient_address/region', None),
            'mp_recipient_address_zipcode': ('order_list/recipient_address/zipcode', None),
            'mp_recipient_address_phone': ('order_list/recipient_address/phone', None),
            'mp_recipient_address_state': ('order_list/recipient_address/state', None),
            'mp_recipient_address_full': ('order_list/recipient_address/full_address', None),
        }

        def _convert_timestamp_to_datetime(env, data):
            if data:
                return datetime.fromtimestamp(time.mktime(time.gmtime(data))).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            else:
                return None

        mp_field_mapping.update({
            'mp_payment_date': ('order_list/pay_time', _convert_timestamp_to_datetime),
            'mp_order_date': ('order_list/create_time', _convert_timestamp_to_datetime),
            'mp_update_order_date': ('order_list/update_time', _convert_timestamp_to_datetime),
            'mp_shipping_deadline': ('order_list/ship_by_date', _convert_timestamp_to_datetime)
        })

        mp_field_mappings.append((marketplace, mp_field_mapping))
        super(SaleOrder, cls)._add_rec_mp_field_mapping(mp_field_mappings)

    @api.model
    def shopee_get_sanitizers(self, mp_field_mapping):
        default_sanitizer = self.get_default_sanitizer(mp_field_mapping, root_path='response')
        return {
            'order_detail': default_sanitizer
        }

    # @api.model
    # def _finish_mapping_raw_data(self, sanitized_data, values):
    #     sanitized_data, values = super(SaleOrder, self)._finish_mapping_raw_data(sanitized_data, values)
    #     mp_account = self.get_mp_account_from_context()
    #     partner, shipping_address = self.get_mp_partner(mp_account, values)
    #     values.update({
    #         'partner_id': partner.id,
    #         'partner_shipping_id': shipping_address.id,
    #         'partner_invoice_id': partner.id
    #     })
    #     return sanitized_data, values
