from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import requests

class StockMove(models.Model):
    _inherit = 'stock.move'

    distribution_id = fields.Many2one('Distribution')

class StockDistribution(models.Model):
    _name = 'stock.distribution'

    name = fields.Char('Name', required=True)
    move_ids = fields.One2many('stock.move', 'distribution_id', 'Stock Moves')
    distribution_date = fields.Date('Distribution Date')
    location_id = fields.Many2one('stock.location', 'Source Location', required=True)
    location_dest_id = fields.Many2one('stock.location', 'Destination Location', required=True)
    line_ids = fields.One2many('stock.distribution.line', 'distribution_id', 'Distribution Details')
    distribution_percentage = fields.Float('Distribution Percentage (%)')
    mp_tokopedia_id = fields.Many2one('mp.tokopedia', 'Tokopedia Account')
    mp_shopee_id = fields.Many2one('mp.shopee', 'Shopee Account')
    mp_lazada_id = fields.Many2one('mp.lazada', 'Lazada Account')
    mp_blibli_id = fields.Many2one('mp.blibli', 'Blibli Account')
    mp_account_type = fields.Selection([
        ('tokopedia', 'Tokopedia'),
        ('shopee', 'Shopee'),
        ('lazada', 'Lazada'),
        ('blibli', 'Blibli')], string='Related Marketplace', required=True)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('transferred', 'Transferred'),
        ('returned', 'Returned'),], default='draft')
    # Multi Locationnya Nanti Aja
    
    @api.onchange('mp_tokopedia_id')
    def _set_mp_tokopedia_location(self):
        for rec in self:
            rec.location_id = rec.mp_tokopedia_id.wh_main_id.lot_stock_id.id
            rec.location_dest_id = rec.mp_tokopedia_id.wh_shop_id.lot_stock_id.id
    
    @api.onchange('mp_shopee_id')
    def _set_mp_shopee_location(self):
        for rec in self:
            rec.location_id = rec.mp_shopee_id.wh_main_id.lot_stock_id.id
            rec.location_dest_id = rec.mp_shopee_id.wh_shop_id.lot_stock_id.id
    
    @api.onchange('mp_lazada_id')
    def _set_mp_lazada_location(self):
        for rec in self:
            rec.location_id = rec.mp_lazada_id.wh_main_id.lot_stock_id.id
            rec.location_dest_id = rec.mp_lazada_id.wh_shop_id.lot_stock_id.id

    @api.onchange('mp_blibli_id')
    def _set_mp_blibli_location(self):
        for rec in self:
            rec.location_id = rec.mp_blibli_id.wh_main_id.lot_stock_id.id
            rec.location_dest_id = rec.mp_blibli_id.wh_shop_id.lot_stock_id.id

    def open_warehouse_config_wizard(self):
        view = self.env.ref('juragan_product.warehouse_config_wizard')
        return {
            'name': 'Warehouse Config',
            'view_mode': 'form',
            'res_model': 'warehouse.config.wizard',
            'view_id' : view.id,
            'views': [(view.id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context' : {},
        }

    def distribute_by_percentage(self):
        if not self.distribution_percentage:
            raise UserError('Please input Distribution Percentage (%) to do this action!')
        elif self.distribution_percentage < 0 or self.distribution_percentage > 100 :
            raise UserError('Please input Distribution Percentage (%) between 0 and 100!')
        
        for line in self.line_ids:
            if line.qty_available:
                line.qty_transfer = int(line.qty_available * self.distribution_percentage / 100)


    def check_stock(self):
        # if self.state != 'draft':
        #     raise UserError('The document state must be in draft.')

        qty_by_product = {}
        quants = self.env['stock.quant'].sudo().search([('location_id','=',self.location_id.id), ('product_id.izi_id','!=',False)])
        for qt in quants:
            if qt.product_id.id not in qty_by_product:
                qty_by_product[qt.product_id.id] = {
                    'qty_available': 0,
                    'qty_reserved': 0,
                    'qty_draft': 0,
                    'qty_total': 0,
                }
            qty_by_product[qt.product_id.id]['qty_available'] += qt.quantity - qt.reserved_quantity

        qty_dest_by_product = {}
        if self.location_dest_id:
            quants = self.env['stock.quant'].sudo().search([('location_id','=',self.location_dest_id.id)])
            for qt in quants:
                if qt.product_id.id not in qty_dest_by_product:
                    qty_dest_by_product[qt.product_id.id] = {
                        'qty_available': 0,
                        'qty_reserved': 0,
                        'qty_draft': 0,
                        'qty_total': 0,
                    }
                qty_dest_by_product[qt.product_id.id]['qty_available'] += qt.quantity - qt.reserved_quantity

        DistributionLine = self.env['stock.distribution.line'].sudo()
        dist_line_by_product_id = {}
        dist_lines = DistributionLine.search([('distribution_id', '=', self.id)])
        for line in dist_lines:
            dist_line_by_product_id[line.product_id.id] = line
        
        for prd_id in qty_by_product:
            if not prd_id in dist_line_by_product_id:
                values = {
                    'distribution_id': self.id,
                    'product_id': prd_id,
                    'qty_available': qty_by_product[prd_id]['qty_available'],
                    'qty_reserved': 0,
                    'qty_draft': 0,
                    'qty_total': 0,
                    'qty_transfer': 0,
                }
                if prd_id in qty_dest_by_product:
                    values['qty_available_dest'] = qty_dest_by_product[prd_id]['qty_available']
                DistributionLine.create(values)
            else:
                values = {
                    'qty_available': qty_by_product[prd_id]['qty_available'],
                }
                if prd_id in qty_dest_by_product:
                    values['qty_available_dest'] = qty_dest_by_product[prd_id]['qty_available']
                dist_line_by_product_id[prd_id].write(values)

    def transfer_stock(self):
        if not self.state == 'draft':
            raise UserError('State must be in draft.')
        if not self.location_dest_id:
            raise UserError('Location Destination is not set.')
        
        StockMove = self.env['stock.move'].sudo()
        process_moves = []
        for line in self.line_ids:
            if line.qty_transfer > 0:
                sm = StockMove.create({
                    'name': self.name + '/TRF/' + str(line.product_id.id),
                    'product_id': line.product_id.id,
                    'product_uom': line.product_id.uom_id.id,
                    'product_uom_qty': line.qty_transfer,
                    'quantity_done': line.qty_transfer,
                    'location_id': self.location_id.id,
                    'location_dest_id': self.location_dest_id.id,
                    'distribution_id': self.id,
                })
                sm._action_done()
                process_moves.append(sm)
        self.state = 'transferred'
        self.check_stock()
        
        # Sync Stock to IZI
        # Get Warehouse
        wh = self.env['stock.warehouse'].sudo().search([('lot_stock_id', '=', self.location_id.id)])
        wh_dest = self.env['stock.warehouse'].sudo().search([('lot_stock_id', '=', self.location_dest_id.id)])
        
        if (wh and wh.izi_id) or (wh_dest and wh_dest.izi_id):
            # Prepare move_lines
            move_lines = []
            for ml in process_moves:
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
            if server:
                body = {
                    'name': self.name + '/TRF',
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

    def return_stock(self):
        if not self.state == 'transferred':
            raise UserError('State must be in transferred.')
        if not self.location_dest_id:
            raise UserError('Location Destination is not set.')

        StockMove = self.env['stock.move'].sudo()
        process_moves = []
        for line in self.line_ids:
            if line.qty_transfer > 0:
                qty_to_return = line.qty_transfer
                if qty_to_return > line.qty_available_dest:
                    qty_to_return = line.qty_available_dest
                sm = StockMove.create({
                    'name': self.name + '/RTN/' + str(line.product_id.id),
                    'product_id': line.product_id.id,
                    'product_uom': line.product_id.uom_id.id,
                    'product_uom_qty': qty_to_return,
                    'quantity_done': qty_to_return,
                    'location_id': self.location_dest_id.id,
                    'location_dest_id': self.location_id.id,
                    'distribution_id': self.id,
                })
                sm._action_done()
                process_moves.append(sm)
        self.state = 'returned'
        self.check_stock()
        
        # Sync Stock to IZI
        # Get Warehouse
        wh = self.env['stock.warehouse'].sudo().search([('lot_stock_id', '=', self.location_dest_id.id)])
        wh_dest = self.env['stock.warehouse'].sudo().search([('lot_stock_id', '=', self.location_id.id)])
        
        if (wh and wh.izi_id) or (wh_dest and wh_dest.izi_id):
            # Prepare move_lines
            move_lines = []
            for ml in process_moves:
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
            if server:
                body = {
                    'name': self.name + '/TRF',
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

class StockDistributionLine(models.Model):
    _name = 'stock.distribution.line'

    distribution_id = fields.Many2one('stock.distribution', 'Distribution')
    product_id = fields.Many2one('product.product', 'Product')
    qty_available = fields.Float('Qty Available')
    qty_reserved = fields.Float('Qty Reserved')
    qty_draft = fields.Float('Qty Draft')
    qty_total = fields.Float('Qty Total')
    qty_available_dest = fields.Float('Qty in Destination')
    qty_transfer = fields.Float('Qty to Transfer')