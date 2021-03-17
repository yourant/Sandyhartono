from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import requests
import json
import datetime
from odoo.addons.juragan_webhook import BigMany2one, BigInteger


ORDER_STATUS_DICT = {
    '0': 'Seller cancel order.',
    '2': 'Order Reject Replaced.',
    '3': 'Order Reject Due Empty Stock.',
    '4': 'Order Reject Approval.',
    '5': 'Order Canceled by Fraud',
    '10': 'Order rejected by seller.',
    '11': 'Order Pending Replacement.',
    '100': 'Pending order.',
    '103': 'Wait for payment confirmation from third party.',
    '200': 'Payment confirmation.',
    '220': 'Payment verified, order ready to process.',
    '221': 'Waiting for partner approval.',
    '400': 'Seller accept order.',
    '450': 'Waiting for pickup.',
    '500': 'Order shipment.',
    '501': 'Status changed to waiting resi have no input.',
    '520': 'Invalid shipment reference number (AWB).',
    '530': 'Requested by user to correct invalid entry of shipment reference number.',
    '540': 'Delivered to Pickup Point.',
    '550': 'Return to Seller.',
    '600': 'Order delivered.',
    '601': 'Buyer open a case to finish an order.',
    '690': 'Fraud Review',
    '691': 'Suspected Fraud',
    '695': 'Post Fraud Review',
    '698': 'Finish Fraud Review',
    '699': 'Order invalid or shipping more than 25 days and payment more than 5 days.',
    '700': 'Order finished.',
    '701': 'Order assumed as finished but the product not arrived yet to the buyer.',
}

ORDER_STATUS = [(str(i), ORDER_STATUS_DICT.get(i, 'Reserved by Tokopedia.')) for i in range(0, 1000)]

SHOPEE_ORDER_STATUS = [
    ('UNPAID', 'Unpaid'),
    ('READY_TO_SHIP', 'Ready to Ship'),
    ('SHIPPED', 'Shipped'),
    ('COMPLETED', 'Completed'),
    ('IN_CANCEL', 'In Cancel'),
    ('CANCELLED', 'Cancelled'),
    ('TO_RETURN', 'To Return'),
]

class ResPartner(models.Model):
    _inherit = 'res.partner'
    izi_id = fields.Integer()
    buyer_id = fields.Integer()
    buyer_username = fields.Char()
class ProductProduct(models.Model):
    _inherit = 'product.product'
    izi_id = fields.Integer()
class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    izi_id = fields.Integer()
class ResCompany(models.Model):
    _inherit = 'res.company'
    izi_id = fields.Integer()
class MPTokopedia(models.Model):
    _inherit = 'mp.tokopedia'
    izi_id = fields.Integer()
    server_id = fields.Many2one('webhook.server')
    wh_id = fields.Many2one('stock.warehouse', string='Warehouse')
class MPShopee(models.Model):
    _inherit = 'mp.shopee'
    izi_id = fields.Integer()
    server_id = fields.Many2one('webhook.server')
    wh_id = fields.Many2one('stock.warehouse', string='Warehouse')
class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'
    izi_id = fields.Integer()
class StockLocation(models.Model):
    _inherit = 'stock.location'
    izi_id = fields.Integer()



class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = 'sale.order'

    izi_id = fields.Integer()
    mp_channel = fields.Selection([
        ('tp', 'Tokopedia'),
        ('sp', 'Shopee'),
        ('lz', 'Lazada'),
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
        ])
    
    order_status_notes = fields.Char()
    cancel_by_customer = fields.Boolean()

    # Marketplace Fields
    mp_update_order_time = fields.Datetime()
    mp_payment_method_info = fields.Char('Payment Method')
    mp_awb_number = fields.Char('Nomor Resi')
    mp_awb_url = fields.Text('URL Resi')

    mp_invoice_number = fields.Char('Invoice Number')
    mp_buyer_id = fields.Integer(string="Buyer ID")
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
    mp_delivery_type = fields.Selection([
            ('pickup', 'Pickup'),
            ('drop off', 'Drop Off')])
    shipping_date = fields.Date(string='Batas Tanggal Pengiriman')

    # Tokopedia
    tp_order_status = fields.Selection(ORDER_STATUS)
    mp_tokopedia_id = fields.Many2one('mp.tokopedia', string='Tokopedia Account', ondelete='cascade')
    tp_order_id = fields.Integer()
    tp_invoice_url = fields.Text('Invoice URL')
    tp_reason_close_date = fields.Datetime()
    tp_reason_note = fields.Text('Reason Note')

    # Shopee
    mp_shopee_id = fields.Many2one('mp.shopee', string='Shopee Account', ondelete='cascade')
    sp_order_status = fields.Selection(SHOPEE_ORDER_STATUS)
    sp_cancel_by = fields.Selection([
        ('buyer','Buyer'), 
        ('seller','Seller'),
        ('system','System')
    ], 'Cancel By')

    # TODO: Add sale.order.cancel.reason
    cancel_reason_id = fields.Many2one('sale.order.cancel.reason', 'Cancel Order Reason')
    pickup_ids = fields.One2many('sale.order.pickup.info', 'order_id')

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        for order in self:
            if order.mp_tokopedia_id:
                server = order.get_webhook_server()
                server.action_orders('accept_order', [order.izi_id])

    def action_cancel(self):
        res = super(SaleOrder, self).action_cancel()
        for order in self:
            if order.mp_tokopedia_id:
                server = order.get_webhook_server()
                server.action_orders('reject_order', [order.izi_id])

    @api.depends('mp_tokopedia_id', 'mp_shopee_id')
    def _compute_mp_channel(self):
        for order in self:
            if order.mp_tokopedia_id:
                order.mp_channel = 'tp'
            if order.mp_shopee_id:
                order.mp_channel = 'sp'

    def action_by_order_status(self):
        for order in self:
            if order.order_status == 'return':
                order.action_done()
            elif order.order_status == 'done':
                order.action_done()
            elif order.order_status == 'ship':
                order.action_confirm()
            elif order.order_status == 'ready-ship':
                order.action_confirm()
            elif order.order_status == 'ready-process':
                order.action_draft()
            elif order.order_status == 'cancel':
                order.action_cancel()
            elif order.order_status == 'waiting':
                order.action_draft()

    def get_webhook_server(self):
        server = self.env['webhook.server'].search([], limit=1)
        if not server:
            raise UserError('There is no webhook server.')
        if not self.izi_id:
            raise UserError('There is no izi_id.')
        return server

    def action_orders_reject(self):
        # server = self.get_webhook_server()
        # res = server.action_orders('reject_order', [self.izi_id])
        # pass

        form_view = self.env.ref('juragan_product.sale_cancel_form')
        if self.mp_shopee_id:
            mp_type = 'shp'
        elif self.mp_tokopedia_id:
            mp_type = 'tp'

        return {
            'name': 'Cancel Order',
            'view_mode': 'form',
            'res_model': 'sale.cancel.wizard',
            'view_id' : form_view.id,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context' : {'mp_type':mp_type},
        }

    def action_orders_accept(self):
        server = self.get_webhook_server()
        res = server.action_orders('accept_order', [self.izi_id])
        pass

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
    

    def action_orders_confirm_shipping(self):
        server = self.get_webhook_server()
        res = server.action_orders('confirm_shipping', [self.izi_id])
        pass

    def action_orders_request_pickup(self):
        server = self.get_webhook_server()
        if self.mp_shopee_id:
            res = server.get_pickup_info([self.izi_id])
            pickup_obj = self.env['sale.order.pickup.info']
            shop_obj = self.env['mp.shop.address']
            if res['code'] == 200:
                form_view = self.env.ref('juragan_product.request_pickup_form')
                server.get_records('mp.shop.address')
                data = res['data']

                orders = self.env['sale.order'].search([])
                order_by_izi_id = {}
                for order in orders:
                    order_by_izi_id[order.izi_id] = order

                shops = shop_obj.search([])
                shop_by_izi_id = {}
                for shop in shops:
                    shop_by_izi_id[shop.izi_id] = shop

                pickup_data = pickup_obj.sudo().search([('order_id','=',self.id),'|',('active','=',True),('active','=',False)])
                if pickup_data:
                    for pickup in pickup_obj:
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
        if self.mp_tokopedia_id:        
            res = server.action_orders('request_pickup', [self.izi_id])

    def action_orders_get_label(self):
        server = self.get_webhook_server()
        if self.mp_tokopedia_id:
            res = server.action_orders('get_label', [self.izi_id])
            return {
                'name': 'Label',
                'res_model': 'ir.actions.act_url',
                'type': 'ir.actions.act_url',
                'target': 'self',
                'url': res['data']['url'],
            }
        if self.mp_shopee_id:
            if not self.mp_awb_number:
                raise UserError('AWB number is not exist..')
            elif self.mp_awb_url:
                raise UserError('Label is exist..')
            else:
                res = server.action_orders('get_label', [self.izi_id])
                if res['code'] == 200:
                    server.get_records('sale.order')
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'reload',
                    }
                else:
                    raise UserError('Get Label Failed..')
    
class WebhookServer(models.Model):
    _inherit = 'webhook.server'
    
    mp_tokopedia_ids = fields.One2many('mp.tokopedia', 'server_id', 'Tokopedia Account')
    mp_shopee_ids = fields.One2many('mp.shopee', 'server_id', 'Shopee Account')

    #
    # API Get Specific
    #
    def action_orders(self, action_code, order_ids=[], cancel_reason_id=False,picking_time_id=False,address_id=False,refresh=False):
        if not self.session_id:
            self.retry_login(3)
        body = {
            'request_by': 'odoo',
            'action_code': action_code,
            'order_ids': order_ids,
        }
        if action_code == 'reject_order':
            body.update({
                'cancel_reason_id': cancel_reason_id
            })
        elif action_code == 'request_pickup':
            body.update({
                'picking_time_id': picking_time_id,
                'address_id' : address_id
            })
        r = requests.post(self.name + '/ui/v2/orders/action/', json=body, headers={
            'X-Openerp-Session-Id': self.session_id,
        })
        res = json.loads(r.text) if r.status_code == 200 else {}
        if res:
            res = res['result']
            if refresh:
                self.sync_order()
        return res
    
    def get_pickup_info(self, order_ids=[]):
        if not self.session_id:
            self.retry_login(3)
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

    def name_get(self):
        res=[]
        date_dict = {
            'Monday':'Senin',
            'Tuesday':'Selasa',
            'Wednesday': 'Rabu',
            'Thursday': 'Kamis',
            'Friday': 'Jum\'at',
            'Saturday': 'Sabtu',
            'Sunday': 'Minggu'
        }
        for rec in self:
            day = date_dict[rec.start_datetime.strftime('%A')]
            time = rec.start_datetime.strftime('%d-%m-%y, %H:%M') + '-' + rec.end_datetime.strftime('%H:%M')
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
        ('7','Buyer’s request')
    ])

    mp_type = fields.Selection([
        ('shp','Shopee'),
        ('tp','Tokopedia'), 
        ('lz','Lazada'), 
    ])

    reason_status = fields.Char(store=True)
    order_ids = fields.One2many(comodel_name='sale.order', inverse_name='cancel_reason_id', string='Order')
    
    izi_id = fields.Integer('Izi ID')

    # def name_get(self):
    #     result = []
    #     mp_type = self._context.get('mp_type','')
    #     reasons = self.search([('mp_type','=',mp_type)])
    #     if reasons:
    #         for reason in reasons:
    #             result.append((reason.id,reason.reason_status))
    #     return result