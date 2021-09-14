# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import json
from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class MarketplaceToken(models.Model):
    _inherit = 'mp.token'

    tp_token_type = fields.Char(string="Tokopedia Token Type", readonly=True)

    @api.model
    def tokopedia_create_token(self, mp_account, raw_token):
        mp_token_obj = self.env['mp.token']

        expired_date = datetime.now() + relativedelta(seconds=raw_token.get('expires_in'))
        values = {
            'name': raw_token.get('access_token'),
            'expired_date': fields.Datetime.to_string(expired_date),
            'mp_account_id': mp_account.id,
            'tp_token_type': raw_token.get('token_type'),
            'raw': json.dumps(raw_token, indent=4)
        }
        mp_token_obj.create(values)
