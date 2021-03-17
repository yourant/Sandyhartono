# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.addons.juragan_webhook import BigInteger, BigMany2one, BigMany2many

class MPShopee(models.Model):
    _name = 'mp.shopee'
    _description = 'Shopee Account'

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
    izi_id = fields.Integer('Izi ID')
    izi_md5 = fields.Char()



class MPShopeeItemCategory(models.Model):
    _name = 'mp.shopee.item.category'
    _inherit = 'mp.bigint'
    _description = 'Shopee Item Category'
    _rec_name = 'complete_name'
    # _order = 'path'
    
    category_id = BigMany2one(_name)
    
    complete_name = fields.Char(compute='_compute_complete_name', search=lambda s, o, v:[('name', o, v)])
    parent_id = fields.Many2one(_name, 'Parent Category', index=True, ondelete='cascade')
    child_ids = fields.One2many(_name, 'parent_id', 'Child Categories')
    # path = fields.Char(required=True)
    
    name = fields.Char()
    category_name = fields.Char(related='name')
    has_children = fields.Boolean()
    days_to_ship_limits_max_limit = fields.Integer()
    days_to_ship_limits_min_limit = fields.Integer()
    
    attributes = BigMany2many('mp.shopee.item.attribute')
#     parent_attributes = BigMany2many('mp.shopee.item.attribute', compute='_get_parent_attribute')
    
    active = fields.Boolean(default=True)
    
    izi_id = fields.Integer('Izi ID')
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
    is_mandatory = fields.Boolean()
    attribute_type = fields.Char()
    input_type = fields.Char()
    options = BigMany2many('mp.shopee.item.attribute.option')
    
    active = fields.Boolean(default=True)

    izi_id = fields.Integer('Izi ID')

class MPShopeeItemAttributeOption(models.Model):
    _name = 'mp.shopee.item.attribute.option'
    _inherit = 'mp.bigint'
    _description = 'Shopee Item Attribute Option'
    
    name = fields.Char(required=True)
    izi_id = fields.Integer('Izi ID')

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
    attribute_id = BigMany2one('mp.shopee.item.attribute', compute='_get_attribute_id', inverse='_set_attribute_id')
    attribute_value = fields.Char()
    item_id_staging = BigMany2one('product.staging')
    izi_id = fields.Integer('Izi ID')
    
    def _get_attribute_id(self):
        for rec in self:
            rec.attribute_id = rec.attribute_int

    def _set_attribute_id(self):
        self.attribute_int = self.attribute_id.id
    
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

    
    def name_get(self):
        res = []
        for rec in self:
            name = '%s%s' % (rec.name, ' [%s]' % (rec.item_sku) if rec.item_sku else '')
            res.append((rec.id, name))
        return res


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
 
    # active = fields.Boolean(default=True)

    
class MPShopeeLogisticSize(models.Model):
    _name = 'mp.shopee.logistic.size'
    _inherit = 'mp.bigint'
    _description = 'Shopee Logistic Size'
    
    size_id = BigMany2one(_name)
    name = fields.Char()
    default_price = fields.Float()

    izi_id = fields.Integer('Izi ID')


class MPShopeeShopLogistic(models.Model):
    _name = 'mp.shopee.shop.logistic'
    _description = 'Shopee Shop Logistic'
    _rec_name = 'logistic_id'
    
    mp_id = fields.Many2one('mp.shopee', string='Account', ondelete='cascade')
    logistic_id = BigMany2one('mp.shopee.logistic', required=True)
    enabled = fields.Boolean()
    
    active = fields.Boolean(default=True)
    izi_id = fields.Integer('Izi ID')

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
    
    item_id_staging = BigMany2one('product.staging')
    logistic_id = BigMany2one('mp.shopee.logistic')
    enabled = fields.Boolean()
    shipping_fee = fields.Float()
    size_id = BigMany2one('mp.shopee.logistic.size')
    is_free = fields.Boolean()
    estimated_shipping_fee = fields.Float()
    
    izi_id = fields.Integer('Izi ID')

    _sql_constraints = [
        ('logistic_unique', 'unique(item_id_staging, logistic_id)', 'Logistic Already Exist.')
    ]

