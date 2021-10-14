# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from datetime import datetime, timezone
import time
import json


from odoo import api, fields, models
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT

from odoo.addons.izi_marketplace.objects.utils.tools import json_digger


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
    sp_package_number = fields.Char(string="Shopee Package Number", readonly=True)

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
            'mp_invoice_number': ('order_sn', None),
            'sp_order_id': ('order_sn', None),
            'sp_order_status': ('order_status', None),
            'mp_buyer_id': ('buyer_user_id', lambda env, r: str(r)),
            'mp_buyer_username': ('buyer_username', None),
            'mp_payment_method_info': ('payment_method', None),
            'mp_delivery_carrier_name': ('shipping_carrier', None),
            'mp_order_notes': ('note', None),
            'mp_cancel_reason': ('cancel_reason', None),
            'mp_recipient_address_city': ('recipient_address/city', None),
            'mp_recipient_address_name': ('recipient_address/name', None),
            'mp_recipient_address_district': ('recipient_address/district', None),
            'mp_recipient_address_country': ('recipient_address/region', None),
            'mp_recipient_address_zipcode': ('recipient_address/zipcode', None),
            'mp_recipient_address_phone': ('recipient_address/phone', None),
            'mp_recipient_address_state': ('recipient_address/state', None),
            'mp_recipient_address_full': ('recipient_address/full_address', None),
        }

        def _convert_timestamp_to_datetime(env, data):
            if data:
                return datetime.fromtimestamp(time.mktime(time.gmtime(data))).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            else:
                return None

        def _get_package_number(env, data):
            if data:
                return data[0]['package_number']
            else:
                return None

        def _get_tracking_number(env, data):
            if data:
                return data['tracking_number']
            else:
                return None

        mp_field_mapping.update({
            'mp_payment_date': ('pay_time', _convert_timestamp_to_datetime),
            'mp_order_date': ('create_time', _convert_timestamp_to_datetime),
            'mp_order_last_update_date': ('update_time', _convert_timestamp_to_datetime),
            'mp_shipping_deadline': ('ship_by_date', _convert_timestamp_to_datetime),
            'sp_package_number': ('package_list', _get_package_number),
            'mp_awb_number': ('shipping_document_info', _get_tracking_number)

        })

        mp_field_mappings.append((marketplace, mp_field_mapping))
        super(SaleOrder, cls)._add_rec_mp_field_mapping(mp_field_mappings)

    @api.model
    def _finish_create_records(self, records):
        mp_account = self.get_mp_account_from_context()
        mp_account_ctx = mp_account.generate_context()

        order_line_obj = self.env['sale.order.line'].with_context(mp_account_ctx)

        records = super(SaleOrder, self)._finish_create_records(records)

        sp_order_detail_raws, sp_order_detail_sanitizeds = [], []

        if mp_account.marketplace == 'shopee':
            for record in records:
                sp_order_raw = json.loads(record.raw, strict=False)
                list_field = ['item_id', 'item_name', 'item_sku', 'model_id', 'model_name', 'model_sku']

                item_list = sp_order_raw['item_list']
                for item in item_list:
                    item['item_info'] = dict([(key, item[key]) for key in list_field])

                sp_order_details = [
                    # Insert order_id into tp_order_detail_raw
                    dict(sp_order_detail_raw, **dict([('order_id', record.id)]))
                    for sp_order_detail_raw in json_digger(sp_order_raw, 'item_list')
                ]
                sp_data_raw, sp_data_sanitized = order_line_obj.with_context(
                    mp_account_ctx)._prepare_mapping_raw_data(raw_data=sp_order_details)
                sp_order_detail_raws.extend(sp_data_raw)
                sp_order_detail_sanitizeds.extend(sp_data_sanitized)

            check_existing_records_params = {
                'identifier_field': 'sp_order_item_id',
                'raw_data': sp_order_detail_raws,
                'mp_data': sp_order_detail_sanitizeds,
                'multi': isinstance(sp_order_detail_sanitizeds, list)
            }
            check_existing_records = order_line_obj.with_context(
                mp_account_ctx).check_existing_records(**check_existing_records_params)
            order_line_obj.with_context(
                mp_account_ctx).handle_result_check_existing_records(check_existing_records)

        return records

    # @api.model
    # def shopee_get_sanitizers(self, mp_field_mapping):
    #     default_sanitizer = self.get_default_sanitizer(mp_field_mapping, root_path='response')
    #     return {
    #         'order_detail': default_sanitizer
    #     }
