# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import json
import time
from base64 import b64decode
from datetime import datetime

from Cryptodome.Cipher import PKCS1_OAEP, AES
from Cryptodome.Hash import SHA256
from Cryptodome.PublicKey import RSA
from odoo import api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.izi_marketplace.objects.utils.tools import merge_dict, json_digger
from odoo.addons.izi_tokopedia.objects.utils.tokopedia.order import TokopediaOrder


class SaleOrder(models.Model):
    _inherit = 'sale.order'

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
    tp_invoice_url = fields.Char(string="Tokpedia Invoice URL", required=False)

    @api.multi
    @api.depends('tp_order_status')
    def _compute_mp_order_status(self):
        super(SaleOrder, self)._compute_mp_order_status()

    @classmethod
    def _add_rec_mp_external_id(cls, mp_external_id_fields=None):
        if not mp_external_id_fields:
            mp_external_id_fields = []

        mp_external_id_fields.append(('tokopedia', 'tp_order_id'))
        super(SaleOrder, cls)._add_rec_mp_external_id(mp_external_id_fields)

    @classmethod
    def _add_rec_mp_field_mapping(cls, mp_field_mappings=None):
        if not mp_field_mappings:
            mp_field_mappings = []

        marketplace = 'tokopedia'
        mp_field_mapping = {
            'tp_order_id': ('order_id', lambda env, r: str(r)),

            # MP Order Status
            'tp_order_status': ('order_status', lambda env, r: str(r)),

            # MP Order Transaction & Payment
            'mp_invoice_number': ('invoice_number', None),
            'tp_invoice_url': ('invoice_url', None),
            'mp_payment_method_info': ('payment_info/gateway_name', None),

            # MP Order Shipment
            'mp_awb_number': ('order_info/shipping_info/awb', None),
            'mp_delivery_carrier_name': ('order_info/shipping_info/logistic_name', None),
            'mp_delivery_carrier_type': ('order_info/shipping_info/logistic_service', None),
            'shipping_id': ('order_info/shipping_info/shipping_id', lambda env, r: str(r)),

            # MP Buyer Info
            'mp_buyer_id': ('buyer_info/buyer_id', lambda env, r: str(r)),
            'mp_buyer_name': ('buyer_info/buyer_fullname', None),
            'mp_buyer_email': ('buyer_info/buyer_email', None),
            'mp_buyer_phone': ('buyer_info/buyer_phone', None),

            # MP Recipient Info
            'mp_recipient_address_name': ('order_info/destination/receiver_name', None),
            'mp_recipient_address_phone': ('order_info/destination/receiver_phone', None),
            'mp_recipient_address_full': ('order_info/destination/address_street', None),
            'mp_recipient_address_district': ('order_info/destination/address_district', None),
            'mp_recipient_address_city': ('order_info/destination/address_city', None),
            'mp_recipient_address_state': ('order_info/destination/address_province', None),
            'mp_recipient_address_zip': ('order_info/destination/address_postal', None),
            'tp_order_detail': ('order_info/order_detail', None),

            # MP Order Amount
            'mp_amount_total': ('order_summary/amt/ttl_amount', None),  # Amount Total
            'item_price': ('item_price', None),  # Amount Total (Items Only)
        }

        def _handle_isoformat_to_dt_str(env, data):
            isoformat = data[:-1].split('.')[0]
            dt = env['mp.base'].datetime_convert_tz(datetime.fromisoformat(isoformat), 'Asia/Jakarta', 'UTC')
            return fields.Datetime.to_string(dt)

        mp_field_mapping.update({
            # MP Order Transaction & Payment
            'mp_payment_date': ('payment_info/payment_date', _handle_isoformat_to_dt_str),
            'mp_order_date': ('create_time', _handle_isoformat_to_dt_str),
            'date_order': ('create_time', _handle_isoformat_to_dt_str),
            'mp_order_last_update_date': ('update_time', _handle_isoformat_to_dt_str),
            'mp_accept_deadline': ('shipment_fulfillment/accept_deadline', _handle_isoformat_to_dt_str),

            # MP Order Shipment
            'mp_shipping_deadline': ('shipment_fulfillment/confirm_shipping_deadline', _handle_isoformat_to_dt_str),
        })

        mp_field_mappings.append((marketplace, mp_field_mapping))
        super(SaleOrder, cls)._add_rec_mp_field_mapping(mp_field_mappings)

    @api.model
    def _finish_create_records(self, records):
        mp_account = self.get_mp_account_from_context()
        mp_account_ctx = mp_account.generate_context()

        order_line_obj = self.env['sale.order.line'].with_context(mp_account_ctx)

        records = super(SaleOrder, self)._finish_create_records(records)

        if mp_account.marketplace == 'tokopedia':
            tp_order_detail_raws, tp_order_detail_sanitizeds = [], []
            for record in records:
                tp_order_raw = json.loads(record.raw, strict=False)
                tp_order_details = [
                    # Insert order_id into tp_order_detail_raw
                    dict(tp_order_detail_raw, **dict([('order_id', record.id)]))
                    for tp_order_detail_raw in json_digger(tp_order_raw, 'order_info/order_detail')
                ]
                tp_data_raw, tp_data_sanitized = order_line_obj._prepare_mapping_raw_data(raw_data=tp_order_details)
                tp_order_detail_raws.extend(tp_data_raw)
                tp_order_detail_sanitizeds.extend(tp_data_sanitized)

            check_existing_records_params = {
                'identifier_field': 'tp_order_detail_id',
                'raw_data': tp_order_detail_raws,
                'mp_data': tp_order_detail_sanitizeds,
                'multi': isinstance(tp_order_detail_sanitizeds, list)
            }
            check_existing_records = order_line_obj.check_existing_records(**check_existing_records_params)
            order_line_obj.handle_result_check_existing_records(check_existing_records)
        return records

    @classmethod
    def _add_rec_mp_order_status(cls, mp_order_statuses=None, mp_order_status_notes=None):
        if not mp_order_statuses:
            mp_order_statuses = []
        if not mp_order_status_notes:
            mp_order_status_notes = []

        marketplace, tp_order_status_field = 'tokopedia', 'tp_order_status'
        tp_order_statuses = {
            'waiting': ['11', '100', '103', '200'],
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
        super(SaleOrder, cls)._add_rec_mp_order_status(mp_order_statuses, mp_order_status_notes)

    @api.model
    def tokopedia_get_sanitizers(self, mp_field_mapping):
        mp_account = self.get_mp_account_from_context()
        default_sanitizer = self.get_default_sanitizer(mp_field_mapping)

        def sanitize_decrypt(response=None, raw_data=None):
            if response:
                raw_data = response.json()

            decrypted_raw_datas = []
            if not isinstance(raw_data, list):
                raw_data = [raw_data]
            for raw_data_with_encrypted_content in raw_data:
                raw_content = self.tokopedia_decrypt_order(raw_data_with_encrypted_content, mp_account.tp_private_key)
                if raw_content:
                    decrypted_raw_datas.append(raw_content)

            return default_sanitizer(raw_data=decrypted_raw_datas)

        return {
            'sanitize_decrypt': sanitize_decrypt
        }

    @api.model
    def tokopedia_decrypt_secret(self, encrypted_secret, private_key):
        mp_account = self.get_mp_account_from_context()

        if not mp_account.tp_private_key:
            return False
        secret = b64decode(encrypted_secret.encode('utf-8'))
        rsa_key = RSA.import_key(private_key)
        # noinspection PyTypeChecker
        cipher = PKCS1_OAEP.new(key=rsa_key, hashAlgo=SHA256)
        secret_key = cipher.decrypt(secret)
        return secret_key

    @api.model
    def tokopedia_decrypt_content(self, encrypted_content, secret_key):
        if not secret_key:
            return {}
        data = b64decode(encrypted_content.encode('utf-8'))
        nonce = data[-12:]
        tag = data[:-12][-16:]
        cipher_text = data[:-28]
        cipher = AES.new(secret_key, AES.MODE_GCM, nonce)
        content = cipher.decrypt_and_verify(cipher_text, tag)
        return json.loads(content.decode('utf-8'))

    # noinspection PyBroadException
    @api.model
    def tokopedia_decrypt_order(self, raw_data_with_encrypted_content, private_key, retried=0, max_retry=3):
        mp_account = self.get_mp_account_from_context()
        tp_account = mp_account.tokopedia_get_account()
        tp_order = TokopediaOrder(tp_account, api_version="v2")
        invoice_number = raw_data_with_encrypted_content['invoice_number']

        if 'encryption' in raw_data_with_encrypted_content:
            secret = raw_data_with_encrypted_content['encryption']['secret']
            content = raw_data_with_encrypted_content['encryption']['content']
            try:
                raw_content = self.tokopedia_decrypt_content(content,
                                                             self.tokopedia_decrypt_secret(secret, private_key))
                if raw_content:
                    self._logger('tokopedia', 'Decrypting order detail of %s is success!' % invoice_number)
                    return merge_dict(raw_data_with_encrypted_content, raw_content)
            except Exception as e:
                while retried < max_retry:
                    retried += 1
                    self._logger('tokopedia',
                                 "(%d/%d) Order detail of %s decypting is failed due to %s Retrying..." % (
                                     retried, max_retry, invoice_number, str(e)), level='warning')
                    time.sleep(1)
                    mp_account.tokopedia_register_public_key()
                    tp_data_detail_order = merge_dict(raw_data_with_encrypted_content, tp_order.get_order_detail(
                        order_id=raw_data_with_encrypted_content['order_id']))
                    return self.tokopedia_decrypt_order(tp_data_detail_order, private_key, retried=retried)
                else:
                    self._logger('tokopedia',
                                 'Order detail of %s decrypting is skipped, due to exceed max retry limit = %d, '
                                 'please try again later!' % (invoice_number, retried), level='warning')
        return None

    @api.multi
    def tokopedia_generate_delivery_line(self):
        tp_logistic_service_obj = self.env['mp.tokopedia.logistic.service']

        for order in self:
            delivery_line = order.order_line.filtered(lambda l: l.is_delivery)
            if not delivery_line:
                tp_order_raw = json.loads(order.raw, strict=False)
                tp_order_shipping = json_digger(tp_order_raw, 'order_info/shipping_info')
                tp_logistic_service_id = str(tp_order_shipping.get('sp_id'))
                tp_logistic_service = tp_logistic_service_obj.search_mp_records('tokopedia', tp_logistic_service_id)
                tp_logistic_name = '%s - %s' % (
                    tp_logistic_service.logistic_id.shipper_name, tp_logistic_service.service_name)
                delivery_product = tp_logistic_service.get_delivery_product()
                if not delivery_product:
                    raise ValidationError('Please define delivery product on "%s"' % tp_logistic_name)
                order.write({
                    'order_line': [(0, 0, {
                        'sequence': 999,
                        'product_id': delivery_product.id,
                        'name': tp_logistic_name,
                        'product_uom_qty': 1,
                        'price_unit': tp_order_shipping.get('shipping_price', 0),
                        'is_delivery': True
                    })]
                })

    @api.multi
    def tokopedia_generate_insurance_line(self):
        for order in self:
            insurance_line = order.order_line.filtered(lambda l: l.is_insurance)
            if not insurance_line:
                tp_order_raw = json.loads(order.raw, strict=False)
                insurance_cost = json_digger(tp_order_raw, 'order_summary/amt/insurance_cost', default=0)
                if insurance_cost > 0:
                    insurance_product = order.mp_account_id.insurance_product_id
                    if not insurance_product:
                        raise ValidationError(
                            'Please define insurance product on this marketplace account: "%s"' % order.mp_account_id.name)
                    order.write({
                        'order_line': [(0, 0, {
                            'sequence': 999,
                            'product_id': insurance_product.id,
                            'product_uom_qty': 1,
                            'price_unit': insurance_cost,
                            'is_insurance': True
                        })]
                    })

    @api.multi
    def tokopedia_generate_global_discount_line(self):
        for order in self:
            global_discount_line = order.order_line.filtered(lambda l: l.is_global_discount)
            if not global_discount_line:
                tp_order_raw = json.loads(order.raw, strict=False)
                total_global_discount = json_digger(tp_order_raw, 'order_summary/promo_order_detail/total_discount',
                                                    default=0)
                if total_global_discount > 0:
                    global_discount_product = order.mp_account_id.global_discount_product_id
                    if not global_discount_product:
                        raise ValidationError(
                            'Please define global discount product on'
                            ' this marketplace account: "%s"' % order.mp_account_id.name)
                    order.write({
                        'order_line': [(0, 0, {
                            'sequence': 999,
                            'product_id': global_discount_product.id,
                            'product_uom_qty': 1,
                            'price_unit': total_global_discount,
                            'is_global_discount': True
                        })]
                    })

    @api.multi
    def tokopedia_generate_adjusment_line(self):
        for order in self:
            adjustment_line = order.order_line.filtered(lambda l: l.is_adjustment)
            if not adjustment_line:
                tp_order_raw = json.loads(order.raw, strict=False)
                tp_amt = json_digger(tp_order_raw, 'order_summary/amt', default={})
                adjustment_amount = tp_amt['ttl_amount'] - sum([value for key, value in tp_amt.items() if
                                                                key in ['ttl_product_price', 'shipping_cost',
                                                                        'insurance_cost']])
                if adjustment_amount > 0:
                    adjustment_product = order.mp_account_id.adjustment_product_id
                    if not adjustment_product:
                        raise ValidationError(
                            'Please define adjustment product on'
                            ' this marketplace account: "%s"' % order.mp_account_id.name)
                    order.write({
                        'order_line': [(0, 0, {
                            'sequence': 999,
                            'product_id': adjustment_product.id,
                            'product_uom_qty': 1,
                            'price_unit': adjustment_amount,
                            'is_global_discount': True
                        })]
                    })
