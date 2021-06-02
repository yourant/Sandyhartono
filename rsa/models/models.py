# -*- coding: utf-8 -*-

from odoo import models, fields, api
from Cryptodome.Cipher import PKCS1_OAEP
from Cryptodome.PublicKey import RSA as rsa_key
from base64 import urlsafe_b64encode, urlsafe_b64decode


class RSA(models.AbstractModel):
    _name = 'rsa'
    _description = 'RSA'
    
    @api.model
    def generate(self):
        private_key = rsa_key.generate(4096)
        public_key = private_key.publickey()
        private_pem = private_key.export_key().decode()
        public_pem = public_key.export_key().decode()
        self.env['ir.config_parameter'].set_param('rsa.private.pem', private_pem)
        self.env['ir.config_parameter'].set_param('rsa.public.pem', public_pem)
        
    @api.model
    def get_private_pem(self):
        return self.env['ir.config_parameter'].sudo().get_param('rsa.private.pem')
        
    @api.model
    def get_public_pem(self):
        return self.env['ir.config_parameter'].sudo().get_param('rsa.public.pem')
    
    @api.model
    def encrypt(self, message, **kw):
        rsa_public_key = rsa_key.import_key(kw.get('public_pem', self.get_public_pem()))
        cipher = PKCS1_OAEP.new(key=rsa_public_key)
        return urlsafe_b64encode(cipher.encrypt(message.encode())).decode('utf-8')
        
    @api.model
    def decrypt(self, message, **kw):
        rsa_private_key = rsa_key.import_key(kw.get('private_pem', self.get_private_pem()))
        cipher = PKCS1_OAEP.new(key=rsa_private_key)
        return cipher.decrypt(urlsafe_b64decode(message.encode())).decode('utf-8')
    
