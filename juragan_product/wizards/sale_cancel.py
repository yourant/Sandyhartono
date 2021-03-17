from odoo import fields, models, api, _
from odoo.exceptions import UserError

class SaleCancelWizard(models.TransientModel):

    _name = 'sale.cancel.wizard'

    cancel_reason_id = fields.Many2one('sale.order.cancel.reason', 'Cancel Order Reason')

    def cancel_process(self):
        sale = self.env['sale.order'].browse(self._context.get('active_ids', []))
        cancel_reason = self.cancel_reason_id
        pickup_obj = self.env['sale.order.pickup.info']
        sale.write({
            'cancel_reason_id': cancel_reason.id
        })
        server = sale.get_webhook_server()
        res = server.action_orders('reject_order', [sale.izi_id], cancel_reason_id=cancel_reason.izi_id)
        if res['code'] == 200:
            # server.get_records('sale.order')
            data = res['data']
            sale.sudo().write(data)

            if sale.pickup_ids:
                pickup_data = pickup_obj.sudo().search([('order_id','=',sale.id),'|',('active','=',True),('active','=',False)])
                if pickup_data:
                    for pickup in data:
                        pickup.sudo().unlink()
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }
        else:
            raise UserError('Cancel Order Failed..')


class AcceptSaleCancelWizard(models.TransientModel):

    _name = 'accept.sale.cancel.wizard'


    def accept_cancel_process(self):
        sale = self.env['sale.order'].browse(self._context.get('active_ids', []))
        pickup_obj = self.env['sale.order.pickup.info']
        server = sale.get_webhook_server()
        res = server.action_orders('accept_cancel', [sale.izi_id])
        if res['code'] == 200:
            server.get_records('sale.order')
            # data = res['data']
            # sale.write(data)
            # self.mp_cancel_reason = data['mp_cancel_reason']
            # self.sp_cancel_by = data['sp_cancel_by']
            # self.sp_order_status = data['sp_order_status']

            if sale.pickup_ids:
                pickup_data = pickup_obj.sudo().search([('order_id','=',sale.id),'|',('active','=',True),('active','=',False)])
                if pickup_data:
                    for pickup in pickup_data:
                        pickup.sudo().unlink()
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }
        else:
            raise UserError('Accept Cancel Order Failed..')

class RejectSaleCancelWizard(models.TransientModel):

    _name = 'reject.sale.cancel.wizard'


    def reject_cancel_process(self):
        sale = self.env['sale.order'].browse(self._context.get('active_ids', []))
        pickup_obj = self.env['sale.order.pickup.info']
        server = sale.get_webhook_server()
        res = server.action_orders('reject_cancel', [sale.izi_id])
        if res['code'] == 200:
            data = res['data'] 
            sale.write(data)
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }
        else:
            raise UserError('Accept Cancel Order Failed..')
        
            
  
