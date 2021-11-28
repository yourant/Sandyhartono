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

    MP_WEBHOOK_STATES = [
        ('registered', 'Registered'),
        ('no_register', 'No Register')
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
    partner_id = fields.Many2one('res.partner', string='Default Partner Marketplace')
    warehouse_id = fields.Many2one('stock.warehouse', string='Default Warehouse Marketplace')
    insurance_product_id = fields.Many2one(comodel_name="product.product", string="Default Insurance Product",
                                           default=lambda self: self._get_default_insurance_product_id())
    team_id = fields.Many2one(comodel_name='crm.team', string='Default Sales Channel')
    user_id = fields.Many2one(comodel_name='res.users', string='Default Salesperson')
    global_discount_product_id = fields.Many2one(comodel_name="product.product",
                                                 string="Default Global Discount Product",
                                                 default=lambda self: self._get_default_global_discount_product_id())
    adjustment_product_id = fields.Many2one(comodel_name="product.product",
                                            string="Default Adjustment Product",
                                            default=lambda self: self._get_default_adjustment_product_id())

    get_unpaid_orders = fields.Boolean(string="Get Unpaid Order", default=False,
                                       help="Get order with status UNPAID from Shopee")
    get_cancelled_orders = fields.Boolean(string="Get Cancelled Order", default=False,
                                          help="Get order CANCELLED from marketplace if the order is not exists before")

    debug_force_update = fields.Boolean(string="Force Update", default=False,
                                        help="Force update even there is no changes from marketplace")
    debug_force_update_raw = fields.Boolean(string="Force Update Raw Only", default=False,
                                            help="Force update raw field only")
    debug_store_product_img = fields.Boolean(string="Store Product Image",
                                             default=False, help="Store product image as binary into the database")
    debug_product_limit = fields.Integer(string="Product Import Limit", required=True, default=0,
                                         help="Maximum number to import product, set 0 for unlimited!")
    debug_order_limit = fields.Integer(string="Order Import Limit", required=True, default=0,
                                       help="Maximum number to import order, set 0 for unlimited!")
    debug_skip_error = fields.Boolean(string="Skip Error", default=False,
                                      help="Skip error when processing records from marketplace")

    cron_id = fields.Many2one(comodel_name='ir.cron', string='Order Scheduler')
    cron_user_id = fields.Many2one('res.users', string='Scheduler User', related='cron_id.user_id')
    cron_interval_number = fields.Integer(string="Sync Every", default=1,
                                          help="Repeat every x.", related='cron_id.interval_number')
    cron_nextcall = fields.Datetime(string='Next Execution Date', related='cron_id.nextcall')
    cron_interval_type = fields.Selection([('minutes', 'Minutes'),
                                           ('hours', 'Hours'),
                                           ('days', 'Days'),
                                           ('weeks', 'Weeks'),
                                           ('months', 'Months')], string='Interval Unit',
                                          default='minutes', related='cron_id.interval_type')
    cron_active = fields.Boolean(string='Active Scheduler', related='cron_id.active')
    mp_log_error_ids = fields.One2many(comodel_name='mp.log.error',
                                       inverse_name='mp_account_id', string='Marketplace Log Error')
    mp_webhook_state = fields.Selection(string="Webhook Status", selection=MP_WEBHOOK_STATES,
                                        default="no_register", readonly=True)

    @api.model
    def create(self, vals):
        res = super(MarketplaceAccount, self).create(vals)
        if not res.cron_id:
            new_cron = self.env['ir.cron'].sudo().create({
                'name': '%s Scheduler %s' % (str(res.marketplace.capitalize()), str(res.id)),
                'model_id': self.env.ref('%s.model_%s' % (self._module, '_'.join(self._name.split('.')))).id,
                'state': 'code',
                'code': "model.%s_get_orders(id=%d,time_range='last_hour',params='by_date_range');" %
                ((res.marketplace), (res.id)),
                'interval_number': 5,
                'interval_type': 'minutes',
                'numbercall': -1,
                'active': False,
            })
            res.cron_id = new_cron.id
        return res

    @api.onchange('marketplace')
    def onchange_marketplace(self):
        self.partner_id = getattr(
            self.env.ref('izi_{mp}.res_partner_{mp}'.format(**{'mp': self.marketplace}), raise_if_not_found=False),
            'id', False)

    @api.multi
    def _compute_mp_token(self):
        for mp_account in self:
            if mp_account.mp_token_ids:
                mp_token = mp_account.mp_token_ids.sorted('expired_date', reverse=True)[0]
                mp_token = mp_token.validate_current_token()
                mp_account.mp_token_id = mp_token.id
            else:
                mp_account.mp_token_id = False

    @api.model
    def _get_default_insurance_product_id(self):
        mp_insurance_product_tmpl = self.env.ref('izi_marketplace.product_tmpl_mp_insurance', raise_if_not_found=False)
        if mp_insurance_product_tmpl:
            return mp_insurance_product_tmpl.product_variant_id.id
        return False

    @api.model
    def _get_default_global_discount_product_id(self):
        mp_global_discount_product_tmpl = self.env.ref('izi_marketplace.product_tmpl_mp_global_discount',
                                                       raise_if_not_found=False)
        if mp_global_discount_product_tmpl:
            return mp_global_discount_product_tmpl.product_variant_id.id
        return False

    @api.model
    def _get_default_adjustment_product_id(self):
        mp_adjustment_product_tmpl = self.env.ref('izi_marketplace.product_tmpl_mp_adjustment',
                                                  raise_if_not_found=False)
        if mp_adjustment_product_tmpl:
            return mp_adjustment_product_tmpl.product_variant_id.id
        return False

    @api.multi
    def generate_context(self):
        self.ensure_one()
        context = self._context.copy()
        context.update({
            'mp_account_id': self.id,
            'force_update': self.debug_force_update,
            'force_update_raw': self.debug_force_update_raw,
            'store_product_img': self.debug_store_product_img,
            'product_limit': self.debug_product_limit,
            'order_limit': self.debug_order_limit,
            'skip_error': self.debug_skip_error,
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
            return getattr(self, '%s_get_dependencies' % self.marketplace)()

    @api.multi
    def action_get_products(self):
        self.ensure_one()
        if hasattr(self, '%s_get_products' % self.marketplace):
            return getattr(self, '%s_get_products' % self.marketplace)()

    @api.multi
    def register_webhooks(self):
        self.ensure_one()
        if hasattr(self, '%s_register_webhooks' % self.marketplace):
            return getattr(self, '%s_register_webhooks' % self.marketplace)()

    @api.multi
    def unregister_webhooks(self):
        self.ensure_one()
        if hasattr(self, '%s_unregister_webhooks' % self.marketplace):
            return getattr(self, '%s_unregister_webhooks' % self.marketplace)()

    @api.multi
    def action_map_product(self):
        product_map_obj = self.env['mp.map.product']

        self.ensure_one()

        product_map = product_map_obj.search([
            ('marketplace', '=', self.marketplace),
            ('mp_account_id', '=', self.id),
        ])

        if not product_map.exists():
            product_map = product_map_obj.create({
                'name': 'Product Mapping - %s' % self.name,
                'marketplace': self.marketplace,
                'mp_account_id': self.id,
            })

        action = self.env.ref('izi_marketplace.action_window_mp_map_product').read()[0]
        action.update({
            'res_id': product_map.id,
            'views': [(self.env.ref('izi_marketplace.form_mp_map_product').id, 'form')],
        })
        return action

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
