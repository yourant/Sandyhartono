# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from datetime import datetime, timezone
import time
import json


from odoo import api, fields, models
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import ValidationError, UserError


from odoo.addons.izi_marketplace.objects.utils.tools import mp
from odoo.addons.izi_marketplace.objects.utils.tools import json_digger
from odoo.addons.izi_shopee.objects.utils.shopee.account import ShopeeAccount
from odoo.addons.izi_shopee.objects.utils.shopee.order import ShopeeOrder


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
            'mp_order_notes': ('message_to_seller', None),
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
            'mp_expected_income': ('order_income/escrow_amount', None),
            'mp_delivery_carrier_type': ('checkout_shipping_carrier', None)
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

        def _set_mp_delivery_type(env, data):
            if data:
                mp_delivery_type = None
                if 'pickup' in data and 'dropoff' in data:
                    mp_delivery_type = 'both'
                elif 'pickup' in data:
                    mp_delivery_type = 'pickup'
                elif 'dropoff' in data:
                    mp_delivery_type = 'drop off'
                return mp_delivery_type
            else:
                return None

        mp_field_mapping.update({
            'mp_payment_date': ('pay_time', _convert_timestamp_to_datetime),
            'mp_order_date': ('create_time', _convert_timestamp_to_datetime),
            'mp_order_last_update_date': ('update_time', _convert_timestamp_to_datetime),
            'mp_shipping_deadline': ('ship_by_date', _convert_timestamp_to_datetime),
            'sp_package_number': ('package_list', _get_package_number),
            'mp_awb_number': ('shipping_document_info', _get_tracking_number),
            'mp_delivery_type': ('shipping_paramater/info_needed', _set_mp_delivery_type)

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

            def identify_order_line(record_obj, values):
                return record_obj.search([('order_id', '=', values['order_id']),
                                          ('product_id', '=', values['product_id'])], limit=1)

            check_existing_records_params = {
                'identifier_method': identify_order_line,
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
    def shopee_fetch_order(self):
        wiz_mp_order_obj = self.env['wiz.mp.order']

        self.ensure_one()

        wiz_mp_order = wiz_mp_order_obj.create({
            'mp_account_id': self.mp_account_id.id,
            'params': 'by_mp_invoice_number',
            'mp_invoice_number': self.mp_invoice_number
        })
        return wiz_mp_order.get_order()

    @api.multi
    def shopee_generate_delivery_line(self):
        sp_logistic_obj = self.env['mp.shopee.logistic']

        for order in self:
            delivery_line = order.order_line.filtered(lambda l: l.is_delivery)
            sp_order_raw = json.loads(order.raw, strict=False)
            sp_order_shipping = json_digger(sp_order_raw, 'package_list')[0]
            sp_logistic_name = str(sp_order_shipping.get('shipping_carrier'))
            if not delivery_line:
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
            else:
                if delivery_line.name != sp_logistic_name:
                    delivery_line.update({
                        'name': sp_logistic_name,
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

            shopee_coins_line = order.order_line.filtered(lambda l: l.is_shopee_coins)
            if not shopee_coins_line:
                sp_order_raw = json.loads(order.raw, strict=False)
                total_coins = json_digger(sp_order_raw, 'order_income/coins',
                                          default=0)
                if total_coins > 0:
                    shopee_coins_product = order.mp_account_id.sp_coins_product_id
                    if not shopee_coins_product:
                        raise ValidationError(
                            'Please define global discount product on'
                            ' this marketplace account: "%s"' % order.mp_account_id.name)
                    order.write({
                        'order_line': [(0, 0, {
                            'sequence': 999,
                            'name': 'Shopee Coins',
                            'product_id': shopee_coins_product.id,
                            'product_uom_qty': 1,
                            'price_unit': -total_coins,
                            'is_shopee_coins': True
                        })]
                    })

    @api.multi
    def shopee_generate_global_discount_line(self):
        for order in self:
            global_discount_line = order.order_line.filtered(lambda l: l.is_global_discount)
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
            if not global_discount_line:

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
                            'product_uom_qty': 1,
                            'price_unit': -total_discount,
                            'is_global_discount': True
                        })]
                    })
            else:
                if total_discount > 0:
                    global_discount_line.write({
                        'price_unit': total_discount,
                    })

    @api.multi
    @mp.shopee.capture_error
    def shopee_get_awb(self):
        sp_account = False
        for order in self:
            if order.mp_awb_url:
                return {
                    'name': 'Label',
                    'res_model': 'ir.actions.act_url',
                    'type': 'ir.actions.act_url',
                    'target': 'new',
                    'url': order.mp_awb_url,
                }
            elif order.mp_awb_number:
                if order.mp_account_id.mp_token_id.state == 'valid':
                    params = {'access_token': order.mp_account_id.mp_token_id.name}
                    sp_account = order.mp_account_id.shopee_get_account(**params)
                else:
                    raise UserError('Access Token is invalid, Please Reauthenticated Shopee Account')

                if sp_account:
                    sp_order_v1 = ShopeeOrder(sp_account, api_version="v1")
                    awb_data = sp_order_v1.get_airways_bill(order_sn=order.mp_invoice_number)
                    order.mp_awb_url = awb_data.get(order.mp_invoice_number, False)
                    if order.mp_awb_url:
                        return {
                            'name': 'Label',
                            'res_model': 'ir.actions.act_url',
                            'type': 'ir.actions.act_url',
                            'target': 'new',
                            'url': order.mp_awb_url,
                        }
            else:
                pass

    @api.multi
    @mp.shopee.capture_error
    def shopee_drop_off(self):
        sale_order_obj = self.env['sale.order']
        sp_account = False
        for order in self:
            if order.mp_account_id.mp_token_id.state == 'valid':
                params = {'access_token': order.mp_account_id.mp_token_id.name}
                sp_account = order.mp_account_id.shopee_get_account(**params)
            else:
                raise UserError('Access Token is invalid, Please Reauthenticated Shopee Account')

            if sp_account:
                sp_order_v2 = ShopeeOrder(sp_account, sanitizers=sale_order_obj.get_sanitizers(self.marketplace))
                action_params = {
                    'order_sn': order.mp_external_id,
                    # 'package_number': order.sp_package_number,
                    'dropoff': {
                        "tracking_no": "",
                        "branch_id": 0,
                        "sender_real_name": ""
                    }
                }
                action_status = sp_order_v2.action_ship_order(**action_params)
                if action_status == "success":
                    order.action_confirm()
                    time.sleep(3)
                    order.shopee_fetch_order()

    @api.multi
    def shopee_reject_order(self):
        return {
            'name': 'Reject Order(s)',
            'view_mode': 'form',
            'res_model': 'wiz.sp_order_reject',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {
                'default_order_ids': [(6, 0, self.ids)],
            },
        }

    @api.multi
    def shopee_accept_cancellation_order(self):
        for order in self:
            if order.mp_account_id.mp_token_id.state == 'valid':
                params = {'access_token': order.mp_account_id.mp_token_id.name}
                sp_account = order.mp_account_id.shopee_get_account(**params)
                sp_order_v2 = ShopeeOrder(sp_account)
                action_params = {
                    'order_sn': order.mp_external_id,
                    'operation': 'ACCEPT',
                }
                action_status = sp_order_v2.action_handle_buyer_cancel(**action_params)
                if action_status == "success":
                    order.action_cancel()
                    order.shopee_fetch_order()
            else:
                raise UserError('Access Token is invalid, Please Reauthenticated Shopee Account')

    @api.multi
    def shopee_reject_cancellation_order(self):
        for order in self:
            if order.mp_account_id.mp_token_id.state == 'valid':
                params = {'access_token': order.mp_account_id.mp_token_id.name}
                sp_account = order.mp_account_id.shopee_get_account(**params)
                sp_order_v2 = ShopeeOrder(sp_account)
                action_params = {
                    'order_sn': order.mp_external_id,
                    'operation': 'REJECT',
                }
                action_status = sp_order_v2.action_handle_buyer_cancel(**action_params)
                if action_status == "success":
                    order.action_confirm()
                    order.shopee_fetch_order()
            else:
                raise UserError('Access Token is invalid, Please Reauthenticated Shopee Account')
