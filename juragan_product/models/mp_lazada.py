# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.addons.juragan_webhook import BigInteger, BigMany2one, BigMany2many
from odoo.exceptions import ValidationError
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from odoo.tools.safe_eval import safe_eval

class MPLazada(models.Model):
    _name = 'mp.lazada'
    _description = 'Lazada Account'
    _rec_name = 'seller_name'

    country = fields.Selection([
        ('id', 'Indonesia'),
    ], default='id')

    name = fields.Char(readonly=True, )
    active = fields.Boolean()

    seller_name_company = fields.Char(readonly=True)
    seller_logo_url = fields.Char(readonly=True)
    seller_name = fields.Char(readonly=True)
    seller_location = fields.Char(readonly=True)
    seller_seller_id = fields.Char(readonly=True)
    seller_email = fields.Char(readonly=True)
    seller_short_code = fields.Char(readonly=True)
    seller_cb = fields.Char(readonly=True)

    brand_ids = fields.Many2many('mp.lazada.brand', compute='_get_brand_ids', string='Lazada Brands')
    category_ids = fields.Many2many('mp.lazada.category', compute='_get_category_ids', string='Lazada Categories')

    server_id = fields.Many2one('webhook.server')
    wh_id = fields.Many2one('stock.warehouse', string='Warehouse')
    izi_id = fields.Integer()
    izi_md5 = fields.Char()
    wh_shop_id = fields.Many2one('stock.warehouse', string='Shop Warehouse')
    wh_main_id = fields.Many2one('stock.warehouse', string='Main Warehouse')
    wh_config = fields.Selection([
        ('main','Main Warehouse'),
        ('shop','Shop Warehouse'),], string='Take Stock From', default='main')
    sync_stock_active = fields.Boolean('Realtime Stock Update')
    partner_id = fields.Many2one(comodel_name="res.partner", string="Default Customer", required=False)

    def name_get(self):
        result = []
        for this in self:
            names = []
            if not this.active:
                names.append('[ Inactive ]')
            if this.seller_name:
                names.append(this.seller_name)
            else:
                names.append(
                    this.name or str('mp.lazada.' + str(this.id)))
            result.append((this.id, ' '.join(names)))
        return result

    def _get_brand_ids(self):
        brand_obj = self.env['mp.lazada.brand']
        for rec in self:
            rec.brand_ids = brand_obj.search([])
            
    def _get_category_ids(self):
        category_obj = self.env['mp.lazada.category']
        for rec in self:
            rec.category_ids = category_obj.search([('child_ids', '=', False)])


class MPLazadaBrand(models.Model):
    _name = 'mp.lazada.brand'
    _description = 'Lazada Brand'
    
    name = fields.Char(required=True)
    global_identifier = fields.Char()
    name_en = fields.Char()
    
    active = fields.Boolean(default=True)

    izi_id = fields.Integer()
    izi_md5 = fields.Char()
class MPLazadaCategory(models.Model):
    _name = 'mp.lazada.category'
    _description = 'Lazada Category'
    _rec_name = 'complete_name'
    _order = 'path'
        
    complete_name = fields.Char()
    parent_id = fields.Many2one(_name, 'Parent Category', index=True, ondelete='cascade')
    child_ids = fields.One2many(_name, 'parent_id', 'Child Categories')
    path = fields.Char(required=True)
    
    var = fields.Boolean()
    name = fields.Char(required=True)
    leaf = fields.Boolean()
#     attr = fields.Text('Attribute', compute='_get_attr')
    attr_ids = fields.One2many('mp.lazada.category.attr', 'category_id')
    
    active = fields.Boolean(default=True)
    izi_id = fields.Integer()
    izi_md5 = fields.Char()

    # @api.depends('name', 'parent_id.complete_name')
    # def _compute_complete_name(self):
    #     for category in self:
    #         if category.parent_id:
    #             category.complete_name = '%s / %s' % (category.parent_id.complete_name, category.name)
    #         else:
    #             category.complete_name = category.name

    @api.constrains('parent_id')
    def _check_category_recursion(self):
        if not self._check_recursion():
            raise ValidationError(_('Error ! You cannot create recursive categories.'))
        return True

    @api.model
    def name_create(self, name):
        return self.create({'name': name}).name_get()[0]

class MPLazadaCategoryAttr(models.Model):
    _name = 'mp.lazada.category.attr'
    _description = 'Lazada Category Attribute'
    _rec_name = 'label'
    
    category_id = fields.Many2one('mp.lazada.category')
    advanced = fields.Char()
    label = fields.Char()
    name = fields.Char()
    is_mandatory = fields.Boolean()
    is_key_prop = fields.Boolean()
    attribute_type = fields.Char()
    input_type = fields.Char()
    options = fields.Many2many('mp.lazada.category.attr.opt')
    is_sale_prop = fields.Boolean()

    izi_id = fields.Integer()
    izi_md5 = fields.Char()

class MPLazadaCategoryAttrOpt(models.Model):
    _name = 'mp.lazada.category.attr.opt'
    _description = 'Lazada Category Attribute Option'
    
    name = fields.Char(required=True)
    izi_id = fields.Integer()
    izi_md5 = fields.Char()


    @api.model
    def create(self, vals):
        if vals.get('name'):
            res = self.search([('name', '=', vals.get('name'))], limit=1)
            if res:
                return res
        return super(MPLazadaCategoryAttrOpt, self).create(vals)
    
    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Name Already Exist.')
    ]

class MPLazadaProductAttr(models.Model):
    _name = 'mp.lazada.product.attr'
    _description = 'Lazada Product Attribute'
    
    # attribute_id = BigMany2one('mp.lazada.category.attr', compute='_get_attribute_id', inverse='_set_attribute_id')
    item_id_staging = fields.Many2one('product.staging')
    attribute_id = fields.Many2one('mp.lazada.category.attr')
    name = fields.Char()
    value = fields.Text()
    values = fields.Many2many('mp.lazada.category.attr.opt', compute='_compute_attribute')
    option_id = fields.Many2one('mp.lazada.category.attr.opt',domain="[('id','in',values)]")
    is_mandatory = fields.Boolean(compute='_compute_attribute',readonly=1)

    izi_id = fields.Integer()
    izi_md5 = fields.Char()
    
    # _sql_constraints = [
    #     ('name_unique', 'unique(item_id_staging,name)', 'Name Already Exist.')
    # ]

    @api.depends('attribute_id')
    def _compute_attribute(self):
        for rec in self:
            if rec.attribute_id:
                rec.is_mandatory = rec.attribute_id.is_mandatory
                rec.values = rec.attribute_id.options.ids
            else:
                rec.is_mandatory = False
                rec.values = []

    def write(self, vals):
        if not self.env.context.get('create_product_attr'):
            if vals.get('value'):
                option_id = vals.get('value')
                option_obj = self.env['mp.lazada.category.attr.opt'].browse(option_id)
                if option_obj:
                    vals.update({
                        'value': option_obj.display_name
                    })
        res = super(MPLazadaProductAttr, self).write(vals)
        return res

class MPLazadaAttributeLine(models.Model):
    _name = 'mp.lazada.attribute.line'

    product_staging_id = fields.Many2one('product.staging')
    category_id = fields.Many2one('mp.lazada.category')
    attribute_id = fields.Many2one('mp.lazada.category.attr',domain=[('category_id', '=', 'category_id'), ('is_sale_prop', '=', True)])
    attr_values = fields.Many2many('mp.lazada.variant.value', compute='_compute_attribute')

    lz_variant_value_ids = fields.Many2many('mp.lazada.variant.value',domain="[('id','in',attr_values)]")
    # option_ids = fields.Many2many('mp.lazada.category.attr.opt')
    
    izi_id = fields.Integer()
    izi_md5 = fields.Char()
    
    @api.depends('attribute_id')
    def _compute_attribute(self):
        for rec in self:
            if rec.attribute_id:
                rec.attr_values = self.env['mp.lazada.variant.value'].search(
                    [('lz_value_id','in',rec.attribute_id.options.ids)])
            else:
                rec.attr_values = []
class MPLazadaVariantValue(models.Model):

    _name = 'mp.lazada.variant.value'

    name = fields.Char('Value')
    lz_value_id = fields.Many2one('mp.lazada.category.attr.opt')
    product_staging_variant_ids = fields.Many2many('product.staging.variant')
    lz_attribute_line_ids = fields.Many2many('mp.lazada.attribute.line')

    izi_id = fields.Integer()
    izi_md5 = fields.Char()
    

class MPLazadaCategoryAttr(models.Model):
    _inherit = 'mp.lazada.category.attr'

    value_options = fields.Many2many('mp.lazada.variant.value')
    attribute_line_ids = fields.One2many('mp.lazada.attribute.line', 'attribute_id', 'Lines')