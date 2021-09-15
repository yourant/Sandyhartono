# -*- coding: utf-8 -*-

from Cryptodome.Cipher import PKCS1_OAEP
from Cryptodome.PublicKey import RSA as rsa_key
from base64 import urlsafe_b64encode
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
import requests
import json
 
_logger = logging.getLogger(__name__)

mp_detail_args = {
    'mp.tokopedia': {
        'args': [['|', ['active', '=', True], ['active', '=', False]]],
        'kwargs': {
            'fields': [
                'shop_url',
                'fs_id',
                'client_id',
                'client_secret',
                'active',
                'cron_active',
                'load_shop',
                'load_etalase',
                'load_category',
                'force_import',
                'update_master',
                'check_order_detail',
                'log_error',
                'sync_stock_active',
                'sync_stock_history_active',
                'sync_stock_sale_active',
            ],
        },
    },
    'mp.shopee': {
        'args': [['|', ['active', '=', True], ['active', '=', False]]],
        'kwargs': {
            'fields': [
                'shop_name',
                'username',
                'active',
                'cron_active',
                'load_shop',
                'load_shop_category',
                'load_item_category',
                'load_item',
                'load_discount',
                'load_order',
                'load_logistic',
                'load_return',
                'load_payment',
                'force_import',
                'update_master',
                'check_order_detail',
                'log_error',
                'sync_stock_active',
                'sync_stock_history_active',
                'sync_stock_sale_active',
            ],
        },
    },
    'mp.lazada': {
        'args': [['|', ['active', '=', True], ['active', '=', False]]],
        'kwargs': {
            'fields': [
                'country',
                'email',
                'password',
                'code',
                'active',
                'cron_active',
                'load_brand',
                'load_category',
                'load_product',
                'load_order',
                'sync_stock_active',
                'sync_stock_history_active',
                'sync_stock_sale_active',
            ],
        },
    },
}


def mp_translate_dict(*args, **kwargs):
    output = {}
    for k, v in args[0].items():
        if k == 'id':
            output['izi_id'] = v
        else:
            output[k] = v
    return output


class BigInteger(fields.Integer):
    column_type = ('int8', 'int8')


class WebhookServer(models.Model):
    _inherit = 'webhook.server'
    
    mp_tokopedia_ids = fields.One2many('mp.tokopedia', 'server_id', 'Tokopedia Account', domain=['|', ('active', '=', True), ('active', '=', False)])
    mp_shopee_ids = fields.One2many('mp.shopee', 'server_id', 'Shopee Account', domain=['|', ('active', '=', True), ('active', '=', False)])
    mp_lazada_ids = fields.One2many('mp.lazada', 'server_id', 'Lazada Account', domain=['|', ('active', '=', True), ('active', '=', False)])
    
    public_key = fields.Text('Public Key', compute='get_rsa_token', store=True)
    rsa_token = fields.Text('RSA Token', compute='get_rsa_token', store=True)
    
    def remote(self):
        self.ensure_one()
        if not self.rsa_token:
            self.get_rsa_token()
        if self.rsa_token:
            return {                   
                'name': 'Go to website',
                'res_model': 'ir.actions.act_url',
                'type': 'ir.actions.act_url',
                'target': 'new',
                'url': '%s/web/login/rsa/%s' % (self.name, self.rsa_token),
            }
        else:
            raise UserError('Auth error.')
    
    @api.depends('name', 'username', 'password')
    def get_rsa_token(self):
        for rec in self.filtered(lambda r:r.name and r.username and r.password):
            r = requests.get('%s/rsa/pem/public' % (rec.name))
            if r.status_code == 200:
                message = '%s:%s' % (rec.username, rec.password)
                rsa_public_key = rsa_key.import_key(r.text)
                cipher = PKCS1_OAEP.new(key=rsa_public_key)
                rec.public_key = r.text
                rec.rsa_token = urlsafe_b64encode(cipher.encrypt(message.encode())).decode('utf-8')
                
    def get_accounts(self):
        valid_models = ['mp.tokopedia', 'mp.shopee', 'mp.lazada']
        models = self.env.context.get('models', valid_models)
        filter_models = [model for model in filter(lambda r:r in valid_models, models)]
        for rec in self:
            if not rec.rsa_token:
                rec.get_rsa_token()
            if rec.rsa_token:
                rec.get_warehouses()
                rec.get_records('res.partner', loop_commit=False)
                if 'mp.tokopedia' in filter_models:
                    self.env.user.notify_info('Getting Tokopedia Data...')
                    rec.get_records('mp.tokopedia', domain_code='all_active', loop_commit=False)
                if 'mp.shopee' in filter_models:
                    self.env.user.notify_info('Getting Shopee Data...')
                    rec.get_records('mp.shopee', domain_code='all_active', loop_commit=False)
                if 'mp.lazada' in filter_models:
                    self.env.user.notify_info('Getting Lazada Data...')
                    rec.get_records('mp.lazada', domain_code='all_active', loop_commit=False)
                for filter_model in filter_models:
                    server_izi_ids = []
                    r = requests.patch('%s/rsa/api/v1/%s/search_read' % (rec.name, filter_model), headers={
                        'Authorization': 'Bearer %s' % (rec.rsa_token)
                    }, json=mp_detail_args.get(filter_model))
                    responses = r.json()
                    _logger.warn(json.dumps(responses, indent=2))
                    if responses and (responses.get('status') == 200):
                        for response in responses.get('response', []):
                            server_izi_ids.append(response['id'])
                            response = mp_translate_dict(response)
                            response['state'] = 'done'
                            _logger.warn(json.dumps(response, indent=2))
                            mp_id = self.env[filter_model].search([
                                ('server_id', '=', rec.id),
                                ('izi_id', '=', response['izi_id']),
                                '|',
                                ('active', '=', True),
                                ('active', '=', False),
                            ])
                            mp_id.write(response)
                        mp_ids = None
                    if filter_model == 'mp.tokopedia':
                        mp_ids = rec.mp_tokopedia_ids
                    if filter_model == 'mp.shopee':
                        mp_ids = rec.mp_shopee_ids
                    if filter_model == 'mp.lazada':
                        mp_ids = rec.mp_lazada_ids
                    if mp_ids:
                        mp_ids.filtered(lambda r:r.izi_id not in server_izi_ids).write({
                            'izi_id': False,
                            'state': 'draft'
                        })
        self.env.user.notify_info('Done Getting Marketplace Account.')
        
    def create_account(self):
        self.ensure_one()
        return {
            'name': _('Create Account'),
            'context': {
                **self.env.context,
                **{
                    'default_server_id': self.id,
                }
            },
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': self.env.context.get('model'),
            'res_id': None,
            'type': 'ir.actions.act_window',
            'target': 'new'
        }


class RemoteMP(models.AbstractModel):
    _name = 'remote.mp'
    _description = 'Remote Marketplace'
    
    server_id = fields.Many2one('webhook.server')
    izi_id = fields.Integer()
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Uploaded'),
    ], default='draft')
    
    active = fields.Boolean('Active')
    cron_active = fields.Boolean('Active Scheduler')
    
    sync_stock_active = fields.Boolean('Realtime Stock Update', default=True)
    sync_stock_history_active = fields.Boolean('Get Stock History', default=False)
    sync_stock_sale_active = fields.Boolean('Stock Update From Sales Order', default=False)
    
    def open_form(self):
        self.ensure_one()
        return {
            'name': _('Create Account'),
            'context': self.env.context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': self._name,
            'res_id': self.id,
            'type': 'ir.actions.act_window',
            'target': 'new'
        }
      
    def write(self, vals):
        if not vals.get('state'):
            vals['state'] = 'draft'
        return super(RemoteMP, self).write(vals)
      
    def view_detail(self):
        self.ensure_one()
        if not self.server_id.rsa_token:
            self.server_id.get_rsa_token()
        if self.server_id.rsa_token:
            r = requests.patch('%s/rsa/api/v1/ir.actions.act_window/search_read' % (self.server_id.name), headers={
                'Authorization': 'Bearer %s' % (self.server_id.rsa_token)
            }, json={
                'args': [[['res_model', '=', self._name]]],
                'kwargs': {
                    'fields': ['id'],
                    'limit': 1,
                }
            })
            data = r.json()
            if data and (data.get('status') == 200):
                for datum in data.get('response', []):
                    return {                   
                        'name': 'Go to website',
                        'res_model': 'ir.actions.act_url',
                        'type': 'ir.actions.act_url',
                        'target': 'new',
                        'url': '%s/web/login/rsa/%s?redirect=/web#id=%s&view_type=form&model=%s&action=%s' % (
                            self.server_id.name,
                            self.server_id.rsa_token,
                            self.izi_id,
                            self._name,
                            datum.get('id')
                        ),
                    }
        else:
            raise UserError('Auth error.')
        
    def upload(self):
        self.ensure_one()
        if not self.server_id.rsa_token:
            self.server_id.get_rsa_token()
        if self.server_id.rsa_token:
            local_data = self.read(mp_detail_args[self._name]['kwargs']['fields'], load=False)[0]
            del local_data['id']
            _logger.warn(json.dumps(local_data, indent=2))
            if self.izi_id:
                r = requests.patch('%s/rsa/api/v1/%s/write/%s' % (self.server_id.name, self._name, self.izi_id), headers={
                    'Authorization': 'Bearer %s' % (self.server_id.rsa_token)
                }, json={
                    'args': [local_data],
                })
                data = r.json()
                _logger.warn(json.dumps(data, indent=2))
                if data and (data.get('status') == 200):
                    self.write({'state': 'done'})
                    self.server_id.with_context({'models': [self._name]}).get_accounts()
                    self.env.user.notify_info('Upload success.', sticky=True)
                else:
                    self.env.user.notify_info('Upload fail.', sticky=True)
            else:
                r = requests.patch('%s/rsa/api/v1/%s/create' % (self.server_id.name, self._name), headers={
                    'Authorization': 'Bearer %s' % (self.server_id.rsa_token)
                }, json={
                    'args': [local_data],
                })
                data = r.json()
                _logger.warn(json.dumps(data, indent=2))
                if data and (data.get('status') == 200):
                    self.write({
                        'state': 'done',
                        'izi_id': int(data.get('response', '').lstrip('%s(' % (self._name)).rstrip(',)')),
                    })
                    self.server_id.with_context({'models': [self._name]}).get_accounts()
                    self.env.user.notify_info('Upload success.', sticky=True)
                else:
                    self.env.user.notify_info('Upload fail.', sticky=True)
        else:
            raise UserError('Auth error.')
        
    def remote_action(self):
        # _logger.warn(json.dumps(self.env.context, indent=2))
        action_name = self.env.context.get('action')
        action_args = self.env.context.get('args', [])
        action_kwargs = self.env.context.get('kwargs', {})
        if action_name:
            self.ensure_one()
            if not self.server_id.rsa_token:
                self.server_id.get_rsa_token()
            if self.server_id.rsa_token:
                r = requests.patch('%s/rsa/api/v1/%s/%s/%s' % (self.server_id.name, self._name, action_name, self.izi_id), headers={
                    'Authorization': 'Bearer %s' % (self.server_id.rsa_token)
                }, json={
                    'args': action_args,
                    'kwargs': action_kwargs,
                })
                responses = r.json()
                _logger.warn(json.dumps(responses, indent=2))
                if responses and (responses.get('status') == 200):
                    self.server_id.with_context({'models': [self._name]}).get_accounts()
                    self.env.user.notify_info('Remote Action executed successfully.', sticky=True)
                    return responses.get('response')
                else:
                    self.env.user.notify_info('Remote Action failed.', sticky=True)
            else:
                raise UserError('Auth error.')
        else:
            raise UserError('Action Undefined.')
        
    def import_stock_mp(self):
        self.ensure_one()
        if not self.server_id.rsa_token:
            self.server_id.get_rsa_token()
        if self.server_id.rsa_token:
            channel = self._name.split('.')[1]
            r = requests.patch('%s/rsa/api/v1/%s/import_stock_mp/%s' % (self.server_id.name, self._name, self.izi_id), headers={
                'Authorization': 'Bearer %s' % (self.server_id.rsa_token)
            }, json={
                'args': [channel, self.izi_id],
            })
            responses = r.json()
            _logger.warn(json.dumps(responses, indent=2))
            if responses and (responses.get('status') == 200):
                self.env.user.notify_info('Remote Action executed successfully.', sticky=True)
                return responses.get('response')
            else:
                self.env.user.notify_info('Remote Action failed.', sticky=True)
        else:
            raise UserError('Auth error.')

                
class MPTokopedia(models.Model):
    _name = 'mp.tokopedia'
    _inherit = ['mp.tokopedia', 'remote.mp']
    
    shop_url = fields.Text('Shop URL')
    fs_id = BigInteger('App ID')
    client_id = fields.Char('Client ID')
    client_secret = fields.Char()
    
    load_shop = fields.Boolean(default=True)
    load_category = fields.Boolean(default=True)
    load_etalase = fields.Boolean(default=True)
    force_import = fields.Boolean('Force Import')
    update_master = fields.Boolean('Update Master')
    check_order_detail = fields.Boolean('Check Order Detail', default=True)
    log_error = fields.Boolean('Log Error', default=False)

    
class MPShopee(models.Model):
    _name = 'mp.shopee'
    _inherit = ['mp.shopee', 'remote.mp']
    
    shop_name = fields.Char()
    username = fields.Char()
    
    load_shop = fields.Boolean(default=True)
    load_shop_category = fields.Boolean(default=True)
    load_item_category = fields.Boolean(default=True)
    load_item = fields.Boolean(default=True)
    load_discount = fields.Boolean(default=True)
    load_order = fields.Boolean(default=True)
    load_logistic = fields.Boolean(default=True)
    load_return = fields.Boolean(default=True)
    load_payment = fields.Boolean(default=True)
    force_import = fields.Boolean('Force Import')
    update_master = fields.Boolean('Update Master')
    check_order_detail = fields.Boolean('Check Order Detail', default=True)
    log_error = fields.Boolean('Log Error', default=False)

    
class MPLazada(models.Model):
    _name = 'mp.lazada'
    _inherit = ['mp.lazada', 'remote.mp']
    
    country = fields.Selection([
        ('id', 'Indonesia'),
    ], default='id')
    email = fields.Char()
    password = fields.Char()
    code = fields.Char()
    
    load_brand = fields.Boolean(default=True)
    load_category = fields.Boolean(default=True)
    load_product = fields.Boolean(default=True)
    load_order = fields.Boolean(default=True)
