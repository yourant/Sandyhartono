from odoo import fields, models, api, _
from odoo.exceptions import UserError

class SaleCancelWizard(models.TransientModel):

    _name = 'sale.cancel.wizard'

    cancel_reason_id = fields.Many2one('sale.order.cancel.reason', 'Cancel Order Reason')
    cancel_reason_name = fields.Selection(related="cancel_reason_id.name")
    cancel_reason_mp_type = fields.Selection(related="cancel_reason_id.mp_type")
    shop_close_end_date = fields.Date(string="Shop Close End Date", required=False)
    shop_close_note = fields.Char(string="Shop Close Note", required=False)

    def cancel_process(self):
        if 'order_ids' in self._context:
            sales = self.env['sale.order'].browse(self._context.get('order_ids', []))
        else:
            sales = self.env['sale.order'].browse(self._context.get('active_ids', []))

        if not sales:
            raise UserError("There's no order selected!")

        cancel_reason = self.cancel_reason_id
        pickup_obj = self.env['sale.order.pickup.info']
        sales.write({
            'cancel_reason_id': cancel_reason.id
        })
        server = sales[0].get_webhook_server()
        responses = []
        for sale in sales:
            kwargs = {
                'cancel_reason_id': cancel_reason.izi_id,
            }
            if self.shop_close_end_date and self.shop_close_note:
                kwargs.update({
                    'shop_close_end_date': self.shop_close_end_date.strftime('%d/%m/%Y'),
                    'shop_close_note': self.shop_close_note
                })
            res = server.action_orders('reject_order', [sale.izi_id], **kwargs)
            responses.append((res, sale))

        cancel_failed = all([response[0]['code'] != 200 for response in responses])
        cancel_success = all([response[0]['code'] == 200 for response in responses])
        if cancel_failed:
            cancel_status_msg = ''
            for response in responses:
                res = response[0]
                sale = response[1]
                data = res['data']
                cancel_status_msg += '\n- {}: {}'.format(sale.name, data.get('error', 'Failed'))
            raise UserError("Some order(s) is failed to cancel: {}".format(cancel_status_msg))
        elif cancel_success:
            for response in responses:
                res = response[0]
                sale = response[1]
                data = res['data']
                # sale.sudo().write(data)
                domain_url = "[('id', '=', %i)]" % int(sale.izi_id)
                server.get_records('sale.order',domain_url=domain_url)

                if sale.pickup_ids: 
                    pickup_data = pickup_obj.sudo().search(
                        [('order_id', '=', sale.id), '|', ('active', '=', True), ('active', '=', False)])
                    if pickup_data:
                        for pickup in pickup_data:
                            pickup.sudo().unlink()
                return {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                }
        else:
            cancel_status_msg = ''
            for response in responses:
                res = response[0]
                sale = response[1]
                data = res['data']
                if res['code'] == 200:
                    sale.sudo().write(data)

                    if sale.pickup_ids:
                        pickup_data = pickup_obj.sudo().search(
                            [('order_id', '=', sale.id), '|', ('active', '=', True), ('active', '=', False)])
                        if pickup_data:
                            for pickup in data:
                                pickup.sudo().unlink()
                    cancel_status_msg += '\n- {}: {}'.format(sale.name, 'Success')
                else:
                    cancel_status_msg += '\n- {}: {}'.format(sale.name, data.get('error_descrip', 'Failed'))

            raise UserError("Some order(s) is failed to cancel: {}".format(cancel_status_msg))


class AcceptSaleCancelWizard(models.TransientModel):

    _name = 'accept.sale.cancel.wizard'


    def accept_cancel_process(self):
        sale = self.env['sale.order'].browse(self._context.get('active_ids', []))
        pickup_obj = self.env['sale.order.pickup.info']
        server = sale.get_webhook_server()
        res = server.action_orders('accept_cancel', [sale.izi_id])
        if res['code'] == 200:
            domain_url = "[('id', '=', %i)]" % int(sale.izi_id)
            server.get_records('sale.order',domain_url=domain_url)
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
            domain_url = "[('id', '=', %i)]" % int(sale.izi_id)
            server.get_records('sale.order',domain_url=domain_url)
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }
        else:
            raise UserError('Accept Cancel Order Failed..')
        
            
  
