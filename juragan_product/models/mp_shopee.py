# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.addons.juragan_webhook import BigInteger, BigMany2one, BigMany2many
from odoo.exceptions import ValidationError
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from odoo.tools.safe_eval import safe_eval
class MPShopee(models.Model):
    _name = 'mp.shopee'
    _description = 'Shopee Account'
    _rec_name = 'shop_name'

    name = fields.Char(readonly=True, )
    active = fields.Boolean()
    shop_name = fields.Char()
    shop_description = fields.Text()
    country = fields.Selection([
        ('ID', 'Indonesia'),
    ])

    wh_id = fields.Many2one(
        'stock.warehouse', string='Warehouse',)

    shop_logistic_ids = fields.One2many('mp.shopee.shop.logistic', 'mp_id')
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
    company_id = fields.Many2one(comodel_name="res.company", string="Company")

    def name_get(self):
        result = []
        for this in self:
            names = []
            if not this.active:
                names.append('[ Inactive ]')
            if this.shop_name:
                names.append(this.shop_name)
            else:
                names.append(
                    this.name or str('mp.shopee.' + str(this.id)))
            result.append((this.id, ' '.join(names)))
        return result


class MPShopeeItemCategory(models.Model):
    _name = 'mp.shopee.item.category'
    _inherit = 'mp.bigint'
    _description = 'Shopee Item Category'
    _rec_name = 'complete_name'
    # _order = 'path'

    category_id = BigMany2one(_name)
    
    complete_name = fields.Char()
    parent_id = fields.Many2one(_name, 'Parent Category', index=True, ondelete='cascade')
    child_ids = fields.One2many(_name, 'parent_id', 'Child Categories')
    # path = fields.Char(required=True)

    name = fields.Char()
    category_name = fields.Char(related='name')
    has_children = fields.Boolean()
    days_to_ship_limits_max_limit = fields.Integer()
    days_to_ship_limits_min_limit = fields.Integer()

    attributes = BigMany2many('mp.shopee.item.attribute')
    brands = fields.Many2many('mp.shopee.item.brand', 'mp_shopee_item_brand_mp_shopee_item_category_rel')
#     parent_attributes = BigMany2many('mp.shopee.item.attribute', compute='_get_parent_attribute')

    active = fields.Boolean(default=True)

    izi_id = fields.Integer('Izi ID')
    izi_md5 = fields.Char()
#     def _get_parent_attribute(self):
#         for rec in self:
#             rec.parent_attributes = (rec.attributes.ids or []) + (rec.parent_id and rec.parent_id.parent_attributes.ids or [])

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for category in self:
            if category.parent_id:
                category.complete_name = '%s / %s' % (category.parent_id.complete_name, category.name)
            else:
                category.complete_name = category.name

    @api.constrains('parent_id')
    def _check_category_recursion(self):
        if not self._check_recursion():
            raise ValidationError(_('Error ! You cannot create recursive categories.'))
        return True

    @api.model
    def name_create(self, name):
        return self.create({'name': name}).name_get()[0]


class MPShopeeItemAttribute(models.Model):
    _name = 'mp.shopee.item.attribute'
    _inherit = 'mp.bigint'
    _description = 'Shopee Item Attribute'
    _rec_name = 'attribute_name'

    attribute_id = BigMany2one(_name)
    attribute_name = fields.Char()
    original_attribute_name = fields.Char()
    is_mandatory = fields.Boolean()
    attribute_type = fields.Char()
    format_type = fields.Char()
    input_type = fields.Char()
    date_format_type = fields.Char()


    options = BigMany2many('mp.shopee.item.attribute.option')

    # attribute_wizard = fields.One2many('mp.shopee.item.wizard.item.attr','attributes_id')

    active = fields.Boolean(default=True)

    izi_id = fields.Integer('Izi ID')
    izi_md5 = fields.Char()

class MPShopeeItemAttributeOption(models.Model):
    _name = 'mp.shopee.item.attribute.option'
    _inherit = 'mp.bigint'
    _description = 'Shopee Item Attribute Option'

    name = fields.Char(required=True)
    original_value_name = fields.Char()
    value_unit = fields.Char()
    value_id = BigInteger()
    izi_id = fields.Integer('Izi ID')
    izi_md5 = fields.Char()
    
    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Name must be unique.')
    ]

    @api.model
    def create(self, vals):
        if vals.get('name'):
            res = self.search([('name', '=', vals.get('name'))], limit=1)
            if res:
                return res
        return super(MPShopeeItemAttributeOption, self).create(vals)


class MPShopeeItemAttributeVal(models.Model):
    _name = 'mp.shopee.item.attribute.val'
    _description = 'Shopee Item Attribute Value'
    _rec_name = 'attribute_id'

    attribute_int = BigInteger()
    attribute_id = fields.Many2one('mp.shopee.item.attribute', compute='_get_attribute_id', inverse='_set_attribute_id')
    attribute_value = fields.Char()
    item_id_staging = fields.Many2one('product.staging')

    is_mandatory = fields.Boolean(compute='_compute_attribute',readonly=1)
    values = fields.Many2many('mp.shopee.item.attribute.option', compute='_compute_attribute')
    value = fields.Many2one('mp.shopee.item.attribute.option', domain="[('id','in',values)]")

    izi_id = fields.Integer('Izi ID')
    izi_md5 = fields.Char()
    @api.depends('attribute_id')
    def _compute_attribute(self):
        for rec in self:
            if rec.attribute_id:
                rec.is_mandatory = rec.attribute_id.is_mandatory
                rec.values = rec.attribute_id.options.ids
            else:
                rec.is_mandatory = False
                rec.values = []

    def _get_attribute_id(self):
        for rec in self:
            rec.attribute_id = rec.attribute_int

    # @api.one
    def _set_attribute_id(self):
        self.attribute_int = self.attribute_id.id
    

    @api.onchange('value')
    def _set_attribute_value(self):
        self.attribute_value = self.value.display_name
    
    # @api.multi
    def write(self, vals):
        if vals.get('value'):
            option_id = vals.get('value')
            option_obj = self.env['mp.shopee.item.attribute.option'].browse(option_id)
            if option_obj:
                vals.update({
                    'attribute_value': option_obj.display_name
                })
        res = super(MPShopeeItemAttributeVal, self).write(vals)
        return res
    
    # @api.depends('value')
    # def _compute_attribute_value(self):
    #     for rec in self:
    #         rec.attribute_value = rec.value.display_name

#     @api.model
#     def create(self, vals):
#         if vals.get('item_id') and vals.get('attribute_id') and vals.get('attribute_value'):
#             res = self.search([
#                 ('item_id', '=', vals.get('item_id')),
#                 ('attribute_id', '=', vals.get('attribute_id')),
#             ], limit=1)
#             if res:
#                 print(res)
#                 print(vals)
#                 res.write({'attribute_value': vals.get('attribute_value')})
#                 return res
#         return super(MPShopeeItemAttributeVal, self).create(vals)

    _sql_constraints = [
        ('attribute_unique', 'unique(item_id_staging, attribute_int)', 'Attribute Already Exist.')
    ]

    # # @api.multi
    # def name_get(self):
    #     res = []
    #     for rec in self:
    #         rec_name = rec.attribute_id and rec.attribute_id.attribute_name or ''
    #         name = '%s%s' % (rec_name, ' [%s]' % (rec.item_sku) if rec.item_sku else '')
    #         res.append((rec.id, name))
    #     return res





class MPShopeeLogistic(models.Model):
    _name = 'mp.shopee.logistic'
    _inherit = 'mp.bigint'
    _description = 'Shopee Logistic'
    _rec_name = 'logistic_name'

    logistic_id = BigMany2one(_name)
    logistic_name = fields.Char()
    has_cod = fields.Boolean()
    # enabled = fields.Boolean()
    fee_type = fields.Char()
    sizes = BigMany2many('mp.shopee.logistic.size')
    item_max_weight = fields.Float()
    item_min_weight = fields.Float()
    item_max_dimension_height = fields.Float()
    item_max_dimension_width = fields.Float()
    item_max_dimension_length = fields.Float()
    item_max_dimension_unit = fields.Char()

    izi_id = fields.Integer('Izi ID')
    izi_md5 = fields.Char()
    # active = fields.Boolean(default=True)


class MPShopeeLogisticSize(models.Model):
    _name = 'mp.shopee.logistic.size'
    _inherit = 'mp.bigint'
    _description = 'Shopee Logistic Size'

    size_id = BigMany2one(_name)
    name = fields.Char()
    default_price = fields.Float()

    izi_id = fields.Integer('Izi ID')
    izi_md5 = fields.Char()

class MPShopeeShopLogistic(models.Model):
    _name = 'mp.shopee.shop.logistic'
    _description = 'Shopee Shop Logistic'
    _rec_name = 'logistic_id'

    mp_id = fields.Many2one('mp.shopee', string='Account', ondelete='cascade')
    logistic_id = BigMany2one('mp.shopee.logistic', required=True)
    enabled = fields.Boolean()
    is_parent = fields.Boolean()

    active = fields.Boolean(default=True)
    izi_id = fields.Integer('Izi ID')
    izi_md5 = fields.Char()
    # @api.constrains('enabled')
    # def _check_enabled(self):
    #     for rec in self:
    #         rec.mp_id.set_shop_logistic(logistic_ids=rec.logistic_id.ids, enabled=rec.enabled)

    _sql_constraints = [
        ('logistic_unique', 'unique(mp_id, logistic_id)', 'Logistic Already Exist.')
    ]


class MPShopeeItemLogistic(models.Model):
    _name = 'mp.shopee.item.logistic'
    _description = 'Shopee Item Logistic'
    _rec_name = 'logistic_id'

    item_id_staging = fields.Many2one('product.staging')
    logistic_id = fields.Many2one('mp.shopee.logistic',domain="[('id','in',shop_logistic)]")
    enabled = fields.Boolean()
    shipping_fee = fields.Float()
    size_id = fields.Many2one('mp.shopee.logistic.size')
    is_free = fields.Boolean()
    estimated_shipping_fee = fields.Float()

    shop_logistic = fields.Many2many('mp.shopee.logistic', compute='_compute_logistic')
    # value_log = fields.Many2one('mp.shopee.shop.logistic', domain="[('id','in',shop_logistic)]")
    
    izi_id = fields.Integer('Izi ID')
    izi_md5 = fields.Char()
    _sql_constraints = [
        ('logistic_unique', 'unique(item_id_staging, logistic_id)', 'Logistic Already Exist.')
    ]

    @api.depends('item_id_staging')
    def _compute_logistic(self):
        for rec in self:
            if rec.item_id_staging:
                mp_id = rec.item_id_staging.mp_shopee_id.id
                shop_logistic = self.env['mp.shopee.shop.logistic'].search([('mp_id','=',mp_id),('enabled','=',True),('is_parent','=',True)])
                shop_logistic_ids = []
                for log in shop_logistic:
                    shop_logistic_ids.append(log.logistic_id.id)
                rec.shop_logistic = [(6, 0, shop_logistic_ids)] 



class MPShopeeProductAttributeVar(models.Model):
    _name = "mp.shopee.item.var.attribute"
    _description = "Shopee Product Attribute Variant"
    _order = 'name'

    name = fields.Char('Name', required=True, translate=True)
    value_ids = fields.One2many('mp.shopee.item.var.attribute.value', 'attribute_id', 'Values', copy=True)
    attribute_line_ids = fields.One2many('mp.shopee.attribute.line', 'attribute_id', 'Lines')
    create_variant = fields.Boolean(default=True, help="Check this if you want to create multiple variants for this attribute.")

    izi_id = fields.Integer('Izi ID')
    izi_md5 = fields.Char()


class MPShopeeAttributeVarvalue(models.Model):
    _name = "mp.shopee.item.var.attribute.value"
    _order = 'attribute_id, id'

    name = fields.Char('Value', required=True, translate=True)
    attribute_id = fields.Many2one('mp.shopee.item.var.attribute', 'Attribute', ondelete='cascade', required=True)
    product_ids = fields.Many2many('product.staging.variant', string='Variants', readonly=True)

    izi_id = fields.Integer('Izi ID')
    izi_md5 = fields.Char()


    _sql_constraints = [
        ('value_company_uniq', 'unique (name,attribute_id)', 'This attribute value already exists !')
    ]


    # @api.multi
    def name_get(self):
        if not self._context.get('show_attribute', True):  # TDE FIXME: not used
            return super(MPShopeeAttributeVarvalue, self).name_get()
        return [(value.id, "%s: %s" % (value.attribute_id.name, value.name)) for value in self]

    # @api.multi
    def unlink(self):
        linked_products = self.env['product.product'].with_context(active_test=False).search([('attribute_value_ids', 'in', self.ids)])
        if linked_products:
            raise UserError(_('The operation cannot be completed:\nYou are trying to delete an attribute value with a reference on a product variant.'))
        return super(MPShopeeAttributeVarvalue, self).unlink()

    # @api.multi
    def _variant_name(self, variable_attributes):
        return ", ".join([v.name for v in self if v.attribute_id in variable_attributes])


class MPShopeeAttributeLine(models.Model):
    _name = "mp.shopee.attribute.line"
    _rec_name = 'attribute_id'

    product_staging_id  = fields.Many2one('product.staging', 'Product Staging', ondelete='cascade', required=True)
    attribute_id = fields.Many2one('mp.shopee.item.var.attribute', 'Attribute', ondelete='restrict', required=True)
    value_ids = fields.Many2many('mp.shopee.item.var.attribute.value', string='Attribute Values')

    izi_id = fields.Integer('Izi ID')
    izi_md5 = fields.Char()

    @api.constrains('value_ids', 'attribute_id')
    def _check_valid_attribute(self):
        if any(line.value_ids > line.attribute_id.value_ids for line in self):
            raise ValidationError(_('Error ! You cannot use this attribute with the following value.'))
        return True

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        # TDE FIXME: currently overriding the domain; however as it includes a
        # search on a m2o and one on a m2m, probably this will quickly become
        # difficult to compute - check if performance optimization is required
        if name and operator in ('=', 'ilike', '=ilike', 'like', '=like'):
            args = args or []
            domain = ['|', ('attribute_id', operator, name), ('value_ids', operator, name)]
            return self.search(expression.AND([domain, args]), limit=limit).name_get()
        return super(MPShopeeAttributeLine, self).name_search(name=name, args=args, operator=operator, limit=limit)


# class MPShopeeItemWizardItemAttr(models.TransientModel):
#     _name = 'mp.shopee.item.wizard.item.attr'
#     _description = 'Shopee Item Wizard Item Attribute'
#     _rec_name = 'attributes_id'
    
#     item_staging_id = fields.Many2one('product.staging')
#     attributes_id = fields.Many2one('mp.shopee.item.attribute')
#     is_mandatory = fields.Boolean(compute='_compute_attribute')
#     values = fields.Many2many('mp.shopee.item.attribute.option', compute='_compute_attribute')
#     value = fields.Many2one('mp.shopee.item.attribute.option', domain="[('id','in',values)]")
    
#     @api.depends('attributes_id')
#     def _compute_attribute(self):
#         for rec in self:
#             if rec.attributes_id:
#                 rec.is_mandatory = rec.attributes_id.is_mandatory
#                 rec.values = rec.attributes_id.options.ids


class MPShopeeItemAttribute(models.Model):
    _name = 'mp.shopee.item.brand'
    _description = 'Shopee Item Brand'
    
    brand_id = BigInteger()
    name = fields.Char()
    original_brand_name = fields.Char()
    is_mandatory = fields.Boolean()
    input_type = fields.Char()

    categories = fields.Many2many(
        'mp.shopee.item.category',
        'mp_shopee_item_brand_mp_shopee_item_category_rel')
    
    active = fields.Boolean(default=True)

    izi_id = fields.Integer('Izi ID')
    izi_md5 = fields.Char()