# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
from base64 import b64decode

from odoo import api, fields, models


class WizUploadPublicKey(models.TransientModel):
    _name = 'wiz.upload_public_key'
    _description = 'Tokopedia Upload Public Key'

    mp_account_id = fields.Many2one(comodel_name="mp.account", string="Marketplace Account", required=True)
    tp_private_key_file = fields.Binary(string="Secret Key File", required=True)
    tp_public_key_file = fields.Binary(string="Public Key File", required=True)

    def do_upload_key_pair(self):
        _notify = self.env['mp.base']._notify

        self.mp_account_id.tp_private_key_file = b64decode(self.with_context({'bin_size': False}).tp_private_key_file)
        self.mp_account_id.tp_public_key_file = b64decode(self.with_context({'bin_size': False}).tp_public_key_file)
        _notify('info', "New RSA key uploaded successfully!")
        return {
            'type': 'ir.actions.client',
            'tag': 'close_notifications',
            'params': {
                'force_show_number': 1
            }
        }
