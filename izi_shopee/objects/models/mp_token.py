# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
from datetime import datetime, timedelta
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
        x_minutes = 180
        now_utc = datetime.utcnow()
        time_diff = now_utc.replace(tzinfo=None) - datetime.strptime(self.create_date, "%Y-%m-%d %H:%M:%S")
        if (time_diff.days > 0 or time_diff.seconds > (x_minutes * 60)) and self.refresh_token and self.sp_shop_id:
            try:
                self.mp_account_id.shopee_renew_token()
            except Exception as e:
                time_now = str((datetime.now() + timedelta(hours=7)).strftime("%Y-%m-%d %H:%M:%S"))
                auth_message = "%s from: %s" % (str(e.args[0]), time_now)
                self.mp_account_id.write({'state': 'authenticating', 'auth_message': auth_message})
                return self.mp_account_id.mp_token_ids.sorted('expired_date', reverse=True)[0]
        return self
