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
        ('authenticating', 'Authenticating'),
        ('authenticated', 'Authenticated'),
    ]

    READONLY_STATES = {
        'authenticated': [('readonly', True)],
        'authenticating': [('readonly', True)],
    }

    name = fields.Char(string="Name", required=True)
    marketplace = fields.Selection(string="Marketplace", selection=[], required=True, states=READONLY_STATES)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(comodel_name="res.company", string="Company", index=1, readonly=False, required=True,
                                 default=lambda self: self.env['res.company']._company_default_get(),
                                 states=READONLY_STATES)
    currency_id = fields.Many2one(comodel_name="res.currency", string="Currency", required=True,
                                  default=lambda s: s.env.ref('base.IDR'))
    state = fields.Selection(string="Status", selection=MP_ACCOUNT_STATES, required=True, default="new",
                             states=READONLY_STATES)
    mp_token_ids = fields.One2many(comodel_name="mp.token", inverse_name="mp_account_id", string="Marketplace Tokens",
                                   required=False, states=READONLY_STATES)
    mp_token_id = fields.Many2one(comodel_name="mp.token", string="Marketplace Token", compute="_compute_mp_token")
    access_token = fields.Char(string="Access Token", related="mp_token_id.name", readonly=True)
    access_token_expired_date = fields.Datetime(string="Expired Date", related="mp_token_id.expired_date",
                                                readonly=True)
    auth_message = fields.Char(string="Authentication Message", readonly=True)
    mp_product_ids = fields.One2many(comodel_name="mp.product", inverse_name="mp_account_id",
                                     string="Marketplace Product(s)")
    partner_id = fields.Many2one('res.partner', string='Partner Marketplace')
    debug_force_update = fields.Boolean(string="Force Update", default=False,
                                        help="Force update even there is no changes from marketplace")
    debug_force_update_raw = fields.Boolean(string="Force Update Raw Only", default=False,
                                            help="Force update raw field only")
    debug_store_product_img = fields.Boolean(string="Store Product Image",
                                             default=False, help="Store product image as binary into the database")

    @api.multi
    def _compute_mp_token(self):
        for mp_account in self:
            if mp_account.mp_token_ids:
                mp_token = mp_account.mp_token_ids.sorted('expired_date', reverse=True)[0]
                mp_token = mp_token.validate_current_token()
                mp_account.mp_token_id = mp_token.id
            else:
                mp_account.mp_token_id = False

    @api.multi
    def generate_context(self):
        self.ensure_one()
        context = self._context.copy()
        context.update({
            'mp_account_id': self.id,
            'force_update': self.debug_force_update,
            'force_update_raw': self.debug_force_update_raw,
            'debug_store_product_img': self.debug_store_product_img
        })
        return context

    @api.multi
    def action_reauth(self):
        self.ensure_one()
        self.write({'state': 'authenticating'})

    @api.multi
    def action_authenticate(self):
        self.ensure_one()
        if hasattr(self, '%s_authenticate' % self.marketplace):
            return getattr(self, '%s_authenticate' % self.marketplace)()

    @api.multi
    def action_get_dependencies(self):
        self.ensure_one()
        if hasattr(self, '%s_get_dependencies' % self.marketplace):
            getattr(self, '%s_get_dependencies' % self.marketplace)()

    @api.multi
    def action_get_products(self):
        self.ensure_one()
        if hasattr(self, '%s_get_products' % self.marketplace):
            getattr(self, '%s_get_products' % self.marketplace)()

    @api.multi
    def action_get_orders(self):
        self.ensure_one()
        form_view = self.env.ref('izi_marketplace.mp_get_order_form')
        return {
            'name': 'Get Orders',
            'view_mode': 'form',
            'res_model': 'wiz.mp.get.order',
            'view_id': form_view.id,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {
                'marketplace': self.marketplace
            },
        }

    @api.multi
    def action_view_mp_product(self):
        self.ensure_one()
        action = self.env.ref('izi_marketplace.action_window_mp_product_view_per_marketplace').read()[0]
        action.update({
            'domain': [('mp_account_id', '=', self.id)],
            'context': {
                'default_marketplace': self.marketplace,
                'default_mp_account_id': self.id
            }
        })
        return action
