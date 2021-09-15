from odoo import fields, models, api, _
from odoo.exceptions import UserError

class RequestPickupWizard(models.TransientModel):

    _name = 'request.pickup.wizard'

    pickup_id = fields.Many2one('sale.order.pickup.info', string='Waktu Pickup')
    address_id = fields.Many2one('mp.shop.address', string='Alamat Pickup')
    
    def request_pickup(self):
        sale = self.env['sale.order'].browse(self._context.get('active_ids', []))
        server = sale.get_webhook_server()
        pickup_obj = self.env['sale.order.pickup.info'].browse(self.pickup_id.id)
        if pickup_obj:
            pickup_obj.write({
                'active':True,
                'address_id': self.address_id.id
            })
            picking_time_id = pickup_obj.name
            address_id = pickup_obj.address_id.address_id
       
        res = server.action_orders('request_pickup', [sale.izi_id],picking_time_id=picking_time_id,address_id=address_id)
        
        if res['code'] == 200:
            data = res['data']
         
            domain_url = "[('id', '=', %i)]" % int(sale.izi_id)
            server.get_records('sale.order',domain_url=domain_url)

            # sale.action_validate_picking()
            if sale.state == 'draft':
                sale.action_confirm()
        
            # return {
            #     'name': 'Label',
            #     'res_model': 'ir.actions.act_url',
            #     'type': 'ir.actions.act_url',
            #     'target': 'new',
            #     'url': sale.mp_awb_url+'&session_id='+server.session_id,
            # }
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }
           
        else:
            raise UserError('Request Pickup Failed..')
        
            
  
