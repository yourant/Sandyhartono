# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.izi_marketplace.objects.utils.tools import mp
from odoo.addons.izi_shopee.objects.utils.shopee.order import ShopeeOrder


class WizardShopeeOrderReject(models.TransientModel):
    _name = 'wiz.sp_order_reject'
    _description = 'Shopee Order Reject Wizard'

    REJECT_REASONS = [
        ('CUSTOMER_REQUEST', 'Customer request'),
        ('UNDELIVERABLE_AREA', 'Undeliverable area'),
        ('COD_NOT_SUPPORTED', 'COD not support'),
        ('OUT_OF_STOCK', 'Out of stock'),
    ]

    order_ids = fields.Many2many(comodel_name="sale.order", relation="rel_sp_order_reject_sale_order",
                                 column1="order_reject_id", column2="order_id", string="Order(s)", required=True)
    reason_code = fields.Selection(string="Reason", selection=REJECT_REASONS, required=True)
    item_ids = fields.Many2many(comodel_name="sale.order.line", relation="rel_order_reject_item",
                                column1="order_reject_id", column2="product_id", string="Item(s)", required=False)

    @ mp.shopee.capture_error
    def confirm(self):
        for order in self.order_ids:
            if order.mp_account_id.mp_token_id.state == 'valid':
                params = {'access_token': order.mp_account_id.mp_token_id.name}
                sp_account = order.mp_account_id.shopee_get_account(**params)
                sp_order = ShopeeOrder(sp_account)

                kwargs = {
                    'order_exid': order.mp_external_id,
                    'reason_code': self.reason_code,
                }

                if self.reason_code == 'OUT_OF_STOCK':
                    item_list = []
                    for item in self.item_ids:
                        product_dict = {}
                        product_id = item.product_id
                        for product in product_id.map_line_ids:
                            if product.product_id.id == product_id.id:
                                if product.mp_product_id:
                                    product_dict['item_id'] = int(product.mp_product_id.mp_external_id)
                                if product.mp_product_variant_id:
                                    product_dict['item_id'] = int(
                                        product.mp_product_variant_id.mp_product_id.mp_external_id)
                                    product_dict['model_id'] = int(product.mp_product_variant_id.mp_external_id)
                                break
                        item_list.append(product_dict)

                    kwargs.update({
                        'item_list': item_list,
                    })

                action_status = sp_order.action_reject_order(**kwargs)
                if action_status == "success":
                    order.action_cancel()
                    order.shopee_fetch_order()
