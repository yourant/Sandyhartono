# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class MarketplaceMapProduct(models.Model):
    _name = 'mp.map.product'
    _description = 'Marketplace Map Product'
    _sql_constraints = [
        ('unique_mp_account_id', 'unique(mp_account_id)', 'You can only make one mapping per marketplace account!')
    ]

    MAP_STATES = [
        ('draft', 'Draft'),
        ('mapping', 'Mapping')
    ]

    READONLY_STATES = {
        'mapping': [('readonly', True)],
    }

    name = fields.Char(string="Name", required=True, states=READONLY_STATES)
    mp_account_id = fields.Many2one(comodel_name="mp.account", string="Marketplace Account", required=True)
    marketplace = fields.Selection(string="Marketplace", required=True,
                                   selection=lambda env: env['mp.account']._fields.get('marketplace').selection,
                                   related="mp_account_id.marketplace", store=True)
    company_id = fields.Many2one(comodel_name="res.company", string="Company", index=1, readonly=True,
                                 related="mp_account_id.company_id", store=True)
    field_mapping_ids = fields.One2many(comodel_name="mp.map.product.field", inverse_name="map_id",
                                        string="Field Mapping", required=False,
                                        default=lambda self: self._get_default_field_mapping_ids())
    map_line_ids = fields.One2many(comodel_name="mp.map.product.line", inverse_name="map_id", string="Mapping Line")
    state = fields.Selection(string="Status", selection=MAP_STATES, required=True, default="draft")

    # noinspection PyUnresolvedReferences
    @api.model
    def _get_default_field_mapping_ids(self):
        field_mapping_data = [
            (0, 0, {
                'sequence': 1,
                'product_model_id': self.env.ref('product.model_product_product').id,
                'mp_product_model_id': self.env.ref('izi_marketplace.model_mp_product').id,
                'mp_product_variant_model_id': self.env.ref('izi_marketplace.model_mp_product_variant').id,
                'product_field_id': self.env.ref('product.field_product_product_default_code').id,
                'mp_product_field_id': self.env.ref('izi_marketplace.field_mp_product_default_code').id,
                'mp_product_variant_field_id': self.env.ref(
                    'izi_marketplace.field_mp_product_variant_default_code').id,
            })
        ]
        return field_mapping_data

    @api.onchange('mp_account_id')
    def onchange_mp_account_id(self):
        if self.mp_account_id and not self.name:
            self.name = 'Product Mapping - %s' % self.mp_account_id.name

    @api.multi
    def get_product(self, record):
        product_obj = self.env['product.product']

        self.ensure_one()

        field_mappings = self.field_mapping_ids
        lookup_field = None

        if record._name == 'mp.product':
            lookup_field = 'mp_product_field_id'
        elif record._name == 'mp.product.variant':
            lookup_field = 'mp_product_variant_field_id'

        for field_mapping in field_mappings:
            domain = []
            key = field_mapping.product_field_id.name
            value = getattr(record, getattr(field_mapping, lookup_field).name)
            if not value:
                domain.append(('id', '=', 0))
            domain.append((key, '=', value))
            product = product_obj.search(domain)
            if product.exists() and len(product) == 1:
                return product
            continue

        return product_obj

    @api.multi
    def get_existing_map_line(self, record):
        self.ensure_one()

        map_lines = self.map_line_ids
        lookup_field = None

        if record._name == 'mp.product':
            lookup_field = 'mp_product_id'
        elif record._name == 'mp.product.variant':
            lookup_field = 'mp_product_variant_id'

        return map_lines.filtered(
            lambda ml: getattr(ml, lookup_field).id == record.id and ml.marketplace == record.marketplace)

    @api.multi
    def generate_map_line_data(self, record):
        self.ensure_one()

        product = self.get_product(record)
        map_line_data = {
            'map_id': self.id,
            'mp_account_id': self.mp_account_id.id,
            'marketplace': self.mp_account_id.marketplace,
            'state': 'mapped' if product.exists() else 'unmapped',
            'product_id': product.id,
            'mp_product_id': False,
            'mp_product_variant_id': False
        }

        if record._name == 'mp.product':
            map_line_data.update({
                'mp_product_id': record.id,
                'mp_product_variant_id': False
            })
        elif record._name == 'mp.product.variant':
            map_line_data.update({
                'mp_product_id': False,
                'mp_product_variant_id': record.id
            })

        return map_line_data

    @api.multi
    def do_mapping(self, records):
        for record in records:
            map_line = self.get_existing_map_line(record)
            map_line_data = self.generate_map_line_data(record)
            if map_line:
                if not map_line.product_id:
                    map_line.write(map_line_data)
            else:
                map_line.create(map_line_data)

    @api.multi
    def action_start(self):
        for mapping in self:
            mapping.action_generate()
            mapping.write({'state': 'mapping'})

    @api.multi
    def action_generate(self):
        self.ensure_one()

        mp_products = self.mp_account_id.mp_product_ids.filtered(lambda mpp: not mpp.mp_product_variant_ids)
        mp_product_variants = self.mp_account_id.mp_product_ids.mapped('mp_product_variant_ids')
        self.do_mapping(mp_products)
        self.do_mapping(mp_product_variants)

    @api.multi
    def action_edit(self):
        self.ensure_one()

        action = self.env.ref('izi_marketplace.action_window_mp_map_product_line').read()[0]
        action['domain'] = [('map_id', '=', self.id)]
        return action

    @api.multi
    def action_view_unmapped_line(self):
        self.ensure_one()

        action = self.env.ref('izi_marketplace.action_window_mp_map_product_line').read()[0]
        action['domain'] = [('map_id', '=', self.id), ('state', '=', 'unmapped')]
        return action

    @api.multi
    def action_view_mapped_line(self):
        self.ensure_one()

        action = self.env.ref('izi_marketplace.action_window_mp_map_product_line').read()[0]
        action['domain'] = [('map_id', '=', self.id), ('state', '=', 'mapped')]
        return action


class MarketplaceMapProductField(models.Model):
    _name = 'mp.map.product.field'
    _description = 'Marketplace Map Product'

    map_id = fields.Many2one(comodel_name="mp.map.product", string="Product Mapping", required=True, ondelete="cascade")
    sequence = fields.Integer(string="Sequence", required=True, default=1)
    product_model_id = fields.Many2one(comodel_name="ir.model", string="Product Model", required=False,
                                       default=lambda self: self.env.ref('product.model_product_product').id)
    mp_product_model_id = fields.Many2one(comodel_name="ir.model", string="MP Product Model", required=False,
                                          default=lambda self: self.env.ref('izi_marketplace.model_mp_product').id)
    mp_product_variant_model_id = fields.Many2one(comodel_name="ir.model", string="Product Model", required=False,
                                                  default=lambda self: self.env.ref(
                                                      'izi_marketplace.model_mp_product_variant').id)
    product_field_id = fields.Many2one(comodel_name="ir.model.fields", string="Product Field", required=True)
    mp_product_field_id = fields.Many2one(comodel_name="ir.model.fields", string="MP Product Field")
    mp_product_variant_field_id = fields.Many2one(comodel_name="ir.model.fields", string="MP Product Variant Field")


class MarketplaceMapProductLine(models.Model):
    _name = 'mp.map.product.line'
    _description = 'Marketplace Map Product Line'
    _order = 'state,name'

    MAP_LINE_STATES = [
        ('unmapped', 'Unmapped'),
        ('mapped', 'Mapped'),
    ]

    map_id = fields.Many2one(comodel_name="mp.map.product", string="Product Mapping", required=True)
    name = fields.Char(string="Name", compute="_compute_line", store=True)
    default_code = fields.Char(string="Internal Reference", compute="_compute_line", store=True)
    mp_account_id = fields.Many2one(comodel_name="mp.account", string="Marketplace Account", required=True)
    marketplace = fields.Selection(string="Marketplace", required=True,
                                   selection=lambda env: env['mp.account']._fields.get('marketplace').selection,
                                   related="mp_account_id.marketplace", store=True)
    company_id = fields.Many2one(comodel_name="res.company", string="Company", index=1, readonly=True,
                                 related="mp_account_id.company_id", store=True)
    product_id = fields.Many2one(comodel_name="product.product", string="Product", required=False)
    mp_product_id = fields.Many2one(comodel_name="mp.product", string="MP Product", required=False)
    mp_product_variant_id = fields.Many2one(comodel_name="mp.product.variant", string="MP Product Variant",
                                            required=False)
    state = fields.Selection(string="Status", selection=MAP_LINE_STATES, required=True, default="unmapped",
                             readonly=True)

    @api.multi
    @api.depends('mp_product_id', 'mp_product_variant_id')
    def _compute_line(self):
        for line in self:
            if line.mp_product_id:
                line.name = line.mp_product_id.display_name
                line.default_code = line.mp_product_id.default_code
            elif line.mp_product_variant_id:
                line.name = line.mp_product_variant_id.display_name
                line.default_code = line.mp_product_variant_id.default_code

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            # map_lines = self.map_id.map_line_ids
            # existing_map_line = map_lines.filtered(
            #     lambda ml: ml.product_id.id == self.product_id.id and ml.mp_account_id.id == self.mp_account_id.id) \
            #     .filtered(lambda ml: ml.id != self.id)
            # if existing_map_line.exists():
            #     raise ValidationError('You can only make one mapping per marketplace account!')
            self.state = 'mapped'
