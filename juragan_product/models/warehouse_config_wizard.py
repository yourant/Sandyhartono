from datetime import datetime, date
from odoo import fields, models, api, _
import requests


class WebhookServer(models.Model):
    _inherit = 'webhook.server'
    
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

class WarehouseConfigLine(models.TransientModel):
    _name = 'warehouse.config.line'

    name = fields.Char('Name')
    res_model = fields.Char('Model')
    res_id = fields.Integer('ID')
    wh_config = fields.Selection([
        ('main','Main Warehouse'),
        ('shop','Shop Warehouse'),], string='Take Stock From')
    config_id = fields.Many2one('warehouse.config.wizard', 'Config')
    sync_stock_active = fields.Boolean('Realtime Stock Update')

class WarehouseConfigWizard(models.TransientModel):
    _name = 'warehouse.config.wizard'

    name = fields.Char('Name')
    line_ids = fields.One2many('warehouse.config.line', 'config_id', 'Accounts')

    @api.model
    def default_get(self, fields):
        res = super(WarehouseConfigWizard, self).default_get(fields)
        line_values = []
        for tp in self.env['mp.tokopedia'].sudo().search([]):
            line_values.append((0, 0, {
                'name': tp.shop_name,
                'res_model': 'mp.tokopedia',
                'res_id': tp.izi_id,
                'wh_config': tp.wh_config,
                'sync_stock_active': tp.sync_stock_active,
            }))
        for tp in self.env['mp.shopee'].sudo().search([]):
            line_values.append((0, 0, {
                'name': tp.shop_name,
                'res_model': 'mp.shopee',
                'res_id': tp.izi_id,
                'wh_config': tp.wh_config,
                'sync_stock_active': tp.sync_stock_active,
            }))
        for tp in self.env['mp.lazada'].sudo().search([]):
            line_values.append((0, 0, {
                'name': tp.seller_name_company,
                'res_model': 'mp.lazada',
                'res_id': tp.izi_id,
                'wh_config': tp.wh_config,
                'sync_stock_active': tp.sync_stock_active,
            }))
        res['line_ids'] = line_values
        return res

    def process_wizard(self):
        server = self.env['webhook.server'].search([], limit=1)
        if not server:
            raise UserError('There is no webhook server.')
        if server:
            config_lines = []
            for line in self.line_ids:
                config_lines.append({
                    'res_model': line.res_model,
                    'res_id': line.res_id,
                    'wh_config': line.wh_config,
                    'sync_stock_active': line.sync_stock_active,
                })
            body = {
                'config_lines': config_lines,
            }
            url = server.name + '/api/ui/stock/config/wh'
            res = requests.post(url, json=body, headers={
                'X-Openerp-Session-Id': server.session_id,
            })
            res = res.json()
            if (res and res.get('code') == 200):
                server.get_accounts()
