from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.addons.juragan_webhook import BigInteger, BigMany2one, BigMany2many
from odoo.exceptions import ValidationError
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from odoo.tools.safe_eval import safe_eval


class MPBlibli(models.Model):
    _name = 'mp.blibli'
    _description = 'Blibli Account'
    _rec_name = 'shop_name'

    name = fields.Char()
    shop_name = fields.Char(string='Shop Name')

    active = fields.Boolean()

    item_category_ids = fields.Many2many('mp.blibli.item.category', compute='_get_item_category_ids')
    brand_ids = fields.Many2many('mp.blibli.brand', compute='_get_brands')
    logistic_ids = fields.Many2many('mp.blibli.logistic', compute='_get_logistics')

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
    company_id = fields.Many2one(comodel_name="res.company", string="Company", required=False)


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
                    this.name or str('mp.blibli.' + str(this.id)))
            result.append((this.id, ' '.join(names)))
        return result


class MPBlibliCategory(models.Model):   
    _name = 'mp.blibli.item.category'
    _description = 'Blibli Item Category'
    _rec_name = 'complete_name'
    _order = 'path'

    category_id = fields.Char(readonly=True)
    
    complete_name = fields.Char()
    path = fields.Char()

    name_en = fields.Char()
    name_id = fields.Char()
    name = fields.Char()
    active = fields.Boolean(default=True)
    category_name = fields.Char(related='name')

    attributes = fields.Many2many('mp.blibli.item.category.attr','mp_blibli_item_category_attr_mp_blibli_item_category_rel')

    izi_id = fields.Integer('Izi ID')
    izi_md5 = fields.Char()

    @api.model
    def name_create(self, name):
        return self.create({'name': name}).name_get()[0]


class MPBlibliCategoryAttribute(models.Model):
    _name = 'mp.blibli.item.category.attr'
    _description = 'Blibli Item Category Attribute'


    attribute_id = fields.Char()
    name = fields.Char(string='Attribute Name')
    name_en = fields.Char()
    name_id = fields.Char()
    is_mandatory = fields.Boolean()
    special_attribute = fields.Boolean()
    variant_creating = fields.Boolean()
    attribute_type = fields.Char()

    categories = fields.Many2many('mp.blibli.item.category', 'mp_blibli_item_category_attr_mp_blibli_item_category_rel')
    options = fields.Many2many('mp.blibli.item.attr.option', 'mp_blibli_item_attr_option_mp_blibli_item_category_attr_rel')

    value_options = fields.Many2many('mp.blibli.variant.value')
    attribute_line_ids = fields.One2many('mp.blibli.attribute.line', 'attribute_id', 'Lines')

    izi_id = fields.Integer('Izi ID')
    izi_md5 = fields.Char()


class MPBlibliItemAttributeOption(models.Model):
    _name = 'mp.blibli.item.attr.option'
    _description = 'Blibli Item Category Attribute Option'
    
    name = fields.Char()
    attributes = fields.Many2many('mp.blibli.item.category.attr', 'mp_blibli_item_attr_option_mp_blibli_item_category_attr_rel')
    
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
        return super(MPBlibliItemAttributeOption, self).create(vals)


class MPBlibliBrand(models.Model):   
    _name = 'mp.blibli.brand'
    _description = 'Blibli Brand'

    name = fields.Char()
    brand_id = fields.Char()
    code = fields.Char()
    active = fields.Boolean()

    izi_id = fields.Integer('Izi ID')
    izi_md5 = fields.Char()



class MPBlibliItemAttributeVal(models.Model):
    _name = 'mp.blibli.item.attribute.val'
    _description = 'Blibli Item Attribute Value'
    _rec_name = 'attribute_id'
    
    name = fields.Char()
    item_id_staging = fields.Many2one('product.staging')
    attribute_id = fields.Many2one('mp.blibli.item.category.attr')
    attribute_value = fields.Char()
    is_mandatory = fields.Boolean(compute='_compute_attribute',readonly=1)
    values = fields.Many2many('mp.blibli.item.attr.option', compute='_compute_attribute')
    attribute_value_id = fields.Many2one('mp.blibli.item.attr.option', domain="[('id','in',values)]")
    
    izi_id = fields.Integer('Izi ID')
    izi_md5 = fields.Char()

    @api.model
    def create(self, vals):
        if vals.get('item_id_staging') and vals.get('attribute_id') and vals.get('attribute_value'):
            res = self.search([
                ('item_id_staging', '=', vals.get('item_id_staging')),
                ('attribute_id', '=', vals.get('attribute_id')),
            ], limit=1)
            if res:
                print(res)
                print(vals)
                res.write({'attribute_value': vals.get('attribute_value')})
                return res
        return super(MPBlibliItemAttributeVal, self).create(vals)

    def write(self, vals):
        if not self.env.context.get('create_product_attr'):
            if vals.get('attribute_value'):
                option_id = vals.get('attribute_value')
                option_obj = self.env['mp.blibli.item.attr.option'].browse(option_id)
                if option_obj:
                    vals.update({
                        'attribute_value': option_obj.display_name
                    })
        res = super(MPBlibliItemAttributeVal, self).write(vals)
        return res
    
    @api.depends('attribute_id')
    def _compute_attribute(self):
        for rec in self:
            if rec.attribute_id:
                rec.is_mandatory = rec.attribute_id.is_mandatory
                rec.values = rec.attribute_id.options.ids
            else:
                rec.is_mandatory = False
                rec.values = []

    _sql_constraints = [
        ('attribute_unique', 'unique(item_id_staging, attribute_id)', 'Attribute Already Exist.')
    ]

class MPBlibliLogistic(models.Model):   
    _name = 'mp.blibli.logistic'
    _description = 'Blibli Logistic'

    name = fields.Char()
    selected = fields.Boolean()
    code = fields.Char()
    geolocation = fields.Boolean()
    info_additional = fields.Char()
    info_highlight = fields.Char()

    izi_id = fields.Integer('Izi ID')
    izi_md5 = fields.Char()


class MPBlibliAttributeLine(models.Model):
    _name = 'mp.blibli.attribute.line'

    product_staging_id = fields.Many2one('product.staging')
    attribute_id = fields.Many2one('mp.blibli.item.category.attr')
    bli_variant_value_ids = fields.Many2many('mp.blibli.variant.value')

    izi_id = fields.Integer('Izi ID')
    izi_md5 = fields.Char()


class MPBlibliVariantValue(models.Model):

    _name = 'mp.blibli.variant.value'

    name = fields.Char('Value')
    is_master_data = fields.Boolean(default=False)
    product_staging_variant_ids = fields.Many2many('product.staging.variant')
    bli_attribute_line_ids = fields.Many2many('mp.blibli.attribute.line')

    izi_id = fields.Integer('Izi ID')
    izi_md5 = fields.Char()
