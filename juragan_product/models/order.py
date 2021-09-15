from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import json
from odoo.addons.juragan_webhook import BigInteger

import logging

_logger = logging.getLogger(__name__)

ORDER_STATUS_DICT = {
    0: 'Seller cancel order.',
    2: 'Order Reject Replaced.',
    3: 'Order Reject Due Empty Stock.',
    4: 'Order Reject Approval.',
    5: 'Order Canceled by Fraud',
    10: 'Order rejected by seller.',
    11: 'Order Pending Replacement.',
    100: 'Pending order.',
    103: 'Wait for payment confirmation from third party.',
    200: 'Payment confirmation.',
    220: 'Payment verified, order ready to process.',
    221: 'Waiting for partner approval.',
    400: 'Seller accept order.',
    450: 'Waiting for pickup.',
    500: 'Order shipment.',
    501: 'Status changed to waiting resi have no input.',
    520: 'Invalid shipment reference number (AWB).',
    530: 'Requested by user to correct invalid entry of shipment reference number.',
    540: 'Delivered to Pickup Point.',
    550: 'Return to Seller.',
    600: 'Order delivered.',
    601: 'Buyer open a case to finish an order.',
    690: 'Fraud Review',
    691: 'Suspected Fraud',
    695: 'Post Fraud Review',
    698: 'Finish Fraud Review',
    699: 'Order invalid or shipping more than 25 days and payment more than 5 days.',
    700: 'Order finished.',
    701: 'Order assumed as finished but the product not arrived yet to the buyer.',
}

ORDER_STATUS = [('%s' % (i), ORDER_STATUS_DICT.get(i, 'Reserved by Tokopedia.')) for i in range(0, 1000)]

SHOPEE_ORDER_STATUS = [
    ('UNPAID', 'Unpaid'),
    ('READY_TO_SHIP', 'Ready to Ship'),
    ('SHIPPED', 'Shipped'),
    ('COMPLETED', 'Completed'),
    ('TO_CONFIRM_RECEIVE', 'In Confirm Receive'),
    ('IN_CANCEL', 'In Cancel'),
    ('CANCELLED', 'Cancelled'),
    ('TO_RETURN', 'To Return'),
]

LAZADA_ORDER_STATUS = [
    ('unpaid', 'unpaid'),
    ('returned', 'returned'),
    ('shipped', 'shipped'),
    ('packed', 'packed'),
    ('repacked', 'repacked'),
    ('shipped', 'shipped'),
    ('failed', 'failed'),
    ('delivered', 'delivered'),
    ('canceled', 'canceled'),
    ('ready_to_ship', 'ready_to_ship'),
    ('ready_to_ship_pending', 'ready_to_ship_pending'),
    ('pending', 'pending'),
]

BLIBLI_ORDER_STATUS = [
    ('FP', 'Waiting'),
    ('PF', 'Ready To Ship'),
    ('CR', 'Customer Request'),
    ('CX', 'In Delivery'),
    ('PU', 'Waiting to Pick Up '),
    ('OS', 'Product Out of Stock'),
    ('BP', 'Big Product Ready to Deliver'),
    ('D', 'Delivered'),
    ('X', 'Canceled'),
]

class ResUsers(models.Model):
    _inherit = "res.users"
    izi_id = fields.Integer()

class ResPartner(models.Model):
    _inherit = 'res.partner'
    buyer_id = fields.Integer(string="Buyer ID")  # store the buyer_id for future reference
    buyer_username = fields.Char('Buyer Username')
    email = fields.Char('Buyer Email')
    phone = fields.Char('Buyer Phone')
    izi_id = fields.Integer()
class ProductProduct(models.Model):
    _inherit = 'product.product'
    izi_id = fields.Integer()
    
    _sql_constraints = [
        ('izi_unique', 'unique(izi_id)', 'Product with izi_id has already'),
    ]

    @api.model
    def create(self, vals_list):
        products = super(ProductProduct, self.with_context(create_product_product=True)).create(vals_list)
        for product in products:
            if 'izi_id' in self._fields:
                if not product.izi_id or product.izi_id == 0:
                    self._cr.execute('UPDATE %s SET izi_id = NULL WHERE id = %s' % (self._table, product.id))
        return products

    def write(self, values):
        res = super(ProductProduct, self).write(values)
        if 'izi_id' in self._fields:
            if not self.izi_id or self.izi_id == 0:
                self._cr.execute('UPDATE %s SET izi_id = NULL WHERE id = %s' % (self._table, self.id))
        return res

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    izi_id = fields.Integer()
    is_delivery = fields.Boolean(string="Is a Delivery", default=False)
    is_insurance = fields.Boolean(string="Is a Insurance", default=False)
    is_adjustment = fields.Boolean(string="Is a Adjustment", default=False)
    is_discount = fields.Boolean(string="Is a Discount", default=False)
class ResCompany(models.Model):
    _inherit = 'res.company'
    izi_id = fields.Integer()
class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'
    izi_id = fields.Integer()
class StockLocation(models.Model):
    _inherit = 'stock.location'
    izi_id = fields.Integer()

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # Change Order Status
    def action_done(self):
        for picking in self:
            server = self.env['webhook.server'].search([], limit=1)
            if not server:
                raise UserError('There is no webhook server.')
            if server.no_action_marketplace or server.no_action_picking_marketplace:
                continue
            # Check Marketplaces
            if picking.sale_id and picking.sale_id.mp_tokopedia_id:
                order = picking.sale_id
                if order.mp_delivery_type == 'drop off' and order.order_status in ('process', 'ready-ship'):
                    res = server.action_orders('confirm_shipping', [order.izi_id])
                    if not (res and res.get('code') == 200):
                        raise UserError('Failed to Confirm Shipping Tokopedia. %s' % str(res))
                # TODO: No Request Pickup From Validate Picking. Request Pickup is From Order Only
                # elif order.mp_delivery_type == 'pickup' and order.order_status in ('process', 'ready-ship'):
                #     res = server.action_orders('request_pickup', [order.izi_id])
                #     if not (res and res.get('code') == 200):
                #         raise UserError('Failed to Request Pickup Tokopedia. %s' % str(res))
            elif picking.sale_id and picking.sale_id.mp_shopee_id:
                order = picking.sale_id
                if order.mp_delivery_type == 'drop off':
                    res = server.action_orders('get_label', [order.izi_id])
                    if not (res and res.get('code') == 200):
                        raise UserError('Failed to DropOff Shopee.')
                # TODO: No Request Pickup From Validate Picking. Request Pickup is From Order Only
                # elif order.mp_delivery_type == 'pickup':
                #     order.action_orders_request_pickup()
                # elif order.mp_delivery_type == 'both':
                #     order.action_orders_request_pickup()
            elif picking.sale_id and picking.sale_id.mp_lazada_id:
                order = picking.sale_id
                if order.mp_delivery_type == 'drop off' and order.order_status == 'process':
                    res = server.action_orders('confirm_shipping', [order.izi_id])
                    if not (res and res.get('code') == 200):
                        raise UserError('Failed to Confirm Shipping Lazada. %s' % str(res))
                # TODO: No Request Pickup From Validate Picking. Request Pickup is From Order Only
                # elif order.mp_delivery_type == 'pickup' and order.order_status == 'ready-ship':
                #     res = server.action_orders('request_pickup', [order.izi_id])
                #     if not (res and res.get('code') == 200):
                #         raise UserError('Failed to Request Pickup Tokopedia.')
            elif picking.sale_id and picking.sale_id.mp_blibli_id:
                order = picking.sale_id
                if order.mp_delivery_type == 'drop off' and order.order_status == 'process':
                    res = server.action_orders('confirm_shipping', [order.izi_id])
                    if not (res and res.get('code') == 200):
                        raise UserError('Failed to Confirm Shipping Blibli. %s' % str(res))
                # TODO: No Request Pickup From Validate Picking. Request Pickup is From Order Only
                # elif order.mp_delivery_type == 'pickup' and order.order_status == 'ready-ship':
                #     res = server.action_orders('request_pickup', [order.izi_id])
                #     if not (res and res.get('code') == 200):
                #         raise UserError('Failed to Request Pickup Tokopedia.')
        return super(StockPicking, self).action_done()

class StockInventorySync(models.Model):
    _inherit = 'stock.inventory'

    # Syncronize Stock
    def action_validate(self):
        if not self.env.context.get('no_push'):
            for inventory in self:
                location = inventory.location_ids.ensure_one()
                wh = self.env['stock.warehouse'].sudo().search([('lot_stock_id', '=', location.id)])
                if (wh and wh.izi_id):
                    adjustment_data = []
                    for line in inventory.line_ids:
                        if line.product_id.izi_id and line.theoretical_qty != line.product_qty:
                            adjustment_data.append({
                                'product_id': line.product_id.izi_id,
                                'product_qty': line.product_qty,
                            })
                    if adjustment_data:
                        # Post to IZI
                        server = self.env['webhook.server'].sudo().search([], limit=1)
                        if server.no_action_marketplace:
                            continue
                        if server:
                            body = {
                                'warehouse_id': wh.izi_id if wh else False,
                                'adjustment_data': adjustment_data,
                            }
                            url = server.name + '/api/ui/stock/inventory'
                            res = requests.post(url, json=body, headers={
                                'X-Openerp-Session-Id': server.session_id,
                            })
                            res = res.json()
                            if not (res and res.get('code') == 200):
                                if res.get('data'):
                                    if res.get('data').get('error_describ'):
                                        raise UserError(res.get('data').get('error_descrip'))
                                else:
                                    raise UserError('Failed to Validate Inventory.')

        return super(StockInventorySync, self).action_validate()

class StockPickingSync(models.Model):
    _inherit = 'stock.picking'

    # Syncronize Stock
    def action_done(self):
        for picking in self:
            if not picking.sale_id:
                # Get Warehouse
                wh = self.env['stock.warehouse'].sudo().search([('lot_stock_id', '=', picking.location_id.id)])
                wh_dest = self.env['stock.warehouse'].sudo().search([('lot_stock_id', '=', picking.location_dest_id.id)])
                
                if (wh and wh.izi_id) or (wh_dest and wh_dest.izi_id):
                    # Prepare move_lines
                    move_lines = []
                    for ml in picking.move_lines:
                        if ml.product_id.izi_id:
                            move_lines.append({
                                'name': ml.product_id.name,
                                'product_id': ml.product_id.izi_id,
                                'product_uom_qty': ml.product_uom_qty,
                                'quantity_done': ml.quantity_done,
                                'product_uom': ml.product_id.uom_id.id,
                            })
                    # Post to IZI
                    server = self.env['webhook.server'].search([], limit=1)
                    if server.no_action_marketplace:
                        continue
                    if server:
                        body = {
                            'name': picking.name,
                            'warehouse_id': wh.izi_id if wh else False,
                            'warehouse_dest_id': wh_dest.izi_id if wh_dest else False,
                            'move_lines': move_lines,
                        }
                        url = server.name + '/api/ui/stock/picking'
                        res = requests.post(url, json=body, headers={
                            'X-Openerp-Session-Id': server.session_id,
                        })
                        res = res.json()
                        if not (res and res.get('code') == 200):
                            raise UserError('Failed to Validate Picking.')

        return super(StockPickingSync, self).action_done()

class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = 'sale.order'

    izi_id = fields.Integer()
    mp_channel = fields.Selection([
        ('tp', 'Tokopedia'),
        ('sp', 'Shopee'),
        ('lz', 'Lazada'),
        ('bli', 'Blibli'),
    ], compute='_compute_mp_channel')
    order_status = fields.Selection([
            ('new', 'Baru'),
            ('waiting', 'Menunggu Pembayaran'),
            ('cancel', 'Batal'),
            ('ready-process', 'Siap Proses'),
            ('process', 'Dalam Proses'),
            ('ready-ship', 'Siap Dikirim'),
            ('ship', 'Dalam Pengiriman'),
            ('done', 'Selesai'),
            ('return', 'Dikembalikan'),
        ], track_visibility='always')
    # ,compute='_compute_order_status',store=True,
    
    order_status_notes = fields.Char()
    cancel_by_customer = fields.Boolean()

    # Marketplace Fields
    mp_update_order_time = fields.Datetime()
    mp_payment_method_info = fields.Char('Payment Method')
    mp_awb_number = fields.Char('Nomor Resi')
    mp_awb_url = fields.Text('URL Resi')

    mp_invoice_number = fields.Char('Invoice Number')
    mp_buyer_username = fields.Char('Buyer Username')
    mp_buyer_name = fields.Char('Buyer Name')
    mp_buyer_email = fields.Char('Buyer Email')
    mp_buyer_phone = fields.Char('Buyer Phone')
    mp_cancel_reason = fields.Char('Cancel Reason')
    mp_recipient_address_city = fields.Char('Recipient City')
    mp_recipient_address_name = fields.Char('Recipient name')
    mp_recipient_address_district = fields.Char('Recipient District')
    mp_recipient_address_country = fields.Char('Recipient Country')
    mp_recipient_address_zipcode = fields.Char('Recipient Zipcode')
    mp_recipient_address_phone = fields.Char('Recipient Phone')
    mp_recipient_address_state = fields.Char('Recipient State')
    mp_recipient_address_full = fields.Text('Recipient Full Address')
    mp_amount_insurance = fields.Integer()
    mp_delivery_carrier_name = fields.Char('Delivery Name')
    mp_delivery_carrier_type = fields.Char('Delivery Carrier Type')
    mp_delivery_type = fields.Selection([
            ('pickup', 'Pickup'),
            ('drop off', 'Drop Off'),
            ('both','Pickup & Drop Off')])
    mp_accept_deadline = fields.Datetime(string='Batas Tanggal Konfirmasi')
    shipping_date = fields.Datetime(string='Batas Tanggal Pengiriman')


    # Tokopedia
    tp_order_status = fields.Selection(ORDER_STATUS)
    mp_tokopedia_id = fields.Many2one('mp.tokopedia', string='Tokopedia Account', ondelete='cascade')
    tp_order_id = fields.Integer()
    tp_invoice_url = fields.Text('Invoice URL')
    tp_reason_close_date = fields.Datetime()
    tp_reason_note = fields.Text('Reason Note')
    tp_cancel_request_create_time = fields.Datetime('Request Time')
    tp_cancel_request_reason = fields.Text('Reason')
    tp_cancel_request_status = fields.Integer('Request Cancel Reason Status')
    tp_comment = fields.Text('Comment')
    mp_delivery_weight = fields.Float(string='Weight (KG)')

    # Shopee
    mp_shopee_id = fields.Many2one('mp.shopee', string='Shopee Account', ondelete='cascade')
    sp_order_status = fields.Selection(SHOPEE_ORDER_STATUS)
    sp_cancel_by = fields.Selection([
        ('buyer','Buyer'), 
        ('seller','Seller'),
        ('system','System')
    ], 'Cancel By')

    # Lazada
    mp_lazada_id = fields.Many2one('mp.lazada', string='Lazada Account', ondelete='cascade')
    lz_order_status = fields.Selection(LAZADA_ORDER_STATUS)

    # Blibli
    mp_blibli_id = fields.Many2one('mp.blibli', string='Blibli Account', ondelete='cascade')
    bli_order_status = fields.Selection(BLIBLI_ORDER_STATUS)

    # TODO: Add sale.order.cancel.reason
    cancel_reason_id = fields.Many2one('sale.order.cancel.reason', 'Cancel Order Reason')
    pickup_ids = fields.One2many('sale.order.pickup.info', 'order_id')
    
    no_action_marketplace = fields.Boolean('Unsync Marketplace Action', default=False)

    _sql_constraints = [
        ('sale_order_invoice_unique', 'unique(mp_invoice_number)', 'Invoice already exist'),
    ]

    @api.depends('state', 'picking_ids', 'invoice_ids', 'sp_order_status','picking_ids.state', 'invoice_ids.state', 'tp_order_status','mp_awb_number','mp_tokopedia_id','mp_shopee_id', 'mp_lazada_id', 'lz_order_status', 'mp_blibli_id', 'bli_order_status')
    def _compute_order_status(self):
        # Deprecated.
        return True
        for order in self:
            # Default State From Odoo
            order_status = 'new'
            if (order.state == 'cancel'):
                order_status = 'cancel'
            elif(not order.picking_ids and not order.invoice_ids):
                order_status = 'new'
            elif(order.invoice_ids and order.invoice_ids[0].state == 'paid') and (order.picking_ids and order.picking_ids[0].state == 'done'):
                order_status = 'done'
            elif(order.picking_ids and order.picking_ids[0].state != 'done'):
                order_status = 'process'
            elif (order.invoice_ids and order.invoice_ids[0].state != 'paid'):
                order_status = 'waiting'

            # Tokopedia
            if order.mp_tokopedia_id:
                tokopedia_order_status = order.tp_order_status
                if (tokopedia_order_status in [550, ]):
                    order_status = 'return'
                    order.action_done()
                elif (tokopedia_order_status in [600, 601, 700, 701, ]):
                    order_status = 'done'
                    order.action_done()
                elif (tokopedia_order_status in [500, 501, 520, 530, 540, ]):
                    order_status = 'ship'
                    order.action_confirm()
                elif (tokopedia_order_status in [450, 400]):
                    order_status = 'ready-ship'
                    order.action_confirm()
                elif (tokopedia_order_status in [220, 221, ]):
                    order_status = 'ready-process'
                    order.action_draft()
                elif (tokopedia_order_status in [0, 2, 3, 4, 5, 10, 690, 691, 695, 698, 699, ]):
                    order_status = 'cancel'
                    order.action_cancel()
                elif (tokopedia_order_status in [11, 100, 103, 200, ]):
                    order_status = 'waiting'
                    order.action_draft()
            # Shopee
            if order.mp_shopee_id:
                shopee_order_status = order.sp_order_status
                if (shopee_order_status == 'TO_RETURN'):
                    order_status = 'return'
                    order.action_done()
                elif (shopee_order_status == 'COMPLETED'):
                    order_status = 'done'
                    order.action_done()
                elif (shopee_order_status in ('READY_TO_SHIP','IN_CANCEL')):
                    if shopee_order_status == 'IN_CANCEL':
                        order.cancel_by_customer = True
                        order_status = 'process'
                    elif shopee_order_status == 'IN_CANCEL' and order.mp_awb_number:
                        order_status = 'ready-ship'
                        order.cancel_by_customer = True
                    elif shopee_order_status == 'READY_TO_SHIP' and order.mp_awb_number:
                        order_status = 'ready-ship'
                        order.action_confirm()
                    else:
                        order_status = 'process'
                        order.action_draft()
                elif (shopee_order_status in ('SHIPPED')):
                    order_status = 'ship'
                    order.action_validate_picking()
                elif (shopee_order_status == 'CANCELLED'):
                    order_status = 'cancel'
                    order.action_cancel()
                elif (shopee_order_status == 'UNPAID'):
                    order_status = 'waiting'
                    order.action_draft()
            # Lazada
            if order.mp_lazada_id:
                lazada_order_status = order.lz_order_status
                if (lazada_order_status == 'returned'):
                    order_status = 'return'
                    order.action_done()
                elif (lazada_order_status == 'delivered'):
                    order_status = 'done'
                    order.action_done()
                elif (lazada_order_status in ('pending', 'repacked')):
                    order_status = 'process'
                    order.action_draft()
                elif (lazada_order_status == 'packed'):
                    order_status = 'ready-process'
                    order.action_draft()
                elif (lazada_order_status in ('ready_to_ship', 'ready_to_ship_pending')):
                    order_status = 'ready-ship'
                    order.action_confirm()
                elif (lazada_order_status == 'shipped'):
                    order_status = 'ship'
                    order.action_confirm()
                elif (lazada_order_status in ('failed', 'canceled')):
                    order_status = 'cancel'
                    order.action_cancel()
                elif (lazada_order_status == 'unpaid'):
                    order_status = 'waiting'
                    order.action_draft()
            
            # Blibli
            if order.mp_blibli_id:
                blibli_order_status = order.bli_order_status
                if (blibli_order_status == 'FP'):
                    order_status = 'ready-process'
                    order.action_draft()
                elif (blibli_order_status == 'X'):
                    order_status = 'cancel'
                    order.action_cancel()
                elif (blibli_order_status == 'D'):
                    order_status = 'done'
                    order.action_done()
                elif (blibli_order_status == 'CX'):
                    order_status = 'ship'
                    order.action_confirm()
                elif (blibli_order_status in ('PF', 'PU')):
                    order_status = 'ready-ship'
                    order.action_confirm()

            # Set Status
            order.order_status = order_status

    # TODO: Where is Shopee and Lazada Code?
    def action_confirm(self):
        if not self.env.context.get('no_push'):
            for order in self:
                if order.mp_tokopedia_id:
                    server = order.get_webhook_server()
                    if server.no_action_marketplace or order.no_action_marketplace:
                        continue
                    # First, Accept The Order
                    if order.order_status == 'ready-process':
                        res = server.action_orders('accept_order', [order.izi_id], refresh=False)
                        if not (res and res.get('code') == 200):
                            raise UserError('Failed to Accept Order Tokopedia. %s' % str(res))
                    # # Second, Get No Resi
                    # res = server.action_orders('get_label', [order.izi_id])
                    # if not (res and res.get('code') == 200):
                    #     # raise UserError('Failed to Get No Resi Tokopedia. %s' % str(res))
                    #     _logger.error('Failed to Get No Resi Tokopedia. %s' % str(res))
                    # elif res.get('data') and res.get('data').get('awb_number'):
                    #     order.mp_awb_number = res['data']['awb_number'][0]
        return super(SaleOrder, self).action_confirm()

    # TODO: Where is Shopee and Lazada Code?
    def action_cancel(self):
        if not self.env.context.get('no_push'):
            for order in self:
                if order.mp_tokopedia_id:
                    server = order.get_webhook_server()
                    if server.no_action_marketplace or order.no_action_marketplace:
                        continue
                    if order.order_status not in ('cancel', 'done'):
                        res = server.action_orders('reject_order', [order.izi_id])
                        if not (res and res.get('code') == 200):
                            raise UserError('Failed to Reject Order Tokopedia. %s' % str(res))
                if order.mp_shopee_id:
                    server = order.get_webhook_server()
                    if server.no_action_marketplace or order.no_action_marketplace:
                        continue
                    if order.order_status not in ('cancel', 'done'):
                        super(SaleOrder, self).action_cancel()
                        form_view = self.env.ref('juragan_product.sale_cancel_form')
                        return {
                            'name': 'Cancel Order',
                            'view_mode': 'form',
                            'res_model': 'sale.cancel.wizard',
                            'view_id' : form_view.id,
                            'type': 'ir.actions.act_window',
                            'target': 'new',
                            'context' : {'mp_type':'shp'},
                        }
                        
        
        return super(SaleOrder, self).action_cancel()

    @api.depends('mp_tokopedia_id', 'mp_shopee_id', 'mp_lazada_id', 'mp_blibli_id')
    def _compute_mp_channel(self):
        for order in self:
            if order.mp_tokopedia_id:
                order.mp_channel = 'tp'
            elif order.mp_shopee_id:
                order.mp_channel = 'sp'
            elif order.mp_lazada_id:
                order.mp_channel = 'lz'
            elif order.mp_blibli_id:
                order.mp_channel = 'bli'
            else:
                order.mp_channel = False

    def action_by_order_status(self):
        for order in self:
            try:
                if order.order_status == 'return':
                    order.action_cancel()
                elif order.order_status == 'done':
                    order.action_confirm()
                    order.action_done()
                elif order.order_status == 'ship':
                    order.action_confirm()
                elif order.order_status == 'ready-ship' or order.order_status == 'process':
                    order.action_confirm()
                elif order.order_status == 'ready-process':
                    order.action_draft()
                elif order.order_status == 'cancel':
                    order.action_cancel()
                elif order.order_status == 'waiting':
                    order.action_draft()
            except Exception as e:
                print(str(e))

    def get_webhook_server(self):
        server = self.env['webhook.server'].search([], limit=1)
        if not server:
            raise UserError('There is no webhook server.')
        if not self.mapped('izi_id'):
            raise UserError('There is no izi_id.')
        return server

    def action_orders_cancel(self):
        form_view = self.env.ref('juragan_product.sale_cancel_form')
        if self.mp_shopee_id:
            mp_type = 'shp'
        elif self.mp_tokopedia_id:
            mp_type = 'tp'
        elif self.mp_lazada_id:
            mp_type = 'lz'
        elif self.mp_blibli_id:
            mp_type = 'bli'

        return {
            'name': 'Cancel Order',
            'view_mode': 'form',
            'res_model': 'sale.cancel.wizard',
            'view_id' : form_view.id,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context' : {'mp_type':mp_type},
        }

    def action_validate_picking(self):
        for order in self:
            for picking in order.picking_ids:
                picking.action_confirm()
                for move_line in picking.move_lines:
                    # Force Done!
                    move_line.quantity_done = move_line.product_uom_qty
                    # move_line._action_assign()
                    # if move_line.state == 'assigned':
                    #     move_line.quantity_done = move_line.product_uom_qty
                picking.action_done()

    # Not Used. To Be Deleted.
    def action_pay_invoice(self):
        for order in self:
            order._create_invoices(final=True)
            for invoice in order.invoice_ids:
                # invoice.action_invoice_open()
                invoice.action_post()
                journal = self.env['account.journal'].search([('type', '=', 'bank')], limit=1)
                if journal:
                    #create payment
                    payment = self.env['account.payment'].create({
                        'payment_type': 'inbound',
                        'partner_type': 'customer',
                        'partner_id': invoice.partner_id.id,
                        'payment_date': invoice.invoice_date,
                        'amount': invoice.amount_residual,
                        'journal_id':journal.id,
                        'payment_method_id': self.env.ref('account.account_payment_method_manual_in').id
                    })
                    if payment:
                        # post payment
                        payment.post()

                        for aml in payment.move_line_ids:
                            # reconcile payment
                            if aml.account_id.user_type_id == self.env.ref('account.data_account_type_receivable'):
                                invoice.js_assign_outstanding_line(aml.id)
                    

                    # invoice.pay_and_reconcile(pay_journal=journal)

    def action_orders_accept(self):
        server = self.get_webhook_server()
        for order in self:
            res = server.action_orders('accept_order', [order.izi_id])
            if res and res.get('code') == 200:
                pass
                # order.action_confirm()

    def action_orders_reject(self):
        server = self.get_webhook_server()
        for order in self:
            res = server.action_orders('reject_order', [order.izi_id])
        
    def action_orders_packing(self):
        server = self.get_webhook_server()
        for order in self:
            res = server.action_orders('packing', [order.izi_id])
            if res['code'] == 400:
                raise UserError('Failed to Packing Order Blibli. %s' % str(res['data']['error']))

    def action_orders_status(self):
        server = self.get_webhook_server()
        for order in self:
            res = server.action_orders('update_status', [order.izi_id])
            if res['code'] == 400:
                raise UserError('Failed to Update Status Order Blibli. %s' % str(res['data']['error']))
    
    def action_orders_confirm_shipping(self):
        server = self.get_webhook_server()
        form_view = self.env.ref('juragan_product.confirm_shipping_form')
        for order in self:
            if order.mp_lazada_id:
                res = server.action_orders('ready_to_ship', [order.izi_id])
            else:
                return {
                'name': 'Confirm Shipping',
                'view_mode': 'form',
                'res_model': 'confirm.shipping.wizard',
                'view_id': form_view.id,
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': {
                    'order_id': order.id,
                    'default_mp_awb_number': order.mp_awb_number
                }
            }
            

    def action_orders_accept_cancel(self):
        form_view = self.env.ref('juragan_product.accept_sale_cancel_form')
        return {
            'name': 'Accept Cancel Order',
            'view_mode': 'form',
            'res_model': 'accept.sale.cancel.wizard',
            'view_id' : form_view.id,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def action_orders_reject_cancel(self):
        form_view = self.env.ref('juragan_product.reject_sale_cancel_form')
        return {
            'name': 'Reject Cancel Order',
            'view_mode': 'form',
            'res_model': 'reject.sale.cancel.wizard',
            'view_id' : form_view.id,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }
    
    def action_orders_request_pickup(self):
        server = self.get_webhook_server()
        if self.mp_shopee_id:
            if not self.mp_awb_number:
                res = server.get_pickup_info([self.izi_id])
                pickup_obj = self.env['sale.order.pickup.info']
                shop_obj = self.env['mp.shop.address']
                if res['code'] == 200:
                    form_view = self.env.ref('juragan_product.request_pickup_form')
                    server.get_records('mp.shop.address')
                    data = res['data']

                    orders = self.env['sale.order'].search([
                        ('mp_shopee_id', '!=', False)
                    ])
                    order_by_izi_id = {}
                    for order in orders:
                        order_by_izi_id[order.izi_id] = order

                    shops = shop_obj.search([])
                    shop_by_izi_id = {}
                    for shop in shops:
                        shop_by_izi_id[shop.izi_id] = shop

                    pickup_data = pickup_obj.sudo().search([('order_id','=',self.id),'|',('active','=',True),('active','=',False)])
                    if pickup_data:
                        for pickup in pickup_data:
                            pickup.sudo().unlink()

                    for pickup_list in data['pickup_list']:
                        address_id = pickup_list['address_id']
                        if address_id in shop_by_izi_id:
                            addr_id = shop_by_izi_id[address_id]
                        orderid = pickup_list['order_id']
                        if orderid in order_by_izi_id:
                            order_id = order_by_izi_id[orderid]
                        
                        vals = {
                            'name' : pickup_list['name'],
                            'address_id' : addr_id.id,
                            'end_datetime': pickup_list['end_datetime'],
                            'start_datetime' : pickup_list['start_datetime'],
                            'order_id': order_id.id,
                            'izi_id' : pickup_list['id'],
                            'active': False
                        }
                        pickup_obj.sudo().create(vals)

                    return {
                        'name': 'Request Pickup',
                        'view_mode': 'form',
                        'res_model': 'request.pickup.wizard',
                        'view_id' : form_view.id,
                        'type': 'ir.actions.act_window',
                        'target': 'new',
                        'context' : {
                            'order_id':order_id.id,
                            'mp_shopee_ids': [self.mp_shopee_id.id]
                            },
                    }
            else:
                raise UserError('Request Pickup Failed, AWB Number is Exist')

        if self.mp_tokopedia_id:        
            res = server.action_orders('request_pickup', [self.izi_id])
            if res and res.get('code') == 200:
                self.action_validate_picking()

    def action_orders_get_label(self):
        for rec in self:
            if rec.state in ('draft', 'cancel'):
                raise UserError('Can not get label from quotation or cancelled order. Confirm order first!')
        server = self.get_webhook_server()
        if self.mapped('mp_tokopedia_id'):
            res = server.action_orders('get_label', self.mapped('izi_id'))
            if res.get('data') and res.get('data').get('url') and server.session_id:
                if isinstance(res['data']['url'], list):
                    for url in res['data']['url']:
                        return {
                            'name': 'Label',
                            'res_model': 'ir.actions.act_url',
                            'type': 'ir.actions.act_url',
                            'target': 'new',
                            'url': url+'&session_id='+server.session_id,
                        }
                elif isinstance(res['data']['url'], str):
                    return {
                            'name': 'Label',
                            'res_model': 'ir.actions.act_url',
                            'type': 'ir.actions.act_url',
                            'target': 'new',
                            'url': res['data']['url']+'&session_id='+server.session_id,
                        }
        if self.mapped('mp_lazada_id'):
            res = server.action_orders('get_label', self.mapped('izi_id'))
            if res.get('data') and res.get('data').get('url') and server.session_id:
                if isinstance(res['data']['url'], list):
                    for url in res['data']['url']:
                        return {
                            'name': 'Label',
                            'res_model': 'ir.actions.act_url',
                            'type': 'ir.actions.act_url',
                            'target': 'new',
                            'url': url+'&session_id='+server.session_id,
                        }
                elif isinstance(res['data']['url'], str):
                    return {
                            'name': 'Label',
                            'res_model': 'ir.actions.act_url',
                            'type': 'ir.actions.act_url',
                            'target': 'new',
                            'url': res['data']['url']+'&session_id='+server.session_id,
                        }
        if self.mapped('mp_shopee_id'):
            for order in self:
                if order.mp_awb_url:
                    return {
                        'name': 'Label',
                        'res_model': 'ir.actions.act_url',
                        'type': 'ir.actions.act_url',
                        'target': 'new',
                        'url': order.mp_awb_url+'&session_id='+server.session_id,
                    }
                elif order.mp_delivery_type == 'pickup' and not order.mp_awb_number:
                    raise UserError('Please Request Pickup before Get Label for Shopee Order with Pickup Delivery type ')
                else:
                    res = server.action_orders('get_label', [order.izi_id])
                    if res['code'] == 200:
                        domain_url = "[('id', '=', %i)]" % int(order.izi_id)
                        server.get_records('sale.order',domain_url=domain_url)
                        if res.get('data') and res.get('data').get('url') and server.session_id:
                            if isinstance(res['data']['url'], list):
                                for url in res['data']['url']:
                                    return {
                                        'name': 'Label',
                                        'res_model': 'ir.actions.act_url',
                                        'type': 'ir.actions.act_url',
                                        'target': 'new',
                                        'url': url+'&session_id='+server.session_id,
                                    }
                            elif isinstance(res['data']['url'], str):
                                return {
                                        'name': 'Label',
                                        'res_model': 'ir.actions.act_url',
                                        'type': 'ir.actions.act_url',
                                        'target': 'new',
                                        'url': res['data']['url']+'&session_id='+server.session_id,
                                    }
                    elif res['code'] == 429:
                        form_view = self.env.ref('juragan_product.popup_message_wizard')
                        view_id = form_view and form_view.id or False
                        context = dict(self._context or {})
                        context['message'] = 'AWB Number is not available, Please waiting a few minutes.'
                        return {
                            'name': 'Warning',
                            'type': 'ir.actions.act_window',
                            'view_mode': 'form',
                            'view_type': 'form',
                            'res_model': 'popup.message.wizard',
                            'views': [(view_id,'form')],
                            'view_id' : form_view.id,
                            'target': 'new',
                            'context': context,
                        }
                    else:
                        raise UserError('Get Label Failed %s' % str(res))
    
class WebhookServer(models.Model):
    _inherit = 'webhook.server'
    
    mp_tokopedia_ids = fields.One2many('mp.tokopedia', 'server_id', 'Tokopedia Account')
    mp_shopee_ids = fields.One2many('mp.shopee', 'server_id', 'Shopee Account')
    mp_lazada_ids = fields.One2many('mp.lazada', 'server_id', 'Lazada Account')
    mp_blibli_ids = fields.One2many('mp.blibli', 'server_id', 'Blibli Account')

    #
    # API Get Specific
    #
    def action_orders(self, action_code, order_ids=[], cancel_reason_id=False, picking_time_id=False, address_id=False,
                      refresh=False, mp_awb_number=False, **kwargs):
        body = {
            'request_by': 'odoo',
            'action_code': action_code,
            'order_ids': order_ids,
        }
        if action_code == 'reject_order':
            body.update({
                'cancel_reason_id': cancel_reason_id,
            })
            if 'shop_close_end_date' in kwargs and 'shop_close_note' in kwargs:
                body.update({
                    'shop_close_end_date': kwargs['shop_close_end_date'],  # Format: DD/MM/YYYY
                    'shop_close_note': kwargs['shop_close_note']
                })
        elif action_code == 'request_pickup':
            body.update({
                'picking_time_id': picking_time_id,
                'address_id' : address_id
            })
        elif action_code == 'confirm_shipping':
            body.update({
                'mp_awb_number': mp_awb_number
            })
        elif action_code == 'ready_to_ship':
            pass
        r = requests.post(self.name + '/ui/v2/orders/action/', json=body, headers={
            'X-Openerp-Session-Id': self.session_id,
        })
        res = json.loads(r.text) if r.status_code == 200 else {}
        if res:
            res = res['result']
            domain_url = "[('id', 'in', %s)]" % str(order_ids)
            try:
                self.get_records('sale.order', domain_url=domain_url, force_update=True)
            except Exception as e:
                _logger.info(str(e))
            if refresh:
                self.with_context(no_push=True).sync_order()
        return res
    
    def get_pickup_info(self, order_ids=[]):
        r = requests.post(self.name + '/ui/v2/orders/logistic/info', json={
            'order_ids': order_ids
        }, headers={
            'X-Openerp-Session-Id': self.session_id,
        })
        res = json.loads(r.text) if r.status_code == 200 else {}
        if res:
            res = res['result']
        return res


class AddressShop(models.Model):
    _name = 'mp.shop.address'

    name = fields.Text('Address')
    address_id = BigInteger('Address ID')
    country = fields.Char('Country')
    state = fields.Char('State')
    city = fields.Char('City')
    zipcode = fields.Char('Zipcode')
    district = fields.Char('District')
    town = fields.Char('Town')
    default_address = fields.Boolean(store=True)
    pickup_address = fields.Boolean(store=True)
    return_address = fields.Boolean(store=True)
    pickup_ids = fields.One2many('sale.order.pickup.info','address_id')
    mp_shopee_ids = fields.Many2many('mp.shopee')

    izi_id = fields.Integer('Izi ID')

class PickupInformation(models.Model):
    _name = 'sale.order.pickup.info'


    name = fields.Char('Pickup Time ID')
    start_datetime = fields.Datetime('Start Datetime')
    end_datetime = fields.Datetime('End Datetime')
    order_id = fields.Many2one('sale.order')
    address_id = fields.Many2one('mp.shop.address')
    state = fields.Selection([
        ('waiting','Menunggu Penjemputan'),
        ('done','Pickup Selesai')
    ])
    active = fields.Boolean(default=False,store=True)

    izi_id = fields.Integer('Izi ID')

    # @api.multi
    def name_get(self):
        res=[]
        date_dict = {
            'Monday':'Senin',
            'Tuesday':'Selasa',
            'Wednesday': 'Rabu',
            'Thursday': 'Kamis',
            'Friday': 'Jum\'at',
            'Saturday': 'Sabtu',
            'Sunday': 'Minggu',
            'Senin':'Senin',
            'Selasa': 'Selasa',
            'Rabu': 'Rabu',
            'Kamis': 'Kamis',
            'Jumat': 'Jum\'at',
            'Sabtu': 'Sabtu',
            'Minggu': 'Minggu',
        }
        for rec in self:
            day = date_dict[rec.start_datetime.strftime('%A')]
            start_datetime = rec.start_datetime.strftime('%d-%m-%y, %H:%M')
            end_datetime = rec.end_datetime.strftime('%H:%M') if rec.end_datetime else False
            if start_datetime and end_datetime:
                time =  start_datetime + '-' + end_datetime
            elif start_datetime and not end_datetime:
                time =  start_datetime

            date_time = day+', '+time

            res.append((rec.id, date_time))
        return res

class CancelReasonOrder(models.Model):
    _name = 'sale.order.cancel.reason'
    _rec_name = 'reason_status'

    name = fields.Selection([
        ('OUT_OF_STOCK','Out Of Stock'),
        ('CUSTOMER_REQUEST','Customer Request'), 
        ('UNDELIVERABLE_AREA','Undeliverable Area'), 
        ('COD_NOT_SUPPORT','Cod Not Support'),
        ('1','Product(s) out of stock'),
        ('2','Product variant unavailable'),
        ('3','Wrong price or weight'),
        ('4','Shop Closed'),
        ('5','Others'),
        ('6','Courier Problem'),
        ('7','Buyer’s request'),
        ('10','Sourcing Delay(cannot meet deadline)'),
        ('11','System Error'),
        ('13','Incorrect or Incomplete Shipping Address'),
        ('14','Out of Delivery Area'),
        ('15','Out of Stock'),
        ('16','Customer unreachable'),
        ('17','Duplicate order'),
        ('21','Wrong Price or Pricing Error')
    ])

    mp_type = fields.Selection([
        ('shp','Shopee'),
        ('tp','Tokopedia'), 
        ('lz','Lazada'), 
        ('bli','Blibli'),
    ])

    reason_status = fields.Char(store=True)
    order_ids = fields.One2many(comodel_name='sale.order', inverse_name='cancel_reason_id', string='Order')
    
    izi_id = fields.Integer('Izi ID')

    # # @api.multi
    # def name_get(self):
    #     result = []
    #     mp_type = self._context.get('mp_type','')
    #     reasons = self.search([('mp_type','=',mp_type)])
    #     if reasons:
    #         for reason in reasons:
    #             result.append((reason.id,reason.reason_status))
    #     return result
