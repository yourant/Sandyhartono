# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
from odoo import api, fields, models


class MpShopeeLogToken(models.Model):
    _name = 'mp.shopee.log.token'
    _inherit = 'mp.base'
    _description = 'Shopee Log Token'
    _rec_name = 'log_text'
    _order = 'id desc'

    status = fields.Selection([
        ('fail', 'Fail'),
        ('success', 'Success'), ],
        string='Status', default='fail')
    json_request = fields.Text(string='JSON Request')
    json_response = fields.Text(string='JSON Response')
    log_text = fields.Text(string='Log')
    log_create_datetime = fields.Datetime(string='Log Datetime', default=fields.Datetime.now())
    mp_account_id = fields.Many2one(comodel_name='mp.account', string='Marketplace Account')
    mp_token_id = fields.Many2one(comodel_name='mp.token', string='Marketplace Token')

    @api.model
    def create_log_token(self, mp_account, raw_token, request_json, status, mp_token=False):
        mp_shopee_log_token_obj = self.env['mp.shopee.log.token']

        values = {
            'log_text': self.format_raw_data(raw_token),
            'json_request': request_json,
            'mp_account_id': mp_account.id,
            'json_response': self.format_raw_data(raw_token),
            'status': status,
        }
        if mp_token:
            values.update({
                'mp_token_id': mp_token.id
            })
        mp_shopee_log_token_obj.create(values)
