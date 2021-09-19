# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class MarketplaceToken(models.Model):
    _inherit = 'mp.token'

    sp_shop_id = fields.Char(String="Shopee Shop ID", readonly=True)

    @api.model
    def shopee_create_token(self, mp_account, raw_token):
        mp_token_obj = self.env['mp.token']

        expired_date = datetime.now() + relativedelta(seconds=raw_token.get('expire_in'))
        values = {
            'name': raw_token.get('access_token'),
            'expired_date': fields.Datetime.to_string(expired_date),
            'mp_account_id': mp_account.id,
            'refresh_token': raw_token.get('refresh_token'),
            'sp_shop_id': raw_token.get('shop_id'),
            'raw': self.format_raw_data(raw_token)
        }
        mp_token_obj.create(values)

    @api.multi
    def shopee_validate_current_token(self):
        self.ensure_one()
        if self.state != 'valid':
            try:
                self.mp_account_id.shopee_renew_token()
            except Exception as e:
                self.mp_account_id.write({'state': 'authenticating', 'sp_reason': str(e.args[0])})
            return self.mp_account_id.mp_token_ids.sorted('expired_date', reverse=True)[0]
        return self
