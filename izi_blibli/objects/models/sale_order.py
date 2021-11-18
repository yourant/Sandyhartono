# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from datetime import datetime, timezone
import time
import json

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.addons.izi_marketplace.objects.utils.tools import json_digger
from odoo.exceptions import ValidationError


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
    bli_package_number = fields.Char(string="Blibli Package Number", readonly=True)

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
            'mp_invoice_number': ('orderNo', lambda env, r: str(r)),
            'bli_order_id': ('orderNo', lambda env, r: str(r)),
            'bli_order_status': ('orderStatus', None),
            'mp_buyer_username': ('customerFullName', None),
            'bli_package_number': ('packageId', None),
        }

        def _convert_timestamp_to_datetime(env, data):
            if data:
                return datetime.fromtimestamp(
                    time.mktime(time.gmtime(data/1000))).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            else:
                return None

        def _payment_date(env, data):
            if data:
                location = len(data[0]['orderHistory'])-1
                if data[0]['orderHistory'][location]['orderStatusDesc'] == 'Pembayaran Diterima':
                    date_temp = data[0]['orderHistory'][location]['createdDate']
                    date = datetime.fromtimestamp(
                        time.mktime(time.gmtime(date_temp/1000))).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                else:
                    return None
                return date
            else:
                return None

        def _mp_order_notes(env, data):
            if data:
                return data[0]['custNote']
            else:
                return None

        def _mp_cancel_reason(env, data):
            if data:
                return data[0]['unFullFillReason']
            else:
                return None

        def _mp_delivery_carrier_name(env, data):
            if data:
                return data[0]['logisticsProductName']
            else:
                return None

        def _mp_recipient_address_city(env, data):
            if data:
                return data[0]['shippingCity']
            else:
                return None

        def _mp_recipient_address_name(env, data):
            if data:
                return data[0]['shippingRecipientName']
            else:
                return None

        def _mp_recipient_address_district(env, data):
            if data:
                return data[0]['shippingDistrict']
            else:
                return None

        def _mp_recipient_address_zipcode(env, data):
            if data:
                return data[0]['shippingZipCode']
            else:
                return None

        def _mp_recipient_address_phone(env, data):
            if data:
                return data[0]['shippingMobile']
            else:
                return None

        def _mp_recipient_address_full(env, data):
            if data:
                return data[0]['shippingStreetAddress']
            else:
                return None

        def _mp_awb_number(env, data):
            if data:
                return data[0]['awbNumber']
            else:
                return None

        mp_field_mapping.update({
            'mp_payment_date': ('item_list', _payment_date),
            'mp_order_date': ('orderDate', _convert_timestamp_to_datetime),
            'bli_auto_cancel_date': ('autoCancelDate', _convert_timestamp_to_datetime),
            'mp_order_notes': ('item_list', _mp_order_notes),
            'mp_cancel_reason': ('item_list', _mp_cancel_reason),
            'mp_delivery_carrier_name': ('item_list', _mp_delivery_carrier_name),
            'mp_recipient_address_city': ('item_list', _mp_recipient_address_city),
            'mp_recipient_address_name': ('item_list', _mp_recipient_address_name),
            'mp_recipient_address_district': ('item_list', _mp_recipient_address_district),
            'mp_recipient_address_zipcode': ('item_list', _mp_recipient_address_zipcode),
            'mp_recipient_address_phone': ('item_list', _mp_recipient_address_phone),
            'mp_recipient_address_full': ('item_list', _mp_recipient_address_full),
            'mp_awb_number': ('item_list', _mp_awb_number),
        })

        mp_field_mappings.append((marketplace, mp_field_mapping))
        super(SaleOrder, cls)._add_rec_mp_field_mapping(mp_field_mappings)

    @api.model
    def _finish_create_records(self, records):
        mp_account = self.get_mp_account_from_context()
        mp_account_ctx = mp_account.generate_context()

        order_line_obj = self.env['sale.order.line'].with_context(mp_account_ctx)

        bli_order_detail_raws, bli_order_detail_sanitizeds = [], []

        if mp_account.marketplace == 'blibli':
            for record in records:
                bli_order_raw = json.loads(record.raw, strict=False)
                list_field = ['gdnItemSku', 'productItemName', 'merchantSku', 'productName', 'gdnSku']

                item_list = bli_order_raw['item_list']
                for item in item_list:
                    item['item_info'] = dict([(key, item[key]) for key in list_field])

                bli_order_details = [
                    # Insert order_id into bli_order_detail_raw
                    dict(bli_order_detail_raw, **dict([('order_id', record.id)]))
                    for bli_order_detail_raw in json_digger(bli_order_raw, 'item_list')
                ]
                bli_data_raw, bli_data_sanitized = order_line_obj.with_context(
                    mp_account_ctx)._prepare_mapping_raw_data(raw_data=bli_order_details)
                bli_order_detail_raws.extend(bli_data_raw)
                bli_order_detail_sanitizeds.extend(bli_data_sanitized)

            check_existing_records_params = {
                'identifier_field': 'bli_order_item_id',
                'raw_data': bli_order_detail_raws,
                'mp_data': bli_order_detail_sanitizeds,
                'multi': isinstance(bli_order_detail_sanitizeds, list)
            }
            check_existing_records = order_line_obj.with_context(
                mp_account_ctx).check_existing_records(**check_existing_records_params)
            order_line_obj.with_context(
                mp_account_ctx).handle_result_check_existing_records(check_existing_records)
        
        records = super(SaleOrder, self)._finish_create_records(records)
        return records

    @api.multi
    def blibli_generate_delivery_line(self):
        bli_logistic_obj = self.env['mp.blibli.logistic']

        for order in self:
            delivery_line = order.order_line.filtered(lambda l: l.is_delivery)
            if not delivery_line:
                bli_order_raw = json.loads(order.raw, strict=False)
                bli_order_shipping = json_digger(bli_order_raw, 'item_list')[0]
                bli_logistic_name = str(bli_order_shipping.get('logisticsProductName'))
                bli_logistic = bli_logistic_obj.search([('logistics_name', 'ilike', bli_logistic_name)])[0]
                delivery_product = bli_logistic.get_delivery_product()
                if not delivery_product:
                    raise ValidationError('Please define delivery product on "%s"' % bli_logistic_name)

                shipping_fee = bli_order_raw.get('actual_shipping_fee', 0)
                if shipping_fee == 0:
                    shipping_fee = bli_order_raw.get('estimated_shipping_fee', 0)
                order.write({
                    'order_line': [(0, 0, {
                        'product_id': delivery_product.id,
                        'name': bli_logistic_name,
                        'product_uom_qty': 1,
                        'price_unit': shipping_fee,
                        'is_delivery': True
                    })]
                })
