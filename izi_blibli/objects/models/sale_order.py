# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from datetime import datetime, timezone
import time

from odoo import api, fields, models
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    BLI_ORDER_STATUSES = [
        ('FP', 'Waiting'),
        ('PF', 'Ready To Ship'),
        ('CR', 'Customer Request'),
        ('CX', 'In Delivery'),
        ('PU', 'Waiting to Pick Up '),
        ('OS', 'Product Out of Stock'),
        ('BP', 'Big Product Ready to Deliver'),
        ('D', 'Delivered'),
        ('X', 'Canceled')
    ]

    bli_order_status = fields.Selection(string="Blibli Order Status", selection=BLI_ORDER_STATUSES, required=False)
    bli_order_id = fields.Char(string="Blibli Order ID", readonly=True)
    bli_auto_cancel_date = fields.Datetime(string='Blibli Cancel Order Time')

    @classmethod
    def _add_rec_mp_order_status(cls, mp_order_statuses=None, mp_order_status_notes=None):
        if not mp_order_statuses:
            mp_order_statuses = []
        if not mp_order_status_notes:
            mp_order_status_notes = []

        marketplace, bli_order_status_field = 'blibli', 'bli_order_status'
        bli_order_statuses = {
            'waiting': [],
            'cancel': ['X', 'OS'],
            'to_process': ['FP'],
            'in_process': ['CR'],
            'to_ship': ['PF', 'PU', 'BP'],
            'in_ship': ['CX'],
            'done': ['D'],
            'return': []
        }
        mp_order_statuses.append((marketplace, (bli_order_status_field, bli_order_statuses)))
        mp_order_status_notes.append((marketplace, dict(cls.BLI_ORDER_STATUSES)))
        super(SaleOrder, cls)._add_rec_mp_order_status(mp_order_statuses, mp_order_status_notes)

    @api.multi
    @api.depends('bli_order_status')
    def _compute_mp_order_status(self):
        super(SaleOrder, self)._compute_mp_order_status()

    @classmethod
    def _add_rec_mp_external_id(cls, mp_external_id_fields=None):
        if not mp_external_id_fields:
            mp_external_id_fields = []

        mp_external_id_fields.append(('blibli', 'bli_order_id'))
        super(SaleOrder, cls)._add_rec_mp_external_id(mp_external_id_fields)

    @classmethod
    def _add_rec_mp_field_mapping(cls, mp_field_mappings=None):
        if not mp_field_mappings:
            mp_field_mappings = []

        marketplace = 'blibli'
        mp_field_mapping = {
            'mp_invoice_number': ('orderNo', None),
            'bli_order_id': ('orderNo', None),
            'bli_order_status': ('orderStatus', None),
            'mp_buyer_username': ('custName', None),
            'mp_delivery_carrier_name': ('logisticsProductName', None),
            'mp_order_notes': ('custNote', None),
            'mp_cancel_reason': ('unFullFillReason', None),
            'mp_recipient_address_city': ('shippingCity', None),
            'mp_recipient_address_name': ('shippingRecipientName', None),
            'mp_recipient_address_district': ('shippingSubDistrict', None),
            'mp_recipient_address_zipcode': ('shippingZipCode', None),
            'mp_recipient_address_phone': ('shippingMobile', None),
            'mp_recipient_address_full': ('shippingStreetAddress', None),
        }

        def _convert_timestamp_to_datetime(env, data):
            if data:
                return datetime.fromtimestamp(
                    time.mktime(time.gmtime(data/1000))).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            else:
                return None

        # def _convert_payment_timestamp_to_datetime(env, data):
        #     if data:
        #         return datetime.fromtimestamp(
        #           time.mktime(time.gmtime(data/1000))).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        #     else:
        #         return None

        mp_field_mapping.update({
            # 'mp_payment_date': ('order_list/pay_time', _convert_payment_timestamp_to_datetime),
            'mp_order_date': ('orderDate', _convert_timestamp_to_datetime),
            'bli_auto_cancel_date': ('autoCancelDate', _convert_timestamp_to_datetime),
            # 'mp_shipping_deadline': ('order_list/ship_by_date', _convert_timestamp_to_datetime)
        })

        mp_field_mappings.append((marketplace, mp_field_mapping))
        super(SaleOrder, cls)._add_rec_mp_field_mapping(mp_field_mappings)

    @api.model
    def blibli_get_sanitizers(self, mp_field_mapping):
        default_sanitizer = self.get_default_sanitizer(mp_field_mapping, root_path='value')
        return {
            'order_detail': default_sanitizer
        }

    @api.model
    def _finish_mapping_raw_data(self, sanitized_data, values):
        sanitized_data, values = super(SaleOrder, self)._finish_mapping_raw_data(sanitized_data, values)
        mp_account = self.get_mp_account_from_context()
        partner, shipping_address = self.get_mp_partner(mp_account, values)
        values.update({
            'partner_id': partner.id,
            'partner_shipping_id': shipping_address.id,
            'partner_invoice_id': partner.id
        })
        return sanitized_data, values
