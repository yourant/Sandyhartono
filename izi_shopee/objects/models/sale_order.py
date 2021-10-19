# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from datetime import datetime, timezone
import time
import json


from odoo import api, fields, models
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import ValidationError

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
            'mp_amount_total': ('total_amount', None),
            'mp_awb_url': ('awb_url', None),
            'mp_expected_income': ('order_income/escrow_amount', None)
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
                list_item_field = ['item_id', 'item_name', 'item_sku', 'model_id', 'model_name', 'model_sku']

                item_list = sp_order_raw['item_list']
                for item in item_list:
                    item['item_info'] = dict([(key, item[key]) for key in list_item_field])

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

    @api.multi
    def shopee_generate_delivery_line(self):
        sp_logistic_obj = self.env['mp.shopee.logistic']

        for order in self:
            delivery_line = order.order_line.filtered(lambda l: l.is_delivery)
            if not delivery_line:
                sp_order_raw = json.loads(order.raw, strict=False)
                sp_order_shipping = json_digger(sp_order_raw, 'package_list')[0]
                sp_logistic_name = str(sp_order_shipping.get('shipping_carrier'))
                sp_logistic = sp_logistic_obj.search([('logistics_channel_name', '=', sp_logistic_name)])
                delivery_product = sp_logistic.get_delivery_product()
                if not delivery_product:
                    raise ValidationError('Please define delivery product on "%s"' % sp_logistic_name)

                shipping_fee = sp_order_raw.get('actual_shipping_fee', 0)
                if shipping_fee == 0:
                    shipping_fee = sp_order_raw.get('estimated_shipping_fee', 0)
                order.write({
                    'order_line': [(0, 0, {
                        'sequence': 999,
                        'product_id': delivery_product.id,
                        'name': sp_logistic_name,
                        'product_uom_qty': 1,
                        'price_unit': shipping_fee,
                        'is_delivery': True
                    })]
                })

    @api.multi
    def shopee_generate_adjusment_line(self):
        for order in self:
            adjustment_line = order.order_line.filtered(lambda l: l.is_adjustment)
            if not adjustment_line:
                sp_order_raw = json.loads(order.raw, strict=False)
                total_adjustment = json_digger(sp_order_raw, 'order_income/buyer_transaction_fee',
                                               default=0)
                if total_adjustment > 0:
                    adjustment_product = order.mp_account_id.adjustment_product_id
                    if not adjustment_product:
                        raise ValidationError(
                            'Please define global discount product on'
                            ' this marketplace account: "%s"' % order.mp_account_id.name)
                    order.write({
                        'order_line': [(0, 0, {
                            'sequence': 999,
                            'product_id': adjustment_product.id,
                            'product_uom_qty': 1,
                            'price_unit': total_adjustment,
                            'is_adjustment': True
                        })]
                    })

    @api.multi
    def shopee_generate_global_discount_line(self):
        for order in self:
            adjustment_line = order.order_line.filtered(lambda l: l.is_adjustment)
            if not adjustment_line:
                sp_order_raw = json.loads(order.raw, strict=False)
                seller_discount = json_digger(sp_order_raw, 'order_income/seller_discount',
                                              default=0)
                shopee_discount = json_digger(sp_order_raw, 'order_income/shopee_discount',
                                              default=0)
                voucher_from_seller = json_digger(sp_order_raw, 'order_income/voucher_from_seller',
                                                  default=0)
                voucher_from_shopee = json_digger(sp_order_raw, 'order_income/voucher_from_shopee',
                                                  default=0)

                total_discount = seller_discount + shopee_discount + voucher_from_seller + voucher_from_shopee
                if total_discount > 0:
                    discount_product = order.mp_account_id.global_discount_product_id
                    if not discount_product:
                        raise ValidationError(
                            'Please define global discount product on'
                            ' this marketplace account: "%s"' % order.mp_account_id.name)
                    order.write({
                        'order_line': [(0, 0, {
                            'sequence': 999,
                            'product_id': discount_product.id,
                            'product_uom_qty': -1,
                            'price_unit': total_discount,
                            'is_global_discount': True
                        })]
                    })
