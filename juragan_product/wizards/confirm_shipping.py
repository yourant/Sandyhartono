from odoo import fields, models, api, _
from odoo.exceptions import UserError


class ConfirmShippingWizard(models.TransientModel):
    _name = 'confirm.shipping.wizard'
    mp_awb_number = fields.Char('AWB Numbers')

    def do_confirm_shipping(self):
        order_id = self.env['sale.order'].browse(self._context.get('order_id', []))
        server = order_id.get_webhook_server()
        res = server.action_orders('confirm_shipping', [order_id.izi_id], mp_awb_number=self.mp_awb_number)
        if res and res.get('code') == 200:
            pass
        else:
            if 'data' in res:
                if 'error' in res.get('data'):
                    raise UserError(res.get('data').get('error'))
            raise UserError('Failed to Confirm Shipping')