# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class MarketplaceAccount(models.Model):
    _name = 'mp.account'
    _description = 'Marketplace Account'

    @api.multi
    def _check_required_if_marketplace(self):
        """ If the field has 'required_if_marketplace="<marketplace>"' attribute, then it
        required if record.marketplace is <marketplace>. """
        empty_field = []
        for mp_account in self:
            for k, f in mp_account._fields.items():
                if getattr(f, 'required_if_marketplace', None) == mp_account.marketplace and not mp_account[k]:
                    empty_field.append(self.env['ir.model.fields'].search(
                        [('name', '=', k), ('model', '=', mp_account._name)]).field_description)
        if empty_field:
            raise ValidationError(', '.join(empty_field))
        return True

    _constraints = [
        (_check_required_if_marketplace, 'Required fields not filled', []),
    ]

    MP_ACCOUNT_STATES = [
        ('new', 'New'),
        ('authenticated', 'Authenticated'),
    ]

    name = fields.Char(string="Name", required=True)
    marketplace = fields.Selection(string="Marketplace", selection=[], required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(comodel_name="res.company", string="Company", index=1, readonly=False, required=True,
                                 default=lambda self: self.env['res.company']._company_default_get())
    state = fields.Selection(string="Status", selection=MP_ACCOUNT_STATES, required=True, default="new")
    mp_token_ids = fields.One2many(comodel_name="mp.token", inverse_name="mp_account_id", string="Marketplace Tokens",
                                   required=False)
    mp_token_id = fields.Many2one(comodel_name="mp.token", string="Marketplace Token", compute="_compute_mp_token")
    access_token = fields.Char(string="Access Token", related="mp_token_id.name", readonly=True)
    access_token_expired_date = fields.Datetime(string="Expired Date", related="mp_token_id.expired_date",
                                                readonly=True)

    @api.multi
    def _compute_mp_token(self):
        for mp_account in self:
            if mp_account.mp_token_ids:
                mp_token = mp_account.mp_token_ids.sorted('expired_date', reverse=True)[0]
                mp_account.mp_token_id = mp_token.id
            else:
                mp_account.mp_token_id = False

    @api.multi
    def authenticate(self):
        self.ensure_one()
        if hasattr(self, '%s_authenticate' % self.marketplace):
            getattr(self, '%s_authenticate' % self.marketplace)()
