# # -*- coding: utf-8 -*-
# from Cryptodome.Cipher import PKCS1_OAEP
# from Cryptodome.PublicKey import RSA as rsa_key
# from base64 import urlsafe_b64encode
# from odoo import models, fields, api, _
# from odoo.exceptions import UserError
# import logging
# import requests
#  
# _logger = logging.getLogger(__name__)
#  
#  
# class BigInteger(fields.Integer):
#     column_type = ('int8', 'int8')
#  
#  
# class RemoteMP(models.AbstractModel):
#     _name = 'remote.mp'
#     _description = 'Remote Marketplace'
#      
#     webhook_id = fields.Many2one('webhook.server', string='Configuration')
#     mp_id = BigInteger('IZI ID')
#     state = fields.Selection([
#         ('draft', 'Draft'),
#         ('done', 'Uploaded'),
#     ], default='draft', required=True)
#      
#     def write(self, vals):
#         if not vals.get('state'):
#             vals['state'] = 'draft'
#         return super(RemoteMP, self).write(vals)
#      
#     def view_detail(self):
#         self.ensure_one()
#         if not self.webhook_id.rsa_token:
#             self.webhook_id.get_rsa_token()
#         if self.webhook_id.rsa_token:
#             if self._name == 'remote.mp.tokopedia':
#                 _logger.warn('Go To Tokopedia')
#                 r = requests.patch('%s/rsa/api/v1/ir.actions.act_window/search_read' % (self.webhook_id.name), headers={
#                     'Authorization': 'Bearer %s' % (self.webhook_id.rsa_token)
#                 }, json={
#                     'args': [[['res_model', '=', 'mp.tokopedia']]],
#                     'kwargs': {
#                         'fields': ['id'],
#                         'limit': 1,
#                     }
#                 })
#                 data = r.json()
#                 if data and (data.get('status') == 200):
#                     for datum in data.get('response', []):
#                         return {                   
#                             'name': 'Go to website',
#                             'res_model': 'ir.actions.act_url',
#                             'type': 'ir.actions.act_url',
#                             'target': 'new',
#                             'url': '%s/web/login/rsa/%s?redirect=/web#id=%s&view_type=form&model=mp.tokopedia&action=%s' % (self.webhook_id.name, self.webhook_id.rsa_token, self.mp_id, datum.get('id')),
#                         }
#             if self._name == 'remote.mp.shopee':
#                 _logger.warn('Go To Shopee')
#                 r = requests.patch('%s/rsa/api/v1/ir.actions.act_window/search_read' % (self.webhook_id.name), headers={
#                     'Authorization': 'Bearer %s' % (self.webhook_id.rsa_token)
#                 }, json={
#                     'args': [[['res_model', '=', 'mp.shopee']]],
#                     'kwargs': {
#                         'fields': ['id'],
#                         'limit': 1,
#                     }
#                 })
#                 data = r.json()
#                 if data and (data.get('status') == 200):
#                     for datum in data.get('response', []):
#                         return {                   
#                             'name': 'Go to website',
#                             'res_model': 'ir.actions.act_url',
#                             'type': 'ir.actions.act_url',
#                             'target': 'new',
#                             'url': '%s/web/login/rsa/%s?redirect=/web#id=%s&view_type=form&model=mp.shopee&action=%s' % (self.webhook_id.name, self.webhook_id.rsa_token, self.mp_id, datum.get('id')),
#                         }
#             if self._name == 'remote.mp.lazada':
#                 _logger.warn('Go To Lazada')
#                 r = requests.patch('%s/rsa/api/v1/ir.actions.act_window/search_read' % (self.webhook_id.name), headers={
#                     'Authorization': 'Bearer %s' % (self.webhook_id.rsa_token)
#                 }, json={
#                     'args': [[['res_model', '=', 'mp.lazada']]],
#                     'kwargs': {
#                         'fields': ['id'],
#                         'limit': 1,
#                     }
#                 })
#                 data = r.json()
#                 if data and (data.get('status') == 200):
#                     for datum in data.get('response', []):
#                         return {                   
#                             'name': 'Go to website',
#                             'res_model': 'ir.actions.act_url',
#                             'type': 'ir.actions.act_url',
#                             'target': 'new',
#                             'url': '%s/web/login/rsa/%s?redirect=/web#id=%s&view_type=form&model=mp.lazada&action=%s' % (self.webhook_id.name, self.webhook_id.rsa_token, self.mp_id, datum.get('id')),
#                         }
#         else:
#             raise UserError('Auth error.')
#      
#     def upload(self):
#         for rec in self:
#             if not rec.webhook_id.rsa_token:
#                 rec.webhook_id.get_rsa_token()
#             if rec.webhook_id.rsa_token:
#                 if rec._name == 'remote.mp.tokopedia':
#                     _logger.warn('Upload Tokopedia Data')
#                     if rec.mp_id:
#                         r = requests.patch('%s/rsa/api/v1/mp.tokopedia/write/%s' % (rec.webhook_id.name, rec.mp_id), headers={
#                             'Authorization': 'Bearer %s' % (rec.webhook_id.rsa_token)
#                         }, json={
#                             'args': [{
#                                 'shop_url': rec.shop_url,
#                                 'fs_id': rec.fs_id,
#                                 'client_id': rec.client_id,
#                                 'client_secret': rec.client_secret,
#                             }]
#                         })
#                         data = r.json()
#                         if data and (data.get('status') == 200):
#                             rec.state = 'done'
#                     else:
#                         r = requests.patch('%s/rsa/api/v1/mp.tokopedia/create' % (rec.webhook_id.name), headers={
#                             'Authorization': 'Bearer %s' % (rec.webhook_id.rsa_token)
#                         }, json={
#                             'args': [{
#                                 'shop_url': rec.shop_url,
#                                 'fs_id': rec.fs_id,
#                                 'client_id': rec.client_id,
#                                 'client_secret': rec.client_secret,
#                             }]
#                         })
#                         data = r.json()
#                         if data and (data.get('status') == 200):
#                             rec.write({
#                                 'mp_id': int(data.get('response', '').lstrip('mp.tokopedia(').rstrip(',)')),
#                                 'state': 'done',
#                             })
#                 if rec._name == 'remote.mp.shopee':
#                     _logger.warn('Upload Shopee Data')
#                     if rec.mp_id:
#                         r = requests.patch('%s/rsa/api/v1/mp.shopee/write/%s' % (rec.webhook_id.name, rec.mp_id), headers={
#                             'Authorization': 'Bearer %s' % (rec.webhook_id.rsa_token)
#                         }, json={
#                             'args': [{
#                                 'shop_name': rec.shop_name,
#                                 'username': rec.username,
#                             }]
#                         })
#                         data = r.json()
#                         if data and (data.get('status') == 200):
#                             rec.state = 'done'
#                     else:
#                         r = requests.patch('%s/rsa/api/v1/mp.shopee/create' % (rec.webhook_id.name), headers={
#                             'Authorization': 'Bearer %s' % (rec.webhook_id.rsa_token)
#                         }, json={
#                             'args': [{
#                                 'shop_name': rec.shop_name,
#                                 'username': rec.username,
#                             }]
#                         })
#                         data = r.json()
#                         if data and (data.get('status') == 200):
#                             rec.write({
#                                 'mp_id': int(data.get('response', '').lstrip('mp.shopee(').rstrip(',)')),
#                                 'state': 'done',
#                             })
#                 if rec._name == 'remote.mp.lazada':
#                     _logger.warn('Upload Lazada Data')
#                     if rec.mp_id:
#                         r = requests.patch('%s/rsa/api/v1/mp.lazada/write/%s' % (rec.webhook_id.name, rec.mp_id), headers={
#                             'Authorization': 'Bearer %s' % (rec.webhook_id.rsa_token)
#                         }, json={
#                             'args': [{
#                                 'country': rec.country,
#                                 'email': rec.email,
#                             }]
#                         })
#                         data = r.json()
#                         if data and (data.get('status') == 200):
#                             rec.state = 'done'
#                     else:
#                         r = requests.patch('%s/rsa/api/v1/mp.lazada/create' % (rec.webhook_id.name), headers={
#                             'Authorization': 'Bearer %s' % (rec.webhook_id.rsa_token)
#                         }, json={
#                             'args': [{
#                                 'country': rec.country,
#                                 'email': rec.email,
#                             }]
#                         })
#                         data = r.json()
#                         if data and (data.get('status') == 200):
#                             rec.write({
#                                 'mp_id': int(data.get('response', '').lstrip('mp.shopee(').rstrip(',)')),
#                                 'state': 'done',
#                             })
#  
#  
# class RemoteMPTokopedia(models.Model):
#     _name = 'remote.mp.tokopedia'
#     _inherit = 'remote.mp'
#     _description = 'Remote Tokopedia'
#      
#     shop_url = fields.Text('Shop URL', required=True)
#     fs_id = BigInteger('App ID', required=True)
#     client_id = fields.Char('Client ID', required=True)
#     client_secret = fields.Char(required=True)
#      
#      
# class RemoteMPShopee(models.Model):
#     _name = 'remote.mp.shopee'
#     _inherit = 'remote.mp'
#     _description = 'Remote Shopee'
#      
#     shop_name = fields.Char()
#     username = fields.Char(required=True)
#  
#      
# class RemoteMPLazada(models.Model):
#     _name = 'remote.mp.lazada'
#     _inherit = 'remote.mp'
#     _description = 'Remote Lazada'
#      
#     country = fields.Selection([
#         ('id', 'Indonesia'),
#     ], required=True, default='id')
#     email = fields.Char(required=True)
#  
#  
# class WebhookServer(models.Model):
#     _inherit = 'webhook.server'
#      
#     tokopedia_ids = fields.One2many('remote.mp.tokopedia', 'webhook_id', string='Tokopedia')
#     shopee_ids = fields.One2many('remote.mp.shopee', 'webhook_id', string='Shopee')
#     lazada_ids = fields.One2many('remote.mp.lazada', 'webhook_id', string='Lazada')
#      
#     public_key = fields.Text('Public Key', compute='get_rsa_token', store=True)
#     rsa_token = fields.Text('RSA Token', compute='get_rsa_token', store=True)
#      
#     def remote(self):
#         self.ensure_one()
#         if not self.rsa_token:
#             self.get_rsa_token()
#         if self.rsa_token:
#             return {                   
#                 'name': 'Go to website',
#                 'res_model': 'ir.actions.act_url',
#                 'type': 'ir.actions.act_url',
#                 'target': 'new',
#                 'url': '%s/web/login/rsa/%s' % (self.name, self.rsa_token),
#             }
#         else:
#             raise UserError('Auth error.')
#      
#     @api.depends('name', 'username', 'password')
#     def get_rsa_token(self):
#         for rec in self.filtered(lambda r:r.name and r.username and r.password):
#             r = requests.get('%s/rsa/pem/public' % (rec.name))
#             if r.status_code == 200:
#                 message = '%s:%s' % (rec.username, rec.password)
#                 rsa_public_key = rsa_key.import_key(r.text)
#                 cipher = PKCS1_OAEP.new(key=rsa_public_key)
#                 rec.public_key = r.text
#                 rec.rsa_token = urlsafe_b64encode(cipher.encrypt(message.encode())).decode('utf-8')
#                  
#     def get_remote_mp(self):
#         for rec in self:
#             if not rec.rsa_token:
#                 rec.get_rsa_token()
#             if rec.rsa_token:
#                 if self.env.context.get('tokopedia'):
#                     _logger.warn('Get Tokopedia data...')
#                     r = requests.patch('%s/rsa/api/v1/mp.tokopedia/search_read' % (rec.name), headers={
#                         'Authorization': 'Bearer %s' % (rec.rsa_token)
#                     }, json={
#                         'args': [[]],
#                         'kwargs': {
#                             'fields': ['shop_url', 'fs_id', 'client_id', 'client_secret']
#                         }
#                     })
#                     data = r.json()
#                     if data and (data.get('status') == 200):
#                         server_mp_ids = []
#                         exist_mp_ids = rec.tokopedia_ids.mapped('mp_id')
#                         for datum in data.get('response', []):
#                             set_dict = datum.copy()
#                             del set_dict['id']
#                             set_dict['state'] = 'done'
#                             set_dict['mp_id'] = datum.get('id')
#                             server_mp_ids.append(datum.get('id'))
#                             if datum.get('id') in exist_mp_ids:
#                                 rec.tokopedia_ids.filtered(lambda r:r.mp_id == datum.get('id')).write(set_dict)
#                             else:
#                                 rec.write({
#                                     'tokopedia_ids': [(0, 0, set_dict)]
#                                 })
#                         rec.tokopedia_ids.filtered(lambda r:r.mp_id not in server_mp_ids).write({
#                             'mp_id': False,
#                             'state': 'draft'
#                         })
#                 if self.env.context.get('shopee'):
#                     _logger.warn('Get Shopee data...')
#                     r = requests.patch('%s/rsa/api/v1/mp.shopee/search_read' % (rec.name), headers={
#                         'Authorization': 'Bearer %s' % (rec.rsa_token)
#                     }, json={
#                         'args': [[]],
#                         'kwargs': {
#                             'fields': ['shop_name', 'username']
#                         }
#                     })
#                     data = r.json()
#                     if data and (data.get('status') == 200):
#                         server_mp_ids = []
#                         exist_mp_ids = rec.shopee_ids.mapped('mp_id')
#                         for datum in data.get('response', []):
#                             set_dict = datum.copy()
#                             del set_dict['id']
#                             set_dict['state'] = 'done'
#                             set_dict['mp_id'] = datum.get('id')
#                             server_mp_ids.append(datum.get('id'))
#                             if datum.get('id') in exist_mp_ids:
#                                 rec.shopee_ids.filtered(lambda r:r.mp_id == datum.get('id')).write(set_dict)
#                             else:
#                                 rec.write({
#                                     'shopee_ids': [(0, 0, set_dict)]
#                                 })
#                         rec.shopee_ids.filtered(lambda r:r.mp_id not in server_mp_ids).write({
#                             'mp_id': False,
#                             'state': 'draft'
#                         })
#                 if self.env.context.get('lazada'):
#                     _logger.warn('Get Lazada data...')
#                     r = requests.patch('%s/rsa/api/v1/mp.lazada/search_read' % (rec.name), headers={
#                         'Authorization': 'Bearer %s' % (rec.rsa_token)
#                     }, json={
#                         'args': [[]],
#                         'kwargs': {
#                             'fields': ['country', 'email']
#                         }
#                     })
#                     data = r.json()
#                     if data and (data.get('status') == 200):
#                         server_mp_ids = []
#                         exist_mp_ids = rec.lazada_ids.mapped('mp_id')
#                         for datum in data.get('response', []):
#                             set_dict = datum.copy()
#                             del set_dict['id']
#                             set_dict['state'] = 'done'
#                             set_dict['mp_id'] = datum.get('id')
#                             server_mp_ids.append(datum.get('id'))
#                             if datum.get('id') in exist_mp_ids:
#                                 rec.lazada_ids.filtered(lambda r:r.mp_id == datum.get('id')).write(set_dict)
#                             else:
#                                 rec.write({
#                                     'lazada_ids': [(0, 0, set_dict)]
#                                 })
#                         rec.lazada_ids.filtered(lambda r:r.mp_id not in server_mp_ids).write({
#                             'mp_id': False,
#                             'state': 'draft'
#                         })
