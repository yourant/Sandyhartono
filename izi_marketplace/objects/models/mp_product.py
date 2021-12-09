# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models, tools

from odoo.addons import decimal_precision as dp


class MarketplaceProduct(models.Model):
    _name = 'mp.product'
    _inherit = 'mp.base'
    _description = 'Marketplace Product'
    _rec_mp_external_id = {}

    name = fields.Char(string="Name", index=True, required=True)
    active = fields.Boolean(default=True)
    currency_id = fields.Many2one(related="mp_account_id.currency_id")
    company_id = fields.Many2one(related="mp_account_id.company_id")
    description_sale = fields.Text(string="Sale Description",
                                   help="A description of the Product that you want to communicate to your customers. "
                                        "This description will be copied to every Sales Order, Delivery Order and "
                                        "Customer Invoice/Credit Note")
    default_code = fields.Char(string="Internal Reference")
    list_price = fields.Float(string="Sales Price", default=1.0, digits=dp.get_precision('Product Price'),
                              help="Base price to compute the customer price. Sometimes called the catalog price.")
    weight = fields.Float(string="Weight", digits=dp.get_precision('Stock Weight'),
                          help="The weight of the contents in Kg, not including any packaging, etc.")
    volume = fields.Float("Volume", help="The volume in m3.")
    length = fields.Float(string="Length", required=False)
    width = fields.Float(string="Width", required=False)
    height = fields.Float(string="Height", required=False)
    image = fields.Binary(string="Image", attachment=True,
                          help="This field holds the image used as image for the product, limited to 1024x1024px.")
    image_medium = fields.Binary(string="Medium-sized image", attachment=True,
                                 help="Medium-sized image of the product. It is automatically "
                                      "resized as a 128x128px image, with aspect ratio preserved, "
                                      "only when the image exceeds one of those sizes. Use this field in form views "
                                      "or some kanban views.")
    image_small = fields.Binary(string="Small-sized image", attachment=True,
                                help="Small-sized image of the product. It is automatically "
                                     "resized as a 64x64px image, with aspect ratio preserved. "
                                     "Use this field anywhere a small image is required.")
    mp_product_image_ids = fields.One2many(comodel_name="mp.product.image", inverse_name="mp_product_id",
                                           string="Marketplace Product Images")
    mp_product_main_image_url = fields.Char(string="Marketplace Product Main Image URL",
                                            compute="_compute_mp_product_main_image_url", store=True)
    mp_product_variant_ids = fields.One2many(comodel_name="mp.product.variant", inverse_name="mp_product_id",
                                             string="Marketplace Product Variant")
    mp_product_variant_count = fields.Integer(
        '# Product Variants', compute='_compute_product_variant_count')
    debug_store_product_img = fields.Boolean(related="mp_account_id.debug_store_product_img")

    @api.model
    def create(self, values):
        mp_product = super(MarketplaceProduct, self).create(values)
        if mp_product.mp_product_image_ids:
            mp_product_image = mp_product.get_main_image()
            mp_product.write({'image': mp_product_image.image})
        return mp_product

    # @api.multi
    def write(self, values):
        res = super(MarketplaceProduct, self).write(values)
        for mp_product in self:
            if mp_product.mp_product_image_ids:
                mp_product_image = mp_product.get_main_image()
                if mp_product_image.id != self._context.get('latest_mp_product_image_id'):
                    mp_product.with_context({'latest_mp_product_image_id': mp_product_image.id}).write(
                        {'image': mp_product_image.image})
            else:
                if not self._context.get('mp_product_image_id_cleaned'):
                    mp_product.with_context({'mp_product_image_id_cleaned': True}).write({'image': False})
        return res

    @api.onchange('mp_product_image_ids')
    def onchange_mp_product_image_ids(self):
        if self.mp_product_image_ids:
            mp_product_image = self.mp_product_image_ids.filtered(lambda s: not isinstance(s.id, int))
            if mp_product_image.exists():
                mp_product_image.sequence -= len(self.mp_product_image_ids)

    # @api.multi
    def get_product(self):
        mp_map_product_line_obj = self.env['mp.map.product.line']

        self.ensure_one()
        mp_account = self.mp_account_id
        map_line = mp_map_product_line_obj.search([
            ('mp_account_id', '=', mp_account.id),
            ('mp_product_id', '=', self.id)
        ])
        return map_line.product_id

    # @api.multi
    def _prepare_product_tmpl_values(self):
        product_tmpl_obj = self.env['product.template']

        self.ensure_one()
        values = {}

        # Get default values
        fields_with_default = []
        for fname, field in product_tmpl_obj._fields.items():
            if field.type in ['one2many', 'many2many']:  # Exclude "x2many" field type
                continue
            if field.default and field.store:
                fields_with_default.append(fname)
        values.update(product_tmpl_obj.default_get(fields_with_default))

        # Set custom values
        values.update({
            'type': 'product',
            'company_id': self.company_id.id
        })

        # Set values from mp_product
        mp_product_data = self.copy_data()[0]
        mp_fields_list = ['name', 'default_code', 'list_price', 'description_sale', 'weight', 'volume']
        values.update(dict([(mp_fname, mp_product_data.get(mp_fname)) for mp_fname in mp_fields_list]))

        if self._context.get('set_values'):
            values.update(self._context.get('set_values'))

        return values

    # @api.multi
    def create_product_tmpl(self):
        _logger = self.env['mp.base']._logger
        product_tmpl_obj = self.env['product.template']

        self.ensure_one()

        values = self._prepare_product_tmpl_values()

        _log_msg = 'Creating product.template of "%s"' % self.name
        if self._context.get('_log_counter'):
            _log_msg = '%s %s' % (self._context.get('_log_counter'), _log_msg)
        _logger(self.marketplace, _log_msg)

        # Check is it have variant?
        if self.mp_product_variant_ids.exists():
            product_tmpl = product_tmpl_obj.with_context({'create_product_product': False})
            for mp_product_variant in self.mp_product_variant_ids:
                mp_product_variant.create_product(product_tmpl)
        else:
            product_tmpl = product_tmpl_obj.create(values)

        return product_tmpl

    # @api.multi
    def get_main_image(self):
        self.ensure_one()
        if self.mp_product_image_ids.exists():
            return self.mp_product_image_ids.sorted('sequence')[0]
        return self.mp_product_image_ids

    @api.depends('mp_product_image_ids.sequence', 'mp_product_image_ids.name')
    def _compute_mp_product_main_image_url(self):
        for mp_product in self:
            mp_product_main_img = mp_product.get_main_image()
            mp_product.mp_product_main_image_url = mp_product_main_img.name

    @api.one
    @api.depends('mp_product_variant_ids.mp_product_id')
    def _compute_product_variant_count(self):
        # do not pollute variants to be prefetched when counting variants
        self.mp_product_variant_count = len(self.with_prefetch().mp_product_variant_ids)

    # @api.multi
    def action_view_mp_product_variant(self):
        self.ensure_one()
        action = self.env.ref('izi_marketplace.action_window_mp_product_variant_view_per_mp_product').read()[0]
        action.update({
            'domain': [('mp_product_id', '=', self.id)],
            'context': {
                'default_marketplace': self.marketplace,
                'default_mp_product_id': self.id
            }
        })
        return action
