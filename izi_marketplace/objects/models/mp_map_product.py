# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import logging
import uuid

from odoo import api, fields, models
from odoo.exceptions import UserError

from odoo.addons.izi_marketplace.objects.utils.tools.csv import clean_csv_value
from odoo.addons.izi_marketplace.objects.utils.tools import StringIteratorIO

_logger = logging.getLogger(__name__)


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
    debug_force_mapping_without_company = fields.Boolean(string="Force Mapping Without Company", default=False,
                                                         help="Force update raw field only")

    # noinspection PyUnresolvedReferences

    @api.model
    def _get_default_field_mapping_ids(self):
        field_mapping_data = [
            (0, 0, {
                'sequence': 1,
                'product_model_id': self.env.ref('product.model_product_product').id,
                'mp_product_model_id': self.env.ref('izi_marketplace.model_mp_product').id,
                'mp_product_variant_model_id': self.env.ref('izi_marketplace.model_mp_product_variant').id,
                'product_field_id': self.env.ref('product.field_product_product__default_code').id,
                'mp_product_field_id': self.env.ref('izi_marketplace.field_mp_product__default_code').id,
                'mp_product_variant_field_id': self.env.ref(
                    'izi_marketplace.field_mp_product_variant__default_code').id,
            }),
            (0, 0, {
                'sequence': 2,
                'product_model_id': self.env.ref('product.model_product_product').id,
                'mp_product_model_id': self.env.ref('izi_marketplace.model_mp_product').id,
                'mp_product_variant_model_id': self.env.ref('izi_marketplace.model_mp_product_variant').id,
                'product_field_id': self.env.ref('product.field_product_product__name').id,
                'mp_product_field_id': self.env.ref('izi_marketplace.field_mp_product__name').id,
                'mp_product_variant_field_id': self.env.ref(
                    'izi_marketplace.field_mp_product_variant__name').id,
            })
        ]
        return field_mapping_data

    @api.onchange('mp_account_id')
    def onchange_mp_account_id(self):
        if self.mp_account_id and not self.name:
            self.name = 'Product Mapping - %s' % self.mp_account_id.name

    # @api.multi
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
            if self.debug_force_mapping_without_company:
                domain.append(('company_id', '=?', self.company_id.id))
            else:
                domain.append(('company_id', '=', self.company_id.id))
            key = field_mapping.product_field_id.name
            value = getattr(record, getattr(field_mapping, lookup_field).name)
            if not value:
                domain.append(('id', '=', 0))
            domain.append((key, '=', value))
            _logger.info("Looking for product using domain: %s" % domain)
            product = product_obj.search(domain)
            if product.exists() and len(product) == 1:
                _logger.info("Product found: %s" % product.display_name)
                return product
            _logger.info("Product not found, continue to the next lookup...")
            continue

        return product_obj

    # @api.multi
    def generate_map_line_data(self, record):
        self.ensure_one()

        product = self.get_product(record)
        map_line_data = {
            'map_id': self.id,
            'mp_account_id': self.mp_account_id.id,
            'marketplace': self.mp_account_id.marketplace,
            'state': 'mapped' if product.exists() else 'unmapped',
            'product_id': product.id or None,
            'mp_product_id': None,
            'mp_product_variant_id': None,
            'generated_by_mapping': True if product.exists() else False
        }
        if record._name == 'mp.product':
            map_line_data.update({
                'mp_product_id': record.id,
                'mp_product_variant_id': None,
                'map_type': 'product'
            })
        elif record._name == 'mp.product.variant':
            map_line_data.update({
                'mp_product_id': None,
                'mp_product_variant_id': record.id,
                'map_type': 'variant'
            })
        context = self._context
        _log_counter = '[%s (%s/%s)]' % (record._name, context.get('index', 0) + 1, context.get('count', 0))
        _logger.info("%s Map line data generated." % _log_counter)
        return map_line_data

    # @api.multi
    def action_start(self):
        for mapping in self:
            mapping.action_generate()
            mapping.write({'state': 'mapping'})

    # @api.multi
    def action_generate(self):
        _notify = self.env['mp.base']._notify
        mp_map_product_line_obj = self.env['mp.map.product.line']
        self.ensure_one()

        _notify('info', "Collecting information to start mapping... Please wait!", notif_sticky=True)

        # Get mp_products without variant
        mp_products = self.mp_account_id.mp_product_ids.filtered(lambda mpp: not mpp.mp_product_variant_ids)
        # Get mp_product_variants
        mp_product_variants = self.mp_account_id.mp_product_ids.mapped('mp_product_variant_ids')

        existing_map_lines = self.map_line_ids
        # Get mp_products that has map line
        mp_products_has_map_line = mp_products.filtered(
            lambda mpp: mpp.id in existing_map_lines.mapped('mp_product_id').ids)
        # Get mp_product_varints that has map line
        mp_product_variants_hash_map_line = mp_product_variants.filtered(
            lambda mppv: mppv.id in existing_map_lines.mapped('mp_product_variant_id').ids)

        # Then we can get mp_products or mp_product_variants without map line
        mp_products_has_no_map_line = mp_products.filtered(lambda mpp: mpp.id not in mp_products_has_map_line.ids)
        mp_product_variants_has_no_map_line = mp_product_variants.filtered(
            lambda mppv: mppv.id not in mp_product_variants_hash_map_line.ids)

        # Let's create mapping line based on data above
        map_line_datas = []
        map_line_datas.extend([self.with_context(
            {'index': index, 'count': len(mp_products_has_no_map_line)}).generate_map_line_data(
            mp_product_has_no_map_line) for index, mp_product_has_no_map_line in
            enumerate(mp_products_has_no_map_line)])
        map_line_datas.extend([self.with_context(
            {'index': index, 'count': len(mp_product_variants_has_no_map_line)}).generate_map_line_data(
            mp_product_variant_has_no_map_line) for index, mp_product_variant_has_no_map_line in
            enumerate(mp_product_variants_has_no_map_line)])

        if map_line_datas:
            _logger.info("Creating %s mapping lines..." % len(map_line_datas))
            _notify('info', "Creating %s mapping lines..." % len(map_line_datas), notif_sticky=True)
            # Prepare CSV file like object
            map_lines_string_iterator = StringIteratorIO(
                ('|'.join(map(clean_csv_value, tuple(map_line_data.values()))) + '\n') for map_line_data in
                map_line_datas)
            # Import CSV file like object into DB
            self._cr._obj.copy_from(map_lines_string_iterator, 'mp_map_product_line', sep='|',
                                    columns=list(map_line_datas[0].keys()))
            # Prepare to recompute the imported records
            self.env.add_todo(mp_map_product_line_obj._fields['name'],
                              mp_map_product_line_obj.search([('marketplace', '=', self.marketplace)]))
            self.env.add_todo(mp_map_product_line_obj._fields['company_id'],
                              mp_map_product_line_obj.search([('marketplace', '=', self.marketplace)]))
            # Do recompute to fill missing field's values
            mp_map_product_line_obj.recompute()
            self.invalidate_cache()
            _logger.info("Created %s mapping lines." % len(map_line_datas))
            _notify('info', "Created %s mapping lines." % len(map_line_datas), notif_sticky=True)

        # After creating new map lines, then let's process existing map line that we retrieved previously
        unmapped_map_lines = existing_map_lines.filtered(lambda ml: ml.state == 'unmapped')
        _logger.info("Processing %s unmapped map lines..." % len(unmapped_map_lines))
        _notify('info', "Processing %s unmapped map lines..." % len(unmapped_map_lines), notif_sticky=True)
        processed, skipped = unmapped_map_lines.do_mapping()
        _logger.info("Processed %s map lines..." % processed)
        _notify('info', "Processed %s map lines..." % processed, notif_sticky=True)
        _logger.info("Skipped %s map lines..." % skipped)
        _notify('info', "Skipped %s map lines..." % skipped, notif_sticky=True)

    # @api.multi
    def action_generate_product(self):
        product_tmpl_obj = self.env['product.template']
        product_obj = self.env['product.product']
        _notify = self.env['mp.base']._notify

        self.ensure_one()

        # Generate mapping first to make sure
        self.action_generate()

        # Get Unmapped map_lines and its mp_products
        unmapped_map_lines = self.map_line_ids.filtered(lambda ml: ml.state == 'unmapped')
        mp_products = unmapped_map_lines.mapped('mp_product_id') | unmapped_map_lines.mapped(
            'mp_product_variant_id').mapped('mp_product_id')
        # Get mp_products without variant
        mp_products_without_variant = mp_products.filtered(lambda mpp: not mpp.mp_product_variant_ids)
        # Get mp_products with variant
        mp_products_with_variant = mp_products.filtered(lambda mpp: mpp.mp_product_variant_ids)

        # Check if product variant is enabled
        if mp_products_with_variant.exists() and not self.user_has_groups('product.group_product_variant'):
            raise UserError("There are MP Products with variant but you don't have access to "
                            "manage product variant in Odoo, please enable Product Variant feature!")

        # Process mp_products
        _logger.info("Creating products for %s unmapped map lines..." % len(unmapped_map_lines))
        _notify('info', "Creating products for %s unmapped map lines..." % len(unmapped_map_lines), notif_sticky=True)

        set_values = {
            'generated_by_mapping': True,
            'product_map_ref': '%s,%s' % (self._name, self.id),
        }
        if mp_products_without_variant:
            # Process mp_products_without_variant: Create product.template
            product_tmpl_datas = [
                mp_product.with_context({'set_values': set_values})._prepare_product_tmpl_values()
                for mp_product in mp_products_without_variant
            ]
            self.env['mp.base'].pg_copy_from('product_template', product_tmpl_datas)
            product_tmpls = product_tmpl_obj.search([('product_map_ref', '=', '%s,%s' % (self._name, self.id))])
            self.env['mp.base'].do_recompute(product_tmpl_obj, records=product_tmpls,
                                             skip_fields=['barcode', 'default_code', 'standard_price', 'volume',
                                                          'weight'])

            # Process mp_products_without_variant: Create product.product
            product_fields_list = ['id AS product_tmpl_id', 'default_code', 'weight', 'volume']
            product_datas = self.env['mp.base'].pg_select('product_template', product_fields_list,
                                                          where="product_map_ref = '%s,%s'" % (self._name, self.id))
            product_datas = [dict(product_data, **dict(set_values, **{
                'active': True
            })) for product_data in product_datas]
            self.env['mp.base'].pg_copy_from('product_product', product_datas)
            self.env['mp.base'].do_recompute(product_obj, domain=[('product_tmpl_id', 'in', product_tmpls.ids)])

        if mp_products_with_variant:
            # Process mp_products_with_variant: Create product.template
            product_tmpl_datas = [
                mp_product.with_context({'set_values': dict(set_values, **{
                    'mp_product_ids_ref': str(mp_product.id)
                })})._prepare_product_tmpl_values()
                for mp_product in mp_products_with_variant
            ]
            self.env['mp.base'].pg_copy_from('product_template', product_tmpl_datas)
            product_tmpls = product_tmpl_obj.search(
                [('product_map_ref', '=', '%s,%s' % (self._name, self.id)), ('mp_product_ids_ref', '!=', False)])
            product_tmpls = product_tmpls.filtered(lambda pt: any(
                [int(mp_product_id) in mp_products_with_variant.ids for mp_product_id in
                 pt.mp_product_ids_ref.split(',')]))
            self.env['mp.base'].do_recompute(product_tmpl_obj, records=product_tmpls,
                                             skip_fields=['barcode', 'default_code', 'standard_price', 'volume',
                                                          'weight'])

            # Process mp_products_with_variant: Create product.product
            product_fields_list = ['mp_product_id', 'default_code', 'weight', 'volume']
            product_datas = self.env['mp.base'].pg_select('mp_product_variant', product_fields_list,
                                                          where="mp_product_id IN (%s)" % ','.join(
                                                              [str(mp_product_id)
                                                               for mp_product_id in mp_products_with_variant.ids]))
            for product_data in product_datas:
                mp_product_id = str(product_data.pop('mp_product_id'))
                product_tmpl = product_tmpls.filtered(lambda pt: mp_product_id in pt.mp_product_ids_ref.split(','))
                product_data.update({
                    'active': True,
                    'generated_by_mapping': True,
                    'product_tmpl_id': product_tmpl.id
                })
            self.env['mp.base'].pg_copy_from('product_product', product_datas)
            self.env['mp.base'].do_recompute(product_obj, domain=[('product_tmpl_id', 'in', product_tmpls.ids)])

        # Do mapping
        _logger.info("Processing %s unmapped map lines..." % len(unmapped_map_lines))
        _notify('info', "Processing %s unmapped map lines..." % len(unmapped_map_lines), notif_sticky=True)
        processed, skipped = unmapped_map_lines.do_mapping()
        _logger.info("Processed %s map lines..." % processed)
        _notify('info', "Processed %s map lines..." % processed, notif_sticky=True)
        _logger.info("Skipped %s map lines..." % skipped)
        _notify('info', "Skipped %s map lines..." % skipped, notif_sticky=True)

    # @api.multi
    def action_edit(self):
        self.ensure_one()

        action = self.env.ref('izi_marketplace.action_window_mp_map_product_line').read()[0]
        action['domain'] = [('map_id', '=', self.id)]
        return action

    # @api.multi
    def action_view_unmapped_line(self):
        self.ensure_one()

        action = self.env.ref('izi_marketplace.action_window_mp_map_product_line').read()[0]
        action['domain'] = [('map_id', '=', self.id), ('state', '=', 'unmapped')]
        return action

    # @api.multi
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
    mp_product_variant_model_id = fields.Many2one(comodel_name="ir.model", required=False,
                                                  default=lambda self: self.env.ref(
                                                      'izi_marketplace.model_mp_product_variant').id,
                                                  string="MP Product Variant Model")
    product_field_id = fields.Many2one(comodel_name="ir.model.fields",
                                       string="Product Field", ondelete='cascade', required=True)
    mp_product_field_id = fields.Many2one(comodel_name="ir.model.fields", string="MP Product Field")
    mp_product_variant_field_id = fields.Many2one(comodel_name="ir.model.fields", string="MP Product Variant Field")


class MarketplaceMapProductLine(models.Model):
    _name = 'mp.map.product.line'
    _description = 'Marketplace Map Product Line'
    _order = 'state,name'

    MAP_LINE_TYPES = [
        ('product', 'Product'),
        ('variant', 'Variant'),
    ]

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
    product_id = fields.Many2one(comodel_name="product.product", string="Product",
                                 required=False, domain=[('type', '=', 'product')])
    product_tmpl_id = fields.Many2one(comodel_name="product.template", string="Product Template",
                                      related="product_id.product_tmpl_id")
    mp_product_id = fields.Many2one(comodel_name="mp.product", string="MP Product", required=False)
    mp_product_variant_id = fields.Many2one(comodel_name="mp.product.variant", string="MP Product Variant",
                                            required=False)
    map_type = fields.Selection(string="Type", selection=MAP_LINE_TYPES, required=True)
    state = fields.Selection(string="Status", selection=MAP_LINE_STATES, required=True, default="unmapped",
                             readonly=True)
    generated_by_mapping = fields.Boolean(string="Generated by Mapping?", default=False)

    # @api.multi
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
            self.state = 'mapped'
        else:
            self.state = 'unmapped'
        self.generated_by_mapping = False

    @api.model
    def get_product_or_variant(self, map_line):
        if map_line.mp_product_id and not map_line.mp_product_variant_id:
            return map_line.mp_product_id

        if not map_line.mp_product_id and map_line.mp_product_variant_id:
            return map_line.mp_product_variant_id

    @api.model
    def check_need_update(self, map_line, map_line_data):
        current_map_line_data = {
            'map_id': map_line.map_id.id or None,
            'mp_account_id': map_line.map_id.mp_account_id.id or None,
            'marketplace': map_line.map_id.mp_account_id.marketplace,
            'state': map_line.state,
            'product_id': map_line.product_id.id or None,
            'mp_product_id': map_line.mp_product_id.id or None,
            'mp_product_variant_id': map_line.mp_product_variant_id.id or None,
            'map_type': map_line.map_type,
            'generated_by_mapping': map_line.generated_by_mapping
        }
        return current_map_line_data != map_line_data

    # @api.multi
    def do_mapping(self):
        get_product_or_variant = self.get_product_or_variant
        check_need_update = self.check_need_update

        mappings = [
            (map_line, map_line.map_id.with_context({'index': index, 'count': len(self)})
             .generate_map_line_data(get_product_or_variant(map_line))) for index, map_line in enumerate(self)
        ]

        need_update_mappings = list(filter(lambda m: m, map(lambda m: m if check_need_update(*m) else False, mappings)))
        processed, skipped = 0, 0

        if not need_update_mappings:
            skipped = len(mappings)
            return processed, skipped

        def _prepare_map_line_data(mapping):
            map_line, map_line_data = mapping
            return dict(dict([('id', map_line.id)]), **map_line_data)

        map_line_datas = list(map(_prepare_map_line_data, need_update_mappings))

        # Prepare SQL Query
        tmp_tbl_name = 'tmp_map_line_%s' % uuid.uuid4().hex[:8]
        tmp_map_line_columns = [
            "id int4", "map_id int4", "mp_account_id int4", "marketplace varchar", "state varchar", "product_id int4",
            "mp_product_id int4", "mp_product_variant_id int4", "generated_by_mapping bool", "map_type varchar"
        ]
        map_line_update_columns = [
            "%(col)s = %(tmp_tbl)s.%(col)s" % {'col': col, 'tmp_tbl': tmp_tbl_name}
            for col in map_line_datas[0].keys() if col != 'id'
        ]

        # Execute SQL Query
        self.env['mp.base'].pg_create_table(tmp_tbl_name, tmp_map_line_columns, temp=True)
        self.env['mp.base'].pg_copy_from(tmp_tbl_name, map_line_datas)
        self.env['mp.base'].pg_update("mp_map_product_line", map_line_update_columns, from_table=tmp_tbl_name,
                                      where="mp_map_product_line.id = %s.id" % tmp_tbl_name)
        self.env['mp.base'].pg_drop_table(tmp_tbl_name)

        processed = len(map_line_datas)
        skipped = len(mappings) - processed

        return processed, skipped
