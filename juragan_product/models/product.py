# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.modules import get_resource_path
from odoo.tools import file_open

import json
import hashlib
import logging
import requests
from base64 import b64encode
from odoo.exceptions import UserError, ValidationError
from odoo.addons import decimal_precision as dp
from odoo.addons.juragan_webhook import BigInteger, BigMany2one

_logger = logging.getLogger(__name__)


class ProductMapping(models.Model):
    _name = 'product.mapping'

    product_product_izi_id = fields.Integer()
    product_template_izi_id = fields.Integer()
    reference = fields.Char()
    name = fields.Char()
    default_code = fields.Char()
    product_id = fields.Many2one('product.product', 'Product')
    order_product_id = fields.Many2one('product.product', 'Product in Order')
    server_id = fields.Many2one('webhook.server', 'Server')


    _sql_constraints = [
        ('product_unique', 'unique(product_id, server_id)', 'You cannot select same products on product mapping.')
    ]

class WarehouseMapping(models.Model):
    _name = 'warehouse.mapping'

    warehouse_izi_id = fields.Integer()
    reference = fields.Char()
    name = fields.Char()
    code = fields.Char()
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse')
    server_id = fields.Many2one('webhook.server', 'Server')

class LocationMapping(models.Model):
    _name = 'location.mapping'

    location_izi_id = fields.Integer()
    reference = fields.Char()
    name = fields.Char()
    barcode = fields.Char()
    location_id = fields.Many2one('stock.location', 'Location')
    server_id = fields.Many2one('webhook.server', 'Server')

class CategoryMapping(models.Model):
    _name = 'product.category.mapping'

    product_category_izi_id = fields.Integer()
    reference = fields.Char()
    name = fields.Char()
    category_id = fields.Many2one('product.category', 'Product Category')
    server_id = fields.Many2one('webhook.server', 'Server')


class CompanyMapping(models.Model):
    _name = 'company.mapping'

    company_izi_id = fields.Integer()
    reference = fields.Char()
    name = fields.Char()
    company_id = fields.Many2one('res.company', 'Company')
    server_id = fields.Many2one('webhook.server', 'Server')


class ProductTemplate(models.Model):
    _name = 'product.template'
    _inherit = ['product.template']

    _sql_constraints = [
        ('izi_unique', 'unique(izi_id)', 'Product with izi_id has already'),
    ]

    brand_id = fields.Many2one(
        comodel_name='product.brand',
        string='Merek'
    )
    length = fields.Float('Length')
    width = fields.Float('Width')
    height = fields.Float('Height')
    package_content = fields.Text('Package Content')
    # tax_id = fields.Float('Tax')
    product_staging_ids = fields.One2many(
        'product.staging', 'product_template_id', 'Product Marketplace',
        domain=['|', ('active', '=', False), ('active', '=', True), ],
        context={'active_test': False})
    product_status = fields.Selection([
        ('new', 'New'),
        ('draft', 'Draft'),
        ('online', 'Online')
    ], 'Product Status', default='new', store=True)
    product_image_ids = fields.One2many(
        'product.image', 'product_tmpl_id', string='Images')
    mp_tokopedia_ids = fields.Many2many(
        'mp.tokopedia', string='Tokopedia Account',
        domain=['|', ('active', '=', False), ('active', '=', True), ],
        context={'active_test': False})
    mp_tokopedia_icon = fields.Binary(string="Tokopedia Icon") #, compute="_compute_mp_icon"
    mp_shopee_ids = fields.Many2many(
        'mp.shopee', string='Shopee Account',
        domain=['|', ('active', '=', False), ('active', '=', True), ],
        context={'active_test': False})
    mp_shopee_icon = fields.Binary(string="Shopee Icon") #, compute="_compute_mp_icon"
    mp_lazada_ids = fields.Many2many(
        'mp.lazada', string='Lazada Account',
        domain=['|', ('active', '=', False), ('active', '=', True), ],
        context={'active_test': False})
    mp_lazada_icon = fields.Binary(string="Lazada Icon") #, compute="_compute_mp_icon"
    field_adapter_type = fields.Selection(
        [('consu', 'Consumable'),
         ('service', 'Service'), ('product', 'Stockable Product')],
        'Product Type Adapter', compute='set_type_adapter')
    mp_blibli_ids = fields.Many2many(
        'mp.blibli', string='Blibli Account',
        domain=['|', ('active', '=', False), ('active', '=', True), ],
        context={'active_test': False})
    mp_blibli_icon = fields.Binary(string="Blibli Icon") #, compute="_compute_mp_icon"
    product_wholesale_ids = fields.One2many(
        'product.template.wholesale', 'product_tmpl_id')
    default_code = fields.Char('Internal Reference')
    condition = fields.Selection([
        ('1', 'NEW'),
        ('2', 'USED')
    ], string="Condition")
    min_order = fields.Integer('Mininum Order')

    image_url = fields.Char('Image URL', compute='_get_image_url')
    image_url_external = fields.Char('Image URL External')

    @api.model
    def create(self, vals_list):
        templates = super(ProductTemplate, self).create(vals_list)
        if 'izi_id' in self._fields:
            if (not templates.izi_id or templates.izi_id == 0) and templates.id:
                self._cr.execute('UPDATE %s SET izi_id = NULL WHERE id = %s' % (self._table, templates.id))
        return templates

    def write(self, vals):
        res = super(ProductTemplate, self).write(vals)
        if 'izi_id' in self._fields:
            if not self.izi_id or self.izi_id == 0:
                self._cr.execute('UPDATE %s SET izi_id = NULL WHERE id = %s' % (self._table, self.id))
        return res

    def _get_image_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for rec in self:
            if rec.image:
                rec.image_url = '%s/jpg/product.template/image/%s.jpg' % (
                    base_url, str(rec.id))
            elif rec.image_url_external:
                rec.image_url = rec.image_url_external
            else:
                rec.image_url = False

    izi_id = fields.Integer('Izi ID', copy=False)
    izi_md5 = fields.Char()

    @api.depends('product_staging_ids')
    def _compute_mp_icon(self):
        def get_icon(mp, ext):
            icon_path = get_resource_path('juragan_product', 'static/src/img/%s.%s' % (mp, ext))
            return b64encode(file_open(icon_path, 'rb').read())

        mp_type = {
            'Tokopedia': 'tp',
            'Shopee': 'shp',
            'Lazada': 'lz'
        }

        icon_fields_and_ext = {
            'tp': ('mp_tokopedia_icon', 'png'),
            'shp': ('mp_shopee_icon', 'png'),
            'lz': ('mp_lazada_icon', 'png')
        }

        for product_tmpl in self:
            available_mp = product_tmpl.product_staging_ids.mapped('mp_type')
            for avail_mp in available_mp:
                if avail_mp not in mp_type.keys():
                    continue
                icon_field = icon_fields_and_ext[mp_type[avail_mp]][0]
                icon = get_icon(mp_type[avail_mp], icon_fields_and_ext[mp_type[avail_mp]][1])
                setattr(product_tmpl, icon_field, icon)

    @api.depends('type')
    def set_type_adapter(self):
        for obj in self:
            if obj.type:
                obj.field_adapter_type = obj.type

    def upload_self(self):
        for obj in self:
            server = self.env['webhook.server'].search(
                [('active', 'in', [False, True])],
                limit=1, order='write_date desc')
            if not server:
                raise UserError('Create at least 1 webhook server')
            uploaded = server.upload_products(obj._name, obj.id)
            if uploaded[0]:
                obj.message_post(body=uploaded[1], subject=_("Upload to IZI"))
            else:
                raise ValidationError(uploaded[1])

    def upload_product_tmpl_izi(self):
        response_fields_from_izi = ['product_image_ids', 'product_wholesale_ids']
        for product_tmpl_id in self:
            server = self.env['webhook.server'].search(
                [('active', 'in', [False, True])], limit=1, order='write_date desc')
            if not server:
                raise UserError('Create at least 1 webhook server')

            json_data = {
                "id": product_tmpl_id.id,
                "active": product_tmpl_id.active,
                "name": product_tmpl_id.name,
                "description_sale": product_tmpl_id.description_sale,
                "default_code": product_tmpl_id.default_code,
                "barcode": product_tmpl_id.barcode,
                "min_order": product_tmpl_id.min_order,
                "list_price": product_tmpl_id.list_price,
                "weight": product_tmpl_id.weight,
                "length": product_tmpl_id.length,
                "height": product_tmpl_id.height,
                "width": product_tmpl_id.width,
                "condition": product_tmpl_id.condition,
                "package_content": product_tmpl_id.package_content,
                "type": 'product'
            }

            mp_tokopedia_ids = []
            for mp_tokopedia in product_tmpl_id.mp_tokopedia_ids:
                mp_tokopedia_ids.append({'id': mp_tokopedia.izi_id})
            json_data.update({
                'mp_tokopedia_ids': mp_tokopedia_ids
            })

            mp_shopee_ids = []
            for mp_shopee in product_tmpl_id.mp_shopee_ids:
                mp_shopee_ids.append({'id': mp_shopee.izi_id})
            json_data.update({
                'mp_shopee_ids': mp_shopee_ids
            })    

            mp_lazada_ids = []
            for mp_lazada in product_tmpl_id.mp_lazada_ids:
                mp_lazada_ids.append({'id': mp_lazada.izi_id})
            json_data.update({
                'mp_lazada_ids': mp_lazada_ids
            })

            mp_blibli_ids = []
            for mp_blibli in product_tmpl_id.mp_blibli_ids:
                mp_blibli_ids.append({'id': mp_blibli.izi_id})
            json_data.update({
                'mp_blibli_ids': mp_blibli_ids
            })

            images = []
            for image in product_tmpl_id.product_image_ids:
                images.append({
                    'src':  'data:image;base64,' + image.image.decode('utf-8') if image.image else image.url,
                    'name': image.name,
                    'url_external': image.url_external,
                    'id': image.izi_id
                })
            json_data.update({
                'file_image': images
            })

            wholesales = []
            for wholesale in product_tmpl_id.product_wholesale_ids:
                wholesales.append({
                    'id': wholesale.izi_id,
                    'min_qty': wholesale.min_qty,
                    'max_qty': wholesale.max_qty,
                    'price_wholesale': wholesale.price_wholesale,
                })
            json_data.update({
                'wholesale': wholesales
            })

            jsondata = server.get_updated_izi_id(product_tmpl_id, json_data)

            if product_tmpl_id.izi_id:
                url = '{}/external/api/ui/update/product.template/{}'.format(
                    server.name, product_tmpl_id.izi_id)
                jsondata['record_was_exist'] = product_tmpl_id.izi_id
            else:
                url = '{}/external/api/ui/create/product.template'.format(
                    server.name)
            try:
                req = requests.post(
                    url,
                    headers={'X-Openerp-Session-Id': server.session_id},
                    json=json_data)
                if req.status_code == 200:
                    response = req.json()
                    if response.get('code') == 200:
                        response_data = response.get('data')
                        product_tmpl_id.izi_id = response_data.get('id')
                        product_tmpl_id.product_variant_id.izi_id = response_data.get('product_variant_id')[0]
                        for response_key in response_data:
                            if response_key in response_fields_from_izi:
                                existing_data_ids = product_tmpl_id[response_key]
                                domain_url = "[('id', 'in', %s)]" % str(
                                    response_data.get(response_key))
                                server.get_records(
                                    product_tmpl_id[response_key]._name, domain_url=domain_url, force_update=True)
                                for model_data_response in existing_data_ids:
                                    if model_data_response.izi_id not in response_data.get(response_key):
                                        if model_data_response._fields.get('active') != None:
                                            if not model_data_response._fields.get('active').related:
                                                model_data_response.active = False
                                            else:
                                                model_data_response.unlink()
                                        else:
                                            model_data_response.unlink()
                    else:
                        if response.get('data').get('error_descrip') != None:
                            raise UserError(response.get(
                                'data').get('error_descrip'))
                        else:
                            raise UserError(
                                "Error from IZI. Failed Upload to IZI")
            except Exception as e:
                raise UserError(str(e))

    def mapping_master_fields(self):
        form_view = self.env.ref('juragan_product.mapping_master_fields_form')
        return {
            'name': 'Mapping Master Fields to Stagings',
            'view_mode': 'form',
            'res_model': 'mapping.master.wizard',
            'view_id': form_view.id,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {
                'product_tmpl_id': self.id,
                'default_name': self.name,
                'default_default_code': self.default_code,
                'default_description_sale': self.description_sale,
                'default_list_price': self.list_price,
                'default_qty_available': self.qty_available,
                'default_min_order': self.min_order,
                'default_weight': self.weight,
                'default_length': self.length,
                'default_width': self.width,
                'default_height': self.height,
            },
        }


class ProductProduct(models.Model):
    _inherit = 'product.product'

    price_custom = fields.Float('Price Custom')
    product_variant_stg_ids = fields.One2many(
        'product.staging.variant', 'product_id', 'Product Variant Staging')
    
     # image: all image fields are base64 encoded and PIL-supported
    image = fields.Binary("Image", attachment=True)
    image_url = fields.Char('Image URL', compute='_get_image_url')
    image_url_external = fields.Char('Image URL External')

    attribute_value_ids = fields.Many2many(
        'product.template.attribute.value',
        string="Attribute Values",
        compute='_get_attribute_value_ids',
        inverse='_set_attribute_value_ids',
        search=lambda s, o, v:[('product_template_attribute_value_ids', o, v)]
    )

    izi_id = fields.Integer('Izi ID', copy=False)
    izi_md5 = fields.Char()

    product_staging_ids = fields.Many2many('product.staging')

    def init(self):     
        self.env.cr.execute("DROP INDEX IF EXISTS product_product_combination_unique")

    def _get_image_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for rec in self:
            if rec.image:
                rec.image_url = '%s/jpg/product.product/image/%s.jpg' % (
                    base_url, str(rec.id))
            elif rec.image_url_external:
                rec.image_url = rec.image_url_external
            else:
                rec.image_url = False

    @api.depends('product_template_attribute_value_ids')
    def _get_attribute_value_ids(self):
        for rec in self:
            rec.attribute_value_ids = rec.product_template_attribute_value_ids

    def _set_attribute_value_ids(self):
        self.product_template_attribute_value_ids = [(6, 0, self.attribute_value_ids.ids)]

    def upload_self(self):
        self.ensure_one()
        self.product_tmpl_id.upload_self()
        # for obj in self:
        #     server = self.env['webhook.server'].search(
        #         [('active', 'in', [False, True])],
        #         limit=1, order='write_date desc')
        #     if not server:
        #         raise UserError('Buatkan minimal 1 webhook server!')
        #     uploaded = server.upload_products(obj._name, obj.id)
        #     if uploaded[0]:
        #         obj.message_post(body=uploaded[1], subject=_("Upload to IZI"))
        #     else:
        #         raise ValidationError(uploaded[1])

    @api.depends('product_template_attribute_value_ids')
    def _compute_combination_indices(self):
        for product in self:
            combination_indices = product.product_template_attribute_value_ids._ids2str()
            product.combination_indices = None if combination_indices == '' else combination_indices


class ProductImage(models.Model):
    _name = 'product.image'
    _description = 'Product Image [duplicate website_sale]'

    name = fields.Char()
    image = fields.Binary("Image", attachment=True)
    product_tmpl_id = fields.Many2one('product.template', 'Related Product')
    url_external = fields.Char('URL External')
    url = fields.Char('URL', compute='_get_image_url')
    active = fields.Boolean(related='product_tmpl_id.active')

    izi_id = fields.Integer('Izi ID')
    izi_md5 = fields.Char()

    def _get_image_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for rec in self:
            if rec.image:
                rec.url = '%s/jpg/product.image/image/%s.jpg' % (
                    base_url, str(rec.id))
            elif rec.url_external:
                rec.url = rec.url_external
            else:
                rec.url = False


class ProductImageStaging(models.Model):
    _name = 'product.image.staging'

    name = fields.Char('Name')
    image = fields.Binary('Image', attachment=True)
    product_stg_id = fields.Many2one('product.staging')
    url_external = fields.Char('URL External')
    url = fields.Char('URL', compute='_get_image_url')
    active = fields.Boolean(related='product_stg_id.active')

    sp_image_id = fields.Char()

    izi_id = fields.Integer('Izi ID', copy=False)
    izi_md5 = fields.Char()

    def _get_image_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for rec in self:
            if rec.image:
                rec.url = '%s/jpg/product.image.staging/image/%s.jpg' % (
                    base_url, str(rec.id))
            elif rec.url_external:
                rec.url = rec.url_external
            else:
                rec.url = False

class ProductCategory(models.Model):
    _inherit = 'product.category'

    mp_tokopedia_category_id = fields.Many2one(
        'mp.tokopedia.category', string='Tokopedia Category')
    attribute_ids = fields.One2many(
        'product.attribute', 'product_category_id')

    izi_id = fields.Integer('Izi ID', copy=False)
    izi_md5 = fields.Char()


class ProductAttribute(models.Model):
    _inherit = 'product.attribute'

    product_category_id = fields.Many2one('product.category')
    mp_tokopedia_category_variant_id = fields.Many2one(
        'mp.tokopedia.category.variant',
        string='Tokopedia Category Variant')
    unit_ids = fields.One2many('product.attribute.unit', 'attribute_id')

    izi_id = fields.Integer('Izi ID', copy=False)
    izi_md5 = fields.Char()


class ProductAttributeValue(models.Model):
    _inherit = 'product.attribute.value'

    unit_id = fields.Many2one('product.attribute.unit')
    mp_tokopedia_category_value_id = fields.Many2one(
        'mp.tokopedia.category.value', string='Tokopedia Category Value')

    izi_id = fields.Integer('Izi ID', copy=False)
    izi_md5 = fields.Char()


class UomUom(models.Model):
    _inherit = 'uom.uom'

    izi_id = fields.Integer('Izi ID')
    izi_md5 = fields.Char()


class ProductTemplateAttributeLine(models.Model):
    _inherit = 'product.template.attribute.line'

    izi_id = fields.Integer('Izi ID')
    izi_md5 = fields.Char()


class ProductWholesale(models.Model):
    _name = 'product.template.wholesale'

    product_tmpl_id = fields.Many2one('product.template', ondelete='cascade')

    min_qty = fields.Integer('Minimum Quantity')
    max_qty = fields.Integer('Maximum Quantity')
    price_wholesale = fields.Float('Wholesale Price')

    izi_id = fields.Integer('Izi ID')
    izi_md5 = fields.Char()


class ProductStagingWholesale(models.Model):
    _name = 'product.staging.wholesale'

    product_stg_id = fields.Many2one('product.staging', ondelete='cascade')

    min_qty = fields.Integer('Minimum Quantity')
    max_qty = fields.Integer('Maximum Quantity')
    price_wholesale = fields.Float('Wholesale Price')

    izi_id = fields.Integer('Izi ID')
    izi_md5 = fields.Char()


class BatchUploadWizard(models.TransientModel):
    _name = 'batch.upload.product.wizard'

    marketplace = fields.Selection([
        ('tokopedia', 'Tokopedia'),
        ('shopee', 'Shopee'),
        ('lazada', 'Lazada')
    ], string='Marketplace')

    is_replace_fields = fields.Boolean(string='Is replace fields?')

    is_description_sale = fields.Boolean()
    is_list_price = fields.Boolean()
    is_weight = fields.Boolean()
    is_length = fields.Boolean()
    is_width = fields.Boolean()
    is_height = fields.Boolean()
    is_qty_available = fields.Boolean()
    is_min_order = fields.Boolean()
    is_image = fields.Boolean()
    is_is_active = fields.Boolean()

    is_tp_category_id = fields.Boolean()
    is_tp_etalase_id = fields.Boolean()
    is_tp_available_status = fields.Boolean()
    is_tp_active_status = fields.Boolean()
    is_tp_condition = fields.Boolean()
    is_tp_weight_unit = fields.Boolean()
    is_tp_is_must_insurance = fields.Boolean()
    is_tp_is_free_return = fields.Boolean()
    is_tp_preorder = fields.Boolean()
    is_tp_preorder_duration = fields.Boolean()
    is_tp_preorder_time_unit = fields.Boolean()

    is_sp_condition = fields.Boolean()
    is_sp_is_pre_order = fields.Boolean()
    is_sp_days_to_ship = fields.Boolean()
    is_sp_category_id = fields.Boolean()
    is_sp_logistics = fields.Boolean()
    is_sp_attributes = fields.Boolean()
    is_sp_brand_id = fields.Boolean()
    
    is_lz_category_id = fields.Boolean()
    is_lz_brand_id = fields.Boolean()
    is_lz_attributes = fields.Boolean()
    is_lz_status = fields.Boolean()


    description_sale = fields.Text('Description')
    list_price = fields.Float(
        'Sales Price', digits=dp.get_precision('Product Price'))
    weight = fields.Float('Weight')
    length = fields.Float('Length')
    width = fields.Float('Width')
    height = fields.Float('Height')
    is_active = fields.Boolean('Active')
    qty_available = fields.Integer('Qty Available')
    min_order = fields.Integer('Min Order')
    batch_upload_image_ids = fields.One2many('batch.upload.image', 'batch_upload_id', string='Product Images')

    # Tokopedia Fields
    mp_tokopedia_id = fields.Many2one(
        'mp.tokopedia', string='Tokopedia Account')
    tp_category_id = fields.Many2one(
        'mp.tokopedia.category', string="Tokopedia Category")
    tp_etalase_id = fields.Many2one(
        'mp.tokopedia.etalase', string="Tokopedia Etalase")
    tp_available_status = fields.Selection([
        ('1', 'EMPTY'),
        ('2', 'LIMITED'),
        ('3', 'UNLIMITED')
    ], string='Availability', default='2')
    tp_active_status = fields.Selection([
        ('-2', 'Banned'),
        ('-1', 'Pending'),
        ('0', 'Deleted'),
        ('1', 'Active'),
        ('2', 'Best (Featured Product)'),
        ('3', 'Inactive (Warehouse)')
    ], string='Active Status')
    tp_condition = fields.Selection([
        ('1', 'NEW'),
        ('2', 'USED')
    ], string="Condition")
    tp_weight_unit = fields.Selection([
        ('1', 'Gr'),
        ('2', 'KG')
    ], string='Weight Unit')
    tp_is_must_insurance = fields.Boolean('Must Insurance', default=False)
    tp_is_free_return = fields.Boolean('Free Return Cost', default=False)
    tp_preorder = fields.Boolean('Pre-Order', default=False)
    tp_preorder_duration = fields.Integer('Pre-Order Duration')
    tp_preorder_time_unit = fields.Selection([
        ('1', 'DAY'),
        ('2', 'WEEK'),
    ], string='Pre-Order Time Unit')

    # Shopee Fields
    mp_shopee_id = fields.Many2one('mp.shopee', string='Shopee Account')
    sp_condition = fields.Selection(
        [('NEW', 'NEW'), ('USED', 'USED')], 'Condition')
    sp_is_pre_order = fields.Boolean('Pre Order')
    sp_days_to_ship = fields.Integer(default=2)
    sp_category_id = BigMany2one('mp.shopee.item.category',string='Shopee Category')
    # sp_category_int = BigInteger()
    sp_logistics = fields.One2many(
        'mp.shopee.item.logistic.wizard', 'item_id_staging_wizard')
    sp_attributes = fields.One2many(
        'mp.shopee.item.attribute.val.wizard', 'item_id_staging_wizard')
    sp_brand_id =  fields.Many2one('mp.shopee.item.brand', string='Shopee Brand', domain="[('categories', 'child_of', sp_category_id)])")
    # Lazada Fields
    mp_lazada_id = fields.Many2one('mp.lazada', string='Lazada Account')
    lz_category_id =  fields.Many2one('mp.lazada.category', string='Product Category')
    lz_brand_id =  fields.Many2one('mp.lazada.brand', string='Product Brand')
    lz_attributes = fields.One2many('mp.lazada.product.attr.wizard', 'item_id_staging_wizard', string='Attributes Category')
    lz_status = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('deleted', 'Deleted')
    ])
    lz_sku_id = fields.Char()

    def batch_upload(self):
        upload_status = []
        active_ids = self._context.get('active_ids', []) or []
        for product_tmpl_id in self.env['product.template'].browse(active_ids):
            try:
                if self.mp_tokopedia_id:
                    product_tmpl_id.mp_tokopedia_ids = [(4, self.mp_tokopedia_id.id)]
                if self.mp_shopee_id:
                    product_tmpl_id.mp_shopee_ids = [(4, self.mp_shopee_id.id)]
                if self.mp_lazada_id:
                    product_tmpl_id.mp_lazada_ids = [(4, self.mp_lazada_id.id)]
                
                # process images
                images = []
                if self.batch_upload_image_ids:
                    for pic in self.batch_upload_image_ids:
                        images.append((0, 0, {
                            'image': pic.image,
                        }))

                # process lz_attributes
                lz_attributes = []
                if self.lz_attributes:
                    for att in self.lz_attributes:
                        lz_attributes.append((0, 0, {
                            'name': att.attribute_id.name,
                            'value': att.option_id.name,
                            'attribute_id': att.attribute_id.id,
                            'option_id': att.option_id.id,
                        }))

                # process sp_attributes
                sp_attributes = []
                if self.sp_attributes:
                    for att in self.sp_attributes:
                        sp_attributes.append((0, 0, {
                            'attribute_value': att.value.display_name if att.value else '',
                            'attribute_id': att.attribute_id.id,
                        }))

                # process sp_logistics
                sp_logistics = []
                if self.sp_logistics:
                    for logistic in self.sp_logistics:
                        sp_logistics.append((0, 0, {
                            "logistic_id": logistic.logistic_id.id,
                            "estimated_shipping_fee": logistic.estimated_shipping_fee,
                            "is_free": logistic.is_free,
                            "enabled": logistic.enabled,
                        }))

                default_loc = self.env['stock.inventory']._default_location_id()
                stock_location = self.env['stock.location'].browse(default_loc)
                if self.mp_tokopedia_id:
                    stock_location = self.mp_tokopedia_id.wh_id.lot_stock_id
                    if not stock_location:
                        stock_location = product_tmpl_id.mp_tokopedia_ids.wh_id.lot_stock_id
                elif self.mp_shopee_id:
                    stock_location = self.mp_shopee_id.wh_id.lot_stock_id
                    if not stock_location:
                        stock_location = product_tmpl_id.mp_shopee_ids.wh_id.lot_stock_id
                elif self.mp_lazada_id:
                    stock_location = self.mp_lazada_id.wh_id.lot_stock_id
                    if not stock_location:
                        stock_location = product_tmpl_id.mp_lazada_ids.wh_id.lot_stock_id

                # check if staging with given account is exist
                is_staging_exist = False
                product_staging_id = False
                for product_staging in product_tmpl_id.product_staging_ids:
                    if self.mp_tokopedia_id:
                        if self.mp_tokopedia_id.id == product_staging.mp_tokopedia_id.id:
                            is_staging_exist = True
                            product_staging_id = product_staging
                    elif self.mp_shopee_id:
                        if self.mp_shopee_id.id == product_staging.mp_shopee_id.id:
                            is_staging_exist = True
                            product_staging_id = product_staging
                    elif self.mp_lazada_id:
                        if self.mp_lazada_id.id == product_staging.mp_lazada_id.id:
                            is_staging_exist = True
                            product_staging_id = product_staging
                if not is_staging_exist:
                    values = {
                        'product_template_id': product_tmpl_id.id,
                        'name': product_tmpl_id.name,
                        'description_sale': self.description_sale,
                        'is_active': self.is_active,
                        'list_price': self.list_price,
                        'min_order': self.min_order,
                        'length': self.length,
                        'width': self.width,
                        'height': self.height,
                        'product_image_staging_ids': images,
                    }

                    if self.mp_tokopedia_id:
                        # Tokopedia Fields
                        values.update({
                            'weight': self.weight,
                            'default_code': product_tmpl_id.default_code,
                            'mp_tokopedia_id': self.mp_tokopedia_id.id,
                            'tp_active_status': 1 if self.is_active else 3,
                            'tp_available_status': self.tp_available_status,
                            'tp_category_id': self.tp_category_id.id,
                            'tp_condition': self.tp_condition,
                            'tp_weight_unit': self.tp_weight_unit,
                        })

                    elif self.mp_lazada_id:
                        # Lazada Fields
                        default_code = product_tmpl_id.name.lower().replace(' ', '-')
                        values.update({
                            'weight': self.weight,
                            'mp_lazada_id': self.mp_lazada_id.id,
                            'default_code': default_code,
                            'lz_category_id': self.lz_category_id.id,
                            'lz_brand_id': self.lz_brand_id.id,
                            'lz_attributes': lz_attributes,
                        })
                    
                    elif self.mp_shopee_id:
                        # Shopee Fields
                        values.update({
                            'weight': self.weight,
                            'mp_shopee_id': self.mp_shopee_id.id,
                            'sp_category_id': self.sp_category_id.id,
                            'default_code': product_tmpl_id.default_code,
                            'sp_condition': self.sp_condition,
                            'sp_is_pre_order': self.sp_is_pre_order,
                            'sp_days_to_ship': self.sp_days_to_ship,
                            'sp_brand_id': self.sp_brand_id.id,
                            'sp_attributes': sp_attributes,
                            'sp_logistics': sp_logistics,
                        })
                    
                    product_staging_id = self.env['product.staging'].create(values)

                    product_id = product_tmpl_id.product_variant_id.id
                    stock_inventory = self.env['stock.inventory'].create({
                        'name': product_tmpl_id.product_variant_id.display_name,
                        'location_id': stock_location.id,
                        'product_id': product_id,
                        'filter': 'product',
                        'line_ids': [(0, 0, {
                            'product_id': product_id,
                            'location_id': stock_location.id,
                            'product_qty': self.qty_available,
                        })]
                    })
                    try:
                        stock_inventory.action_start()
                        stock_inventory.action_validate()
                    except Exception as e:
                        stock_inventory.unlink()
                        raise UserError(str(e))
                else:
                    if self.mp_shopee_id or self.mp_lazada_id:
                        # validation
                        if self.list_price == 0 and self.is_list_price:
                            raise UserError('Price must be higher than 0')
                        if self.weight == 0 and self.is_weight:
                            raise UserError('Weight must be higher than 0')
                        if self.length == 0 and self.is_length:
                            raise UserError('Length must be higher than 0')
                        if self.width == 0 and self.is_width:
                            raise UserError('Width must be higher than 0')
                        if self.height == 0 and self.is_height:
                            raise UserError('Height must be higher than 0')

                    values = {
                        'description_sale': self.set_value_is_replace(self.is_description_sale,product_staging_id.description_sale, self.description_sale),
                        'is_active': self.set_value_is_replace(self.is_is_active, product_staging_id.is_active, self.is_active),
                        'list_price': self.set_value_is_replace(self.is_list_price, product_staging_id.list_price, self.list_price),
                        'min_order': self.set_value_is_replace(self.is_min_order, product_staging_id.min_order, self.min_order),
                        'weight': self.set_value_is_replace(self.is_weight, product_staging_id.weight, self.weight),
                        'length': self.set_value_is_replace(self.is_length, product_staging_id.length, self.length),
                        'width': self.set_value_is_replace(self.is_width, product_staging_id.width, self.width),
                        'height': self.set_value_is_replace(self.is_height, product_staging_id.height, self.height),
                    }

                    if product_staging_id.mp_tokopedia_id:
                        # Tokopedia Fields
                        values.update({
                            'tp_active_status': self.set_value_is_replace(self.is_tp_active_status, product_staging_id.tp_active_status, 1 if self.is_active else 3),
                            'tp_available_status': self.set_value_is_replace(self.tp_available_status, product_staging_id.tp_available_status, self.tp_available_status),
                            'tp_category_id': self.set_value_is_replace(self.tp_category_id, product_staging_id.tp_category_id.id, self.tp_category_id.id),
                            'tp_condition': self.set_value_is_replace(self.tp_condition, product_staging_id.tp_condition, self.tp_condition),
                            'tp_weight_unit': self.set_value_is_replace(self.tp_weight_unit, product_staging_id.tp_weight_unit, self.tp_weight_unit),
                        })
                    
                    elif product_staging_id.mp_lazada_id:
                        # Lazada Fields
                        default_code = product_staging_id.default_code
                        if not default_code or default_code == '':
                            default_code = product_staging_id.name.lower().replace(' ', '-')
                        values.update({
                            'default_code': default_code,
                            'lz_category_id': self.set_value_is_replace(self.is_lz_category_id, product_staging_id.lz_category_id.id, self.lz_category_id.id),
                            'lz_brand_id': self.set_value_is_replace(self.lz_brand_id, product_staging_id.lz_brand_id.id, self.lz_brand_id.id),
                        })

                        if self.is_lz_attributes or not product_staging_id.lz_attributes:
                            # process lz_attributes
                            for lz_attr in product_staging_id.lz_attributes:
                                lz_attr.unlink()
                            product_staging_id.write({
                                'lz_attributes': lz_attributes
                            })

                    elif product_staging_id.mp_shopee_id:
                        # Shopee Fields
                        values.update({
                            'default_code': product_tmpl_id.default_code,
                            'sp_category_id': self.set_value_is_replace(self.is_sp_category_id, product_staging_id.sp_category_id.id, self.sp_category_id.id),
                            'sp_brand_id': self.set_value_is_replace(self.is_sp_brand_id, product_staging_id.sp_brand_id.id, self.sp_brand_id.id),
                            'sp_condition': self.set_value_is_replace(self.is_sp_condition, product_staging_id.sp_condition, self.sp_condition),
                            'sp_is_pre_order': self.set_value_is_replace(self.is_sp_is_pre_order, product_staging_id.sp_is_pre_order, self.sp_is_pre_order),
                            'sp_days_to_ship': self.set_value_is_replace(self.is_sp_days_to_ship, product_staging_id.sp_days_to_ship, self.sp_days_to_ship),
                        })

                        if self.is_sp_attributes or not product_staging_id.sp_attributes:
                            # process sp_attributes
                            for sp_attr in product_staging_id.sp_attributes:
                                sp_attr.unlink()
                            product_staging_id.write({
                                'sp_attributes': sp_attributes
                            })
                        if self.is_sp_logistics or not product_staging_id.sp_logistics:
                            # process sp_logistic
                            for sp_logistic in product_staging_id.sp_logistics:
                                sp_logistic.unlink()
                            product_staging_id.write({
                                'sp_logistics': sp_logistics
                            })
                        

                    product_staging_id.write(values)

                    if self.is_image or not product_staging_id.product_image_staging_ids:
                        # process image stagings
                        for img_stg in product_staging_id.product_image_staging_ids:
                            img_stg.unlink()
                        product_staging_id.write({
                            'product_image_staging_ids': images
                        })

                    if self.is_qty_available or product_staging_id.qty_available == 0:
                        product_id = product_tmpl_id.product_variant_id.id
                        stock_inventory = self.env['stock.inventory'].create({
                            'name': product_tmpl_id.product_variant_id.display_name,
                            'location_id': stock_location.id,
                            'product_id': product_id,
                            'filter': 'product',
                            'line_ids': [(0, 0, {
                                'product_id': product_id,
                                'location_id': stock_location.id,
                                'product_qty': self.qty_available,
                            })]
                        })
                        try:
                            stock_inventory.action_start()
                            stock_inventory.action_validate()
                        except Exception as e:
                            stock_inventory.unlink()
                            raise UserError(str(e))

                if not product_tmpl_id.izi_id:
                    product_tmpl_id.upload_product_tmpl_izi()
                upload_staging = product_staging_id.with_context(batch_upload=True).upload_product_stg_izi()
                upload_status.append(upload_staging)
            except Exception as e:
                upload_status.append({
                    'product': 'Master Product : ' + product_tmpl_id.name,
                    'default_code': 'SKU Master : ' + product_tmpl_id.default_code,
                    'status': False,
                    'message': e.name if e else 'Failed to prepare staging data',
                })
        

        messages = ''
        for msg in upload_status:
            if msg['status']:
                status = 'Success'
                messages += 'Product with name %s (%s), upload %s \n' % (msg['product'], msg['default_code'], status)
            else:
                status = 'Failed'
                messages += 'Product with name %s (%s), upload %s, with message: %s\n' % (msg['product'], msg['default_code'], status, msg['message'])
            
      
        form_view = self.env.ref('juragan_product.popup_message_wizard')
        view_id = form_view and form_view.id or False
        context = dict(self._context or {})
        context['message'] = messages
        return {
            'name': 'Batch Upload Status.',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'popup.message.wizard',
            'views': [(view_id,'form')],
            'view_id' : form_view.id,
            'target': 'new',
            'context': context,
        }

    def get_webhook_server(self):
        server = self.env['webhook.server'].search([], limit=1)
        if not server:
            raise UserError('There is no webhook server.')
        return server

    def set_value_is_replace(self, object_field, exist_value, replace_value):
        if object_field or not exist_value:
            return replace_value
        else:
            return exist_value

    @api.onchange('lz_category_id')
    def _lz_change_category_id(self):
        if self.mp_lazada_id and self.lz_category_id:
            base_attribute = [
                'name','short_description','description','video','brand',
                'SellerSku','quantity','price','special_price','special_from_date',
                'special_to_date','package_content','package_weight','package_length','package_width','package_height',
                '__images__','name_en','package_contents_en','short_description_en','Delivery_Option_Instant','delivery_option_economy',
                'color_thumbnail','delivery_option_express','tax_class','description_en','color_family','flavor','size'
            ]
            try:
                mp_id_by_izi_id = self.mp_lazada_id.izi_id
                category_id = self.lz_category_id.izi_id
                server = self.get_webhook_server()
                if server:
                    if not self.lz_category_id.attr_ids:
                        res = server.lz_get_attribute_category(category_id,mp_id_by_izi_id)
                # self.mp_ids[0].get_item_category(category_ids=self.category_id.ids)
                self.lz_attributes = [(5, 0, 0), *[(0, 0, {
                    'attribute_id': attribute.id
                }) for attribute in self.lz_category_id.attr_ids if attribute.name not in base_attribute]]
                self.lz_attribute_line_ids = [(5, 0, 0), *[(0, 0, {
                    'attribute_id': attribute.id
                }) for attribute in self.lz_category_id.attr_ids if attribute.is_sale_prop == True]]
            except Exception as e:
                _logger.warn(e)

                
    
    @api.onchange('sp_category_id')
    def _sp_change_category_id(self):
        if self.mp_shopee_id and self.sp_category_id:
            try:
                mp_id_by_izi_id = self.mp_shopee_id.izi_id
                category_id = self.sp_category_id.izi_id
                server = self.get_webhook_server()
                if server:
                    if not self.sp_category_id.attributes:
                        res = server.sp_get_attribute_category(category_id,mp_id_by_izi_id)
                    if not self.sp_category_id.brands:
                        res = server.sp_get_attribute_brand(category_id,mp_id_by_izi_id)
                # self.mp_ids[0].get_item_category(category_ids=self.category_id.ids)
                self.sp_attributes = [(5, 0, 0), *[(0, 0, {
                    'attribute_id': attribute.id
                }) for attribute in self.sp_category_id.attributes]]
            except Exception as e:
                _logger.warn(e)

            if not self.sp_logistics:
                logistic_shop = self.env['mp.shopee.shop.logistic'].search([('mp_id','=',self.mp_shopee_id.id),('enabled','=',True),('is_parent','=',True)])
                self.sp_logistics = [(5, 0, 0), *[(0, 0, {
                            'logistic_id': logistic.logistic_id.id
                        }) for logistic in logistic_shop]]
    
class BatchUploadImage(models.TransientModel):
    _name = 'batch.upload.image'

    image = fields.Binary('Image', attachment=True)
    batch_upload_id = fields.Many2one('Batch Upload ID')

class WebhookServer(models.Model):
    _inherit = 'webhook.server'

    product_mapping_ids = fields.One2many('product.mapping', 'server_id', 'Product Mapping')
    category_mapping_ids = fields.One2many('product.category.mapping', 'server_id','Product Category Mapping')
    warehouse_mapping_ids = fields.One2many('warehouse.mapping', 'server_id', 'Warehouse Mapping')
    location_mapping_ids = fields.One2many('location.mapping', 'server_id', 'Location Mapping')
    company_mapping_ids = fields.One2many('company.mapping', 'server_id', 'Company Mapping')

    def delete_product_mapping(self):
        self.env.cr.execute('''
            DELETE FROM product_mapping;
        ''')

    def start_product_mapping(self):
        # GET existing 
        pm_by_izi_id = {}
        mapped_product_ids = []
        product_mappings = self.env['product.mapping'].sudo().search([])
        for pm in product_mappings:
            if pm.product_product_izi_id:
                pm_by_izi_id[pm.product_product_izi_id] = pm
            if pm.product_id:
                mapped_product_ids.append(pm.product_id.id)
        # GET existing product.product
        pp_by_name = {}
        pp_by_default_code = {}
        pp_by_izi_id = {}
        product_products = self.env['product.product'].sudo().search([])
        for pp in product_products:
            if pp.izi_id:
                pp_by_izi_id[pp.izi_id] = pp
            if pp.name:
                pp_by_name[pp.name] = pp
            if pp.default_code and len(pp.default_code) > 3:
                pp_by_default_code[pp.default_code] = pp
        
        loop = True
        offset = 0
        limit = 1000
        try:
            while loop:
                r = requests.get(self.name + '/api/ui/read/list-detail/izi-product-mapping?offset=%s&limit=%s' % (
                    str(offset), str(limit)),
                    headers={'X-Openerp-Session-Id': self.session_id}
                )
                res = r.json() if r.status_code == 200 else {}
                if res.get('code') == 200:
                    if len(res.get('data')) == 0:
                        loop = False
                    else:
                        offset += limit
                    # Create Product Mapping
                    for pd in res.get('data'):
                        # Skip Service
                        # if pd.get('type') and pd['type']['value'] == 'service':
                        #     continue
                        
                        # Search for product template that has same name or default code
                        product_product = False
                        if pd['id'] in pp_by_izi_id:
                            product_product = pp_by_izi_id[pd['id']]
                        if not product_product and pd['name'] in pp_by_name:
                            product_product = pp_by_name[pd['name']]
                        if not product_product and pd['default_code'] in pp_by_default_code:
                            product_product = pp_by_default_code[pd['default_code']]
                        # Create or Update
                        if pd['id'] not in pm_by_izi_id:
                            values = {
                                'product_product_izi_id': pd['id'],
                                'product_template_izi_id': pd['product_tmpl_id']['id'],
                                'reference': pd['display_name'],
                                'name': pd['name'],
                                'default_code': pd['default_code'],
                                'server_id': self.id,
                            }
                            # Check product_product
                            if product_product:
                                if product_product.id not in mapped_product_ids:
                                    mapped_product_ids.append(product_product.id)
                                    values['product_id'] = product_product.id
                            self.env['product.mapping'].sudo().create(values)
                        else:
                            values = {
                                'product_product_izi_id': pd['id'],
                                'product_template_izi_id': pd['product_tmpl_id']['id'],
                                'reference': pd['display_name'],
                                'name': pd['name'],
                                'default_code': pd['default_code'],
                                'server_id': self.id,
                            }
                            if not pm_by_izi_id[pd['id']].product_id and product_product:
                                if product_product.id not in mapped_product_ids:
                                    mapped_product_ids.append(product_product.id)
                                    values['product_id'] = product_product.id
                            pm_by_izi_id[pd['id']].write(values)

                            # pop product mapping, for checking data later
                            pm_by_izi_id.pop(pd['id'])
                else:
                    loop = False

            # after get data from izi, unlink product mapping that not match
            for product_mapping in pm_by_izi_id:
                pm_by_izi_id[product_mapping].unlink()

        except Exception as e:
            _logger.error(str(e))
    
    def start_warehouse_mapping(self):
        # GET existing
        wm_by_izi_id = {}
        warehouse_mappings = self.env['warehouse.mapping'].sudo().search([])
        for wm in warehouse_mappings:
            if wm.warehouse_izi_id:
                wm_by_izi_id[wm.warehouse_izi_id] = wm
        # GET existing warehouse
        wh_by_name = {}
        wh_by_code = {}
        warehouses = self.env['stock.warehouse'].sudo().search([])
        for wh in warehouses:
            if wh.name:
                wh_by_name[wh.name] = wh
            if wh.code:
                wh_by_code[wh.code] = wh

        loop = True
        offset = 0
        limit = 1000
        while loop:
            r = requests.get(self.name + '/api/ui/read/list-detail/stock.warehouse?domain_code=marketplace&offset=%s&limit=%s' % (
                str(offset), str(limit)),
                headers={'X-Openerp-Session-Id': self.session_id}
            )
            res = r.json() if r.status_code == 200 else {}
            if res.get('code') == 200:
                if len(res.get('data')) == 0:
                    loop = False
                else:
                    offset += limit
                # Create Warehouse Mapping
                for wh in res.get('data'):
                    # Search for warehouse that has same name or default code
                    same_warehouse = False
                    if wh['name'] in wh_by_name:
                        same_warehouse = wh_by_name[wh['name']]
                    if wh['code'] in wh_by_code:
                        same_warehouse = wh_by_code[wh['code']]
                    # Create or Update
                    if wh['id'] not in wm_by_izi_id:
                        values = {
                            'warehouse_izi_id': wh['id'],
                            'reference': wh['name'],
                            'name': wh['name'],
                            'code': wh['code'],
                            'server_id': self.id,
                        }
                        if same_warehouse:
                            values['warehouse_id'] = same_warehouse.id
                        self.env['warehouse.mapping'].sudo().create(values)
                    else:
                        values = {
                            'warehouse_izi_id': wh['id'],
                            'reference': wh['name'],
                            'name': wh['name'],
                            'code': wh['code'],
                            'server_id': self.id,
                        }
                        if not wm_by_izi_id[wh['id']].warehouse_id and same_warehouse:
                            values['warehouse_id'] = same_warehouse.id
                        wm_by_izi_id[wh['id']].write(values)
            else:
                loop = False

    def start_location_mapping(self):
        # GET existing
        lm_by_izi_id = {}
        location_mappings = self.env['location.mapping'].sudo().search([])
        for lm in location_mappings:
            if lm.location_izi_id:
                lm_by_izi_id[lm.location_izi_id] = lm
        # GET existing location
        loc_by_name = {}
        loc_by_barcode = {}
        locations = self.env['stock.location'].sudo().search([('usage', '=', 'internal')])
        for loc in locations:
            if loc.display_name:
                loc_by_name[loc.display_name] = loc
            if loc.barcode:
                loc_by_barcode[loc.barcode] = loc

        loop = True
        offset = 0
        limit = 1000
        while loop:
            r = requests.get(self.name + '/api/ui/read/list-detail/izi-location-mapping?domain_code=internal_stock&offset=%s&limit=%s' % (
                str(offset), str(limit)),
                headers={'X-Openerp-Session-Id': self.session_id}
            )
            res = r.json() if r.status_code == 200 else {}
            if res.get('code') == 200:
                if len(res.get('data')) == 0:
                    loop = False
                else:
                    offset += limit
                # Create Location Mapping
                for loc in res.get('data'):
                    # Search for location that has same name or barcode
                    same_location = False
                    if loc['display_name'] in loc_by_name:
                        same_location = loc_by_name[loc['display_name']]
                    if loc['barcode'] in loc_by_barcode:
                        same_location = loc_by_barcode[loc['barcode']]
                    # Create or Update
                    if loc['id'] not in lm_by_izi_id:
                        values = {
                            'location_izi_id': loc['id'],
                            'reference': loc['display_name'],
                            'name': loc['display_name'],
                            'barcode': loc['barcode'],
                            'server_id': self.id,
                        }
                        if same_location:
                            values['location_id'] = same_location.id
                        self.env['location.mapping'].sudo().create(values)
                    else:
                        values = {
                            'location_izi_id': loc['id'],
                            'reference': loc['display_name'],
                            'name': loc['display_name'],
                            'barcode': loc['barcode'],
                            'server_id': self.id,
                        }
                        if not lm_by_izi_id[loc['id']].location_id and same_location:
                            values['location_id'] = same_location.id
                        lm_by_izi_id[loc['id']].write(values)
            else:
                loop = False
    
    def start_company_mapping(self):
        # GET existing
        cm_by_izi_id = {}
        company_mappings = self.env['company.mapping'].sudo().search([])
        for cm in company_mappings:
            if cm.company_izi_id:
                cm_by_izi_id[cm.company_izi_id] = cm
        # GET existing companies
        cp_by_name = {}
        companies = self.env['res.company'].sudo().search([])
        for cp in companies:
            if cp.name:
                cp_by_name[cp.name] = cp

        loop = True
        offset = 0
        limit = 1000
        while loop:
            r = requests.get(self.name + '/api/ui/read/list-detail/res.company?offset=%s&limit=%s' % (
                str(offset), str(limit)),
                headers={'X-Openerp-Session-Id': self.session_id}
            )
            res = r.json() if r.status_code == 200 else {}
            if res.get('code') == 200:
                if len(res.get('data')) == 0:
                    loop = False
                else:
                    offset += limit
                # Create Companies Mapping
                for cp in res.get('data'):
                    # Search for companies that has same name
                    same_company = False
                    if cp['name'] in cp_by_name:
                        same_company = cp_by_name[cp['name']]
                    # Create or Update
                    if cp['id'] not in cm_by_izi_id:
                        values = {
                            'company_izi_id': cp['id'],
                            'reference': cp['name'],
                            'name': cp['name'],
                            'server_id': self.id,
                        }
                        if same_company:
                            values['company_id'] = same_company.id
                        self.env['company.mapping'].sudo().create(values)
                    else:
                        values = {
                            'company_izi_id': cp['id'],
                            'reference': cp['name'],
                            'name': cp['name'],
                            'server_id': self.id,
                        }
                        if not cm_by_izi_id[cp['id']].company_id and same_company:
                            values['company_id'] = same_company.id
                        cm_by_izi_id[cp['id']].write(values)
            else:
                loop = False
    
    def get_product_category_mapping(self):
        # GET existing 
        pcm_by_izi_id = {}
        product_category_mappings = self.env['product.category.mapping'].sudo().search([])
        for pcm in product_category_mappings:
            if pcm.izi_id:
                pcm_by_izi_id[pcm.izi_id] = pcm

    def get_staging_attribute_line_and_staging_variant(self, offset=0, limit=100, order_field='id', sort='asc', retry_login_count=3, retry_login=False,domain_url_attr=False, domain_url_var=False,mp_type=False):
         # Temporary Product Templates
        product_staging = self.env['product.staging'].sudo().search(
            [('izi_id', '!=', False), '|', ('active','=',True), ('active','=',False)])
        product_staging_by_izi_id = {}
        for pt in product_staging:
            product_staging_by_izi_id[pt.izi_id] = pt

        # Temporary Shopee Attributes
        sp_var_attributes = self.env['mp.shopee.item.var.attribute'].sudo().search(
            [('izi_id', '!=', False)])
        sp_var_attributes_by_izi_id = {}
        for at in sp_var_attributes:
            sp_var_attributes_by_izi_id[at.izi_id] = at

        # Temporary Shopee Attribute Values
        sp_var_attribute_values = self.env['mp.shopee.item.var.attribute.value'].sudo().search(
            [('izi_id', '!=', False)])
        sp_var_attribute_values_by_izi_id = {}
        for av in sp_var_attribute_values:
            sp_var_attribute_values_by_izi_id[av.izi_id] = av

         # Temporary Shopee Attribute Lines
        sp_var_attribute_lines = self.env['mp.shopee.attribute.line'].sudo().search(
            [('izi_id', '!=', False)])
        sp_var_attribute_lines_by_izi_id = {}
        for al in sp_var_attribute_lines:
            sp_var_attribute_lines_by_izi_id[al.izi_id] = al
        
        # Temporary Lazada Attributes
        lz_var_attributes = self.env['mp.lazada.category.attr'].sudo().search(
            [('izi_id', '!=', False),('is_sale_prop','=',True)])
        lz_var_attributes_by_izi_id = {}
        for at in lz_var_attributes:
            lz_var_attributes_by_izi_id[at.izi_id] = at

        # Temporary Lazada Attribute Values
        lz_var_attribute_values = self.env['mp.lazada.variant.value'].sudo().search(
            [('izi_id', '!=', False)])
        lz_var_attribute_values_by_izi_id = {}
        for av in lz_var_attribute_values:
            lz_var_attribute_values_by_izi_id[av.izi_id] = av

        # Temporary Lazada Attribute Lines
        lz_var_attribute_lines = self.env['mp.lazada.attribute.line'].sudo().search(
            [('izi_id', '!=', False)])
        lz_var_attribute_lines_by_izi_id = {}
        for al in lz_var_attribute_lines:
            lz_var_attribute_lines_by_izi_id[al.izi_id] = al

        # Temporary Product Products
        product_products = self.env['product.product'].sudo().search(
            [('izi_id', '!=', False),'|',('active','=',True),('active','=',False)])
        product_products_by_izi_id = {}
        for pp in product_products:
            product_products_by_izi_id[pp.izi_id] = pp

        # Temporary Product Variant Staging
        product_stg_var = self.env['product.staging.variant'].sudo().search(
            [('izi_id', '!=', False),'|',('active','=',True),('active','=',False)])

        product_stg_var_by_izi_id = {}
        for pp in product_stg_var:
            product_stg_var_by_izi_id[pp.izi_id] = pp
        
        def get_sp_attribute_lines(offset, limit, order_field, sort, retry_login_count, retry_login, domain_url_attr):
            try:
                i = 0
                while True:
                    if domain_url_attr:
                        url = self.name + '/api/ui/read/list-detail/izi-shopee-item-attribute-line/%s?offset=%s&limit=%s&order=%s&sort=%s' % (
                        domain_url_attr, str(offset), str(limit), order_field, sort)
                    else:
                        url = self.name + '/api/ui/read/list-detail/izi-shopee-item-attribute-line?offset=%s&limit=%s&order=%s&sort=%s' % (
                            str(offset), str(limit), order_field, sort)
                            
                    r = requests.get(url,
                        headers={'X-Openerp-Session-Id': self.session_id}
                    )
                    res = r.json() if r.status_code == 200 else {}
                    if res.get('code') == 200:
                        if len(res.get('data')) == 0:
                            break
                        else:
                            offset += limit
                        # Prepare Server Log
                        ServerLog = self.env['webhook.server.log'].sudo()
                        server_logs = ServerLog.search([('model_name', '=', 'mp.shopee.item.attribute.line'), ('status', '=', 'failed')])
                        server_logs_by_izi_id = {}
                        for sl in server_logs:
                            server_logs_by_izi_id[sl.izi_id] = sl
                        # Start Read Record
                        for atline in res.get('data'):
                            i += 1
                            error_message = False
                            izi_id = atline.get('id')
                            _logger.info('(%s) Get record %s IZI ID %s' % (i, 'mp.shopee.attribute.line', izi_id))
                            # Detail Log
                            self.log_record('mp.shopee.item.attribute.line', atline)
                            try:
                                if atline.get('id') in sp_var_attribute_lines_by_izi_id:
                                    record = sp_var_attribute_lines_by_izi_id.get(atline.get('id'))
                                else:
                                    record = False

                                if atline.get('product_staging_id').get('id') not in product_staging_by_izi_id:
                                    raise UserError(
                                        'product.staging with this izi_id %s not imported yet.'%(str(atline.get('product_staging_id').get('id'))))                            

                                # Create Template Attribute Value First
                                sp_var_attribute_value_ids = []
                                for atvalue in atline.get('value_ids'):
                                    if atvalue.get('id') not in sp_var_attribute_values_by_izi_id:
                                        raise UserError(
                                            'mp.shopee.item.var.attribute.value with this izi_id %s not imported yet.'%(str(atvalue.get('id'))))
                                    sp_var_attribute_value_ids.append(
                                        sp_var_attribute_values_by_izi_id.get(atvalue.get('id')).id)

                                # Create Template Attribute Line, Link to Product Template
                                if atline.get('attribute_id').get('id') not in sp_var_attributes_by_izi_id:
                                    raise UserError(
                                        'mp.shopee.item.var.attribute with this izi_id %s not imported yet.' %(str(atline.get('attribute_id').get('id'))))
                                if not record:
                                    record = self.env['mp.shopee.attribute.line'].create({
                                        'izi_id': atline.get('id'),
                                        'izi_md5': hashlib.md5(json.dumps(atline).encode('utf-8')).hexdigest(),
                                        'product_staging_id': product_staging_by_izi_id.get(atline.get('product_staging_id').get('id')).id,
                                        'attribute_id': sp_var_attributes_by_izi_id.get(atline.get('attribute_id').get('id')).id,
                                        'value_ids': [(6, 0, sp_var_attribute_value_ids)]
                                    })
                                else:
                                    if sp_var_attribute_lines_by_izi_id.get(atline.get('id')).izi_md5 != hashlib.md5(json.dumps(atline).encode('utf-8')).hexdigest():
                                        record.write({
                                            'izi_md5': hashlib.md5(json.dumps(atline).encode('utf-8')).hexdigest(),
                                            'product_staging_id': product_staging_by_izi_id.get(atline.get('product_staging_id').get('id')).id,
                                            'attribute_id': sp_var_attributes_by_izi_id.get(atline.get('attribute_id').get('id')).id,
                                            'value_ids': [(6, 0, sp_var_attribute_value_ids)]
                                        })
                                    sp_var_attribute_lines_by_izi_id.pop(atline.get('id'))
                            except Exception as e:
                                _logger.info('Failed Create / Update %s. Cause %s' % ('mp.shopee.item.attribute.line', str(e)))
                                if not self.is_skip_error:
                                    raise UserError(str(e))
                                else:
                                    error_message = str(e)
                            # Check Log
                            if not error_message:
                                if izi_id in server_logs_by_izi_id:
                                    server_logs_by_izi_id[izi_id].write({
                                        'res_id': record.id if record else False,
                                        'status': 'success',
                                        'last_retry_time': fields.Datetime.now(),
                                    })
                            else:
                                log_values = {
                                    'name': '%s %s' % (str('mp.shopee.item.attribute.line'), str(izi_id)),
                                    'server_id': self.id,
                                    'model_name': 'mp.shopee.item.attribute.line',
                                    'izi_id': izi_id,
                                    'status': 'failed',
                                    'res_id': False,
                                    'notes': self.get_notes('mp.shopee.item.attribute.line', atline),
                                    'error_message': error_message,
                                    'last_retry_time': fields.Datetime.now(),
                                }
                                if izi_id in server_logs_by_izi_id:
                                    server_logs_by_izi_id[izi_id].write(log_values)
                                else:
                                    ServerLog.create(log_values)
                    elif res.get('code') == 401:
                        if retry_login:
                            self.retry_login(retry_login_count)
                            get_sp_attribute_lines(
                                offset, limit, order_field, sort, retry_login_count, retry_login=False,domain_url_attr=domain_url_attr)
                        else:
                            break
                    else:
                        break
                    #### self.env.cr.commit()
            except Exception as e:
                raise UserError(e)
        
        def get_lz_attribute_lines(offset, limit, order_field, sort, retry_login_count, retry_login, domain_url_attr):
            try:
                i = 0
                while True:
                    if not self.session_id:
                        self.retry_login(retry_login_count)
                    
                    if domain_url_attr:
                        url = self.name + '/api/ui/read/list-detail/izi-lazada-attribute-line/%s?offset=%s&limit=%s&order=%s&sort=%s' % (
                        domain_url_attr, str(offset), str(limit), order_field, sort)
                    else:
                        url = self.name + '/api/ui/read/list-detail/izi-lazada-attribute-line?offset=%s&limit=%s&order=%s&sort=%s' % (
                            str(offset), str(limit), order_field, sort)
                            
                    r = requests.get(url,
                        headers={'X-Openerp-Session-Id': self.session_id}
                    )
                    res = r.json() if r.status_code == 200 else {}
                    if res.get('code') == 200:
                        if len(res.get('data')) == 0:
                            break
                        else:
                            offset += limit
                        # Prepare Server Log
                        ServerLog = self.env['webhook.server.log'].sudo()
                        server_logs = ServerLog.search([('model_name', '=', 'mp.lazada.attribute.line'), ('status', '=', 'failed')])
                        server_logs_by_izi_id = {}
                        for sl in server_logs:
                            server_logs_by_izi_id[sl.izi_id] = sl
                        for atline in res.get('data'):
                            i += 1
                            error_message = False
                            izi_id = atline.get('id')
                            _logger.info('(%s) Get record %s IZI ID %s' % (i, 'mp.lazada.attribute.line', izi_id))
                            # Detail Log
                            self.log_record('mp.lazada.attribute.line', atline)
                            try:
                                if atline.get('id') in lz_var_attribute_lines_by_izi_id:
                                    record = lz_var_attribute_lines_by_izi_id.get(atline.get('id'))
                                else:
                                    record = False

                                if atline.get('product_staging_id').get('id') not in product_staging_by_izi_id:
                                    raise UserError(
                                        'product.staging with this izi_id %s not imported yet.' % (str(atline.get('product_staging_id').get('id'))))                            

                                # Create Template Attribute Value First
                                lz_var_attribute_value_ids = []
                                for atvalue in atline.get('lz_variant_value_ids'):
                                    if atvalue.get('id') not in lz_var_attribute_values_by_izi_id:
                                        raise UserError(
                                            'mp.lazada.variant.value with this izi_id %s not imported yet.'%(str(atvalue.get('id'))))
                                    lz_var_attribute_value_ids.append(
                                        lz_var_attribute_values_by_izi_id.get(atvalue.get('id')).id)

                                # Create Template Attribute Line, Link to Product Template
                                if atline.get('attribute_id').get('id') not in lz_var_attributes_by_izi_id:
                                    raise UserError(
                                        'mp.lazada.category.attr with this izi_id %s not imported yet.'%(str(atline.get('attribute_id'))))
                                if not record:
                                    record = self.env['mp.lazada.attribute.line'].create({
                                        'izi_id': atline.get('id'),
                                        'izi_md5': hashlib.md5(json.dumps(atline).encode('utf-8')).hexdigest(),
                                        'product_staging_id': product_staging_by_izi_id.get(atline.get('product_staging_id').get('id')).id,
                                        'attribute_id': lz_var_attributes_by_izi_id.get(atline.get('attribute_id').get('id')).id,
                                        'lz_variant_value_ids': [(6, 0, lz_var_attribute_value_ids)]
                                    })
                                else:
                                    if lz_var_attribute_lines_by_izi_id.get(atline.get('id')).izi_md5 != hashlib.md5(json.dumps(atline).encode('utf-8')).hexdigest():
                                        record.write({
                                            'izi_md5': hashlib.md5(json.dumps(atline).encode('utf-8')).hexdigest(),
                                            'product_staging_id': product_staging_by_izi_id.get(atline.get('product_staging_id').get('id')).id,
                                            'attribute_id': lz_var_attributes_by_izi_id.get(atline.get('attribute_id').get('id')).id,
                                            'lz_variant_value_ids': [(6, 0, lz_var_attribute_value_ids)]
                                        })
                                    lz_var_attribute_lines_by_izi_id.pop(atline.get('id'))
                            except Exception as e:
                                _logger.info('Failed Create / Update %s. Cause %s' % ('mp.shopee.item.attribute.line', str(e)))
                                if not self.is_skip_error:
                                    raise UserError(str(e))
                                else:
                                    error_message = str(e)
    
                            # Check Log
                            if not error_message:
                                if izi_id in server_logs_by_izi_id:
                                    server_logs_by_izi_id[izi_id].write({
                                        'res_id': record.id if record else False,
                                        'status': 'success',
                                        'last_retry_time': fields.Datetime.now(),
                                    })
                            else:
                                log_values = {
                                    'name': '%s %s' % (str('mp.lazada.attribute.line'), str(izi_id)),
                                    'server_id': self.id,
                                    'model_name': 'mp.lazada.attribute.line',
                                    'izi_id': izi_id,
                                    'status': 'failed',
                                    'res_id': False,
                                    'notes': self.get_notes('mp.lazada.attribute.line', atline),
                                    'error_message': error_message,
                                    'last_retry_time': fields.Datetime.now(),
                                }
                                if izi_id in server_logs_by_izi_id:
                                    server_logs_by_izi_id[izi_id].write(log_values)
                                else:
                                    ServerLog.create(log_values)
                    elif res.get('code') == 401:
                        if retry_login:
                            self.retry_login(retry_login_count)
                            get_lz_attribute_lines(
                                offset, limit, order_field, sort, retry_login_count, retry_login=False,domain_url_attr=domain_url_attr)
                        else:
                            break
                    else:
                        break
                    #### self.env.cr.commit()
            except Exception as e:
                raise UserError(e)
        
        def get_product_staging_variants(offset, limit, order_field, sort, retry_login_count, retry_login, domain_url_var):
            try:
                i = 0
                while True:
                    if domain_url_var:
                        url = self.name + '/api/ui/read/list-detail/izi-product-staging-variants/%s?offset=%s&limit=%s&order=%s&sort=%s' % (
                        domain_url_var, str(offset), str(limit), order_field, sort)
                    else:
                        url = self.name + '/api/ui/read/list-detail/izi-product-staging-variants?offset=%s&limit=%s&order=%s&sort=%s' % (
                        str(offset), str(limit), order_field, sort)

                    r = requests.get(url,
                        headers={'X-Openerp-Session-Id': self.session_id}
                    )
                    res = r.json() if r.status_code == 200 else {}
                    if res.get('code') == 200:
                        if len(res.get('data')) == 0:
                            break
                        else:
                            offset += limit
                        variants_by_product_staging = {}
                        for variant in res.get('data'):
                            i += 1
                            izi_id = variant.get('id')
                            _logger.info('(%s) Get record %s IZI ID %s' % (i, 'product.staging.variant', izi_id))
                            if variant.get('product_stg_id').get('id') not in product_staging_by_izi_id:
                                raise UserError(
                                    'Product Staging with this izi_id not imported yet.')
                            if variant.get('product_stg_id').get('id') not in variants_by_product_staging:
                                variants_by_product_staging[variant.get(
                                    'product_stg_id').get('id')] = []
                            variants_by_product_staging[variant.get(
                                'product_stg_id').get('id')].append(variant)

                        for staging_id in variants_by_product_staging:
                            variants = variants_by_product_staging[staging_id]
                            existing_product_id = self.env['product.staging.variant'].search(
                                [('product_stg_id.izi_id', '=', staging_id)])
                            for variant in variants:
                                # shopee attribute var
                                sp_attribute_value_ids = []
                                for attval in variant.get('sp_attribute_value_ids'):
                                    if attval.get('id') not in sp_var_attribute_values_by_izi_id:
                                        raise UserError(
                                            'Attribute Value with this izi_id not imported yet.')
                                    sp_attribute_value_ids.append(
                                        sp_var_attribute_values_by_izi_id.get(attval.get('id')).id)
                                
                                # lazada attribute var
                                lz_attribute_value_ids = []
                                for attval in variant.get('lz_variant_value_ids'):
                                    if attval.get('id') not in lz_var_attribute_values_by_izi_id:
                                        raise UserError(
                                            'Attribute Value with this izi_id not imported yet.')
                                    lz_attribute_value_ids.append(
                                        lz_var_attribute_values_by_izi_id.get(attval.get('id')).id)

                                varian_values = {
                                    'izi_id': variant.get('id'),
                                    'name': variant.get('name'),
                                    'default_code': variant.get('default_code'),
                                    'product_stg_id': product_staging_by_izi_id.get(variant.get('product_stg_id').get('id')).id,
                                    'barcode': False if variant.get('barcode') == '' or variant.get('barcode') == ' ' else variant.get('barcode'),
#                                     'volume': variant.get('volume'),
#                                     'weight': variant.get('weight'),
                                    'price_custom': variant.get('price_custom'),
                                    'active': variant.get('active'),
                                    'is_active': variant.get('is_active'),
                                    'is_uploaded': variant.get('is_uploaded'),
                                    'mp_external_id': variant.get('mp_external_id'),
                                    'image_url': variant.get('image_url'),
                                    'image_url_external': variant.get('image_url_external'),
                                    'sp_variant_name': variant.get('sp_variant_name'),
                                    'sp_variant_id': variant.get('sp_variant_id'),
                                    'sp_variant_status': variant.get('sp_variant_status'),
                                    'sp_update_time_unix': variant.get('sp_update_time_unix'),
                                    'sp_attribute_value_ids': [(6, 0, sp_attribute_value_ids)] if sp_attribute_value_ids else False,
                                    'lz_variant_value_ids' : [(6, 0, lz_attribute_value_ids)] if lz_attribute_value_ids else False,
                                    'product_id': product_products_by_izi_id.get(variant.get('product_id').get('id')).id if variant.get('product_id').get('id') in product_products_by_izi_id else False,
                                }

                                if variant.get('id') not in product_stg_var_by_izi_id:
                                    self.env['product.staging.variant'].create(
                                        varian_values)
                                    if len(existing_product_id) == 1:
                                        existing_product_id.active = False
                                else:
                                    product_stg_var_by_izi_id.get(
                                        variant.get('id')).write(varian_values)
                    elif res.get('code') == 401:
                        if retry_login:
                            self.retry_login(retry_login_count)
                            get_product_staging_variants(
                                offset, limit, order_field, sort, retry_login_count, retry_login=False, domain_url_var=domain_url_var)
                    else:
                        break
                    #### self.env.cr.commit()
            except Exception as e:
                raise UserError(e)

        if mp_type == "sp":
            get_sp_attribute_lines(offset, limit, order_field, sort,
                                retry_login_count, retry_login, domain_url_attr)
        elif mp_type == "lz":
            get_lz_attribute_lines(offset, limit, order_field, sort,
                                retry_login_count, retry_login, domain_url_attr)
        else:
            get_sp_attribute_lines(offset, limit, order_field, sort,
                                retry_login_count, retry_login, domain_url_attr)
            get_lz_attribute_lines(offset, limit, order_field, sort,
                                retry_login_count, retry_login, domain_url_attr)

        get_product_staging_variants(offset, limit, order_field, sort,
                            retry_login_count, retry_login, domain_url_var)
    
    def after_get_products(self):
        # Unlink all product.product which has product_tmpl_id.izi_id is not false but the product.product itself does not have izi_id
        products_to_unlink = self.env['product.product'].sudo().search([('product_tmpl_id.izi_id', '!=', False), ('izi_id', '=', False)])
        if products_to_unlink:
            for prd in products_to_unlink:
                prd.active = False
                _logger.info('Set active false product.product with ID %s' % str(prd.id))

    def trigger_import_product_izi(self):
        mp_list = []
        mp_tokopedia_ids = self.env['mp.tokopedia'].search([])
        for mp_tokopedia_id in mp_tokopedia_ids:
            mp_list.append({
                'mp': 'tokopedia',
                'mp_id': mp_tokopedia_id.izi_id
            })
        mp_shopee_ids = self.env['mp.shopee'].search([])
        for mp_shopee_id in mp_shopee_ids:
            mp_list.append({
                'mp': 'shopee',
                'mp_id': mp_shopee_id.izi_id
            })
        mp_lazada_ids = self.env['mp.lazada'].search([])
        for mp_lazada_id in mp_lazada_ids:
            mp_list.append({
                'mp': 'lazada',
                'mp_id': mp_lazada_id.izi_id
            })
        mp_blibli_ids = self.env['mp.blibli'].search([])
        for mp_blibli_id in mp_blibli_ids:
            mp_list.append({
                'mp': 'blibli',
                'mp_id': mp_blibli_id.izi_id
            })
        r = requests.post(self.name + '/ui/products/import/all', headers={
                          'X-Openerp-Session-Id': self.session_id, 'Content-type': 'application/json'}, json={'mp_list': mp_list})
        res = r.json()
        if r.status_code == 200:
            if res.get('result').get('status') != 200:
                raise UserError('Error when IZI get product from marketplace')
        else:
            raise UserError('Error when IZI get product from marketplace')

    def get_product_discounts(self):
        campaign_obj = self.env['juragan.campaign'].sudo()
        product_discount_obj = self.env['mp.product.discount'].sudo()

        # pull product discount from IZI
        self.get_records('mp.product.discount', force_update=True, limit=500)
        self.get_records('mp.product.discount.line', force_update=True, limit=500)

        # collecting campaign with related product discount
        mp_campaigns = campaign_obj.search([('discount_id', '!=', False)])
        # collecting its product discount, it may has new values to be updated to campaign
        mp_campaign_product_discounts = mp_campaigns.mapped('discount_id')
        # collecting other product discount, it may new product discount, so need to create campaign
        product_discounts = product_discount_obj.search([('id', 'not in', mp_campaign_product_discounts.ids)])

        # sync existing campaigns with its discount
        mp_campaigns.sync_with_discount()

        # create new campaigns then sync with discount
        for product_discount in product_discounts:
            campaign_values = campaign_obj._prepare_campaign_values_from_discount(product_discount, update=False)
            campaign = campaign_obj.with_context(sync_discount=True).create(campaign_values)
            campaign.sync_with_discount(force=True)
            _logger.info("New campaign created: %s" % campaign.name)

    def get_products(self):
        try:
            self = self.with_context(get_products=True)
            self.with_context(create_product_product=False).get_records('product.template', domain_code='all_active', force_update=True, limit=500, commit_every=100)
            self.get_records('product.image', force_update=True, limit=500, commit_every=100)
            self.get_records('product.template.wholesale', force_update=True, limit=500, commit_every=100)
            self.get_records('product.staging', force_update=True, domain_code='all_active', limit=500, commit_every=100)
            self.get_records('product.image.staging', force_update=True, limit=500, commit_every=100)
            self.get_records('product.staging.wholesale', force_update=True, limit=500, commit_every=100)

            self.get_records('product.product', force_update=True, domain_code='all_active', limit=500, commit_every=100)
            self.get_records('mp.tokopedia.variant.value', force_update=True, limit=500, commit_every=100)
            self.get_records('mp.tokopedia.attribute.line', force_update=True, limit=500, commit_every=100)
            self.get_records('mp.blibli.attribute.line', force_update=True, limit=500, commit_every=100)
            self.get_records('product.staging.variant', force_update=True, limit=500, commit_every=100)

            # get product discount
            try:
                self.get_product_discounts()
            except Exception as e:
                _logger.error(str(e))

            self.after_get_products()

            self.get_staging_attribute_line_and_staging_variant(limit=500)
            self.get_records('mp.shopee.item.attribute.val', force_update=True, limit=500, commit_every=100)
            self.get_records('mp.shopee.item.logistic', force_update=True, limit=500, commit_every=100)

            self.with_context(create_product_attr=True).get_records('mp.lazada.product.attr',force_update=True, limit=500, commit_every=100)
            self.with_context(create_product_attr=True).get_records('mp.blibli.item.attribute.val',force_update=True, limit=500, commit_every=100)
        except Exception as e:
            raise UserError(e)

    def get_product_category(self):
        self.get_records('mp.tokopedia.category',
                         domain_url="[('parent_id', '=', False)]", limit=1000, loop_commit=False, commit_every=500)
        self.get_records('mp.tokopedia.category',
                         domain_url="[('parent_id', '!=', False), ('child_ids', '!=', False)]", limit=1000, loop_commit=False, commit_every=500)
        self.get_records('mp.tokopedia.category',
                         domain_url="[('child_ids', '=', False)]", limit=1000, loop_commit=False, commit_every=500)
        self.get_records('mp.shopee.item.brand', limit=1000, domain_code='all_active', loop_commit=False, commit_every=500)
        self.get_records('mp.shopee.item.category', limit=1000, domain_code='has_children', loop_commit=False, commit_every=500)
        self.get_records('mp.shopee.item.attribute', limit=1000, domain_code='all_active', loop_commit=False, commit_every=500)
        self.get_records('mp.shopee.item.attribute.option', limit=1000, loop_commit=False, commit_every=500)

        # if not self.env['mp.lazada.brand'].search([]):
        self.get_records('mp.lazada.category.attr.opt', limit=1000, loop_commit=False, commit_every=500)
        self.get_records('mp.lazada.variant.value', limit=1000, loop_commit=False, commit_every=500)
        self.get_records('mp.lazada.category', limit=1000, domain_code='has_children', loop_commit=False, commit_every=500)
        self.get_records('mp.lazada.category.attr', limit=1000, loop_commit=False, commit_every=500)

        self.get_records('mp.blibli.item.attr.option', limit=1000, loop_commit=False, commit_every=500)
        self.get_records('mp.blibli.variant.value', force_update=True, limit=500, commit_every=100)
        self.get_records('mp.blibli.item.category.attr', limit=1000, loop_commit=False, commit_every=500)
        self.get_records('mp.blibli.item.category', limit=1000, domain_code='has_children', loop_commit=False, commit_every=500)


    def get_product_brand(self):
        self.get_records('mp.blibli.brand', limit=5000, loop_commit=False, commit_every=500)
        self.get_records('mp.lazada.brand', limit=5000, loop_commit=False, commit_every=500)

    def get_product_dependency(self):
        self.get_records('mp.tokopedia.shop', loop_commit=False)
        self.get_records('mp.tokopedia.etalase', domain_code='all_active', loop_commit=False)

        self.get_records('mp.tokopedia.category.value', limit=1000, loop_commit=False)
        self.get_records('mp.tokopedia.category.unit', limit=1000, loop_commit=False)
        self.get_records('mp.tokopedia.category.variant', limit=1000, loop_commit=False)

        self.get_records('mp.shopee.logistic.size', limit=1000, loop_commit=False)
        self.get_records('mp.shopee.logistic', limit=1000, loop_commit=False)
        self.get_records('mp.shopee.shop.logistic', limit=1000, loop_commit=False)

        self.get_records('mp.shopee.item.var.attribute', limit=1000, loop_commit=False)
        self.get_records('mp.shopee.item.var.attribute.value', limit=1000, loop_commit=False)

        # Lazada

        self.get_records('mp.blibli.logistic', limit=1000, loop_commit=False)


    def sp_get_attribute_category(self,category_id=False,mp_id=False):
        server = self.env['webhook.server'].search(
            [('active', 'in', [False, True])], limit=1, order='write_date desc')
        if not server:
            raise UserError('Create at least 1 webhook server')
        r = requests.post(self.name + '/public/ui/products/sp/category/attributes', json={
            'category_id': category_id,'mp_id': mp_id
        }, headers={
            'X-Openerp-Session-Id': self.session_id,
        })
        res = json.loads(r.text) if r.status_code == 200 else {}
        if res:
            
            # self.get_records('mp.shopee.item.attribute.option')
            # self.get_records('mp.shopee.item.attribute')
            res = res['result']

            # def process_model(model_name,data):
            #     attr_ids = []
            #     for res_values in data:
            #         record = self.get_existing_record(
            #             model_name, res_values)
            #         if record:
            #             if 'izi_md5' in self.env[model_name]._fields:
            #                 izi_md5 = hashlib.md5(json.dumps(
            #                     res_values).encode('utf-8')).hexdigest()
            #                 values = self.mapping_field(
            #                     model_name, res_values, update=True)
            #                 values.update({
            #                     'izi_md5': izi_md5
            #                 })
            #                 record.write(values)
            #                 if model_name == 'mp.shopee.item.attribute':
            #                     attr_ids.append(record.id)
            #             else:
            #                 values = self.mapping_field(
            #                     model_name, res_values, update=True)
            #                 record.write(values)
            #                 if model_name == 'mp.shopee.item.attribute':
            #                     attr_ids.append(record.id)
            #         else:
            #             values = self.mapping_field(
            #                 model_name, res_values, update=False)
            #             obj = self.env[model_name].create(values)
            #             if model_name == 'mp.shopee.item.attribute':
            #                 attr_ids.append(obj.id)
                            
            #         #### self.env.cr.commit()
                
            #     if model_name == 'mp.shopee.item.attribute':
            #         return attr_ids
            
            # process_model('mp.shopee.item.attribute.option', res['options'])

            attribute_by_izi_id = []
            options_by_izi_id = []
            for attr in res.get('data'):
                attribute_by_izi_id.append(attr['id'])
            for opt in res.get('options'):
                options_by_izi_id.append(opt['id'])

            server.get_records('mp.shopee.item.category', force_update=True, domain_url="[('id', '=', %s)]" % str(
                                    category_id))
            server.get_records('mp.shopee.item.attribute', force_update=True, domain_url="[('id', 'in', %s)]" % str(
                                    attribute_by_izi_id))
            server.get_records('mp.shopee.item.attribute.option', force_update=True, domain_url="[('id', 'in', %s)]" % str(
                                    options_by_izi_id))
            

            #### self.env.cr.commit()
        return res

    def sp_get_attribute_brand(self,category_id=False,mp_id=False):
        server = self.env['webhook.server'].search(
            [('active', 'in', [False, True])], limit=1, order='write_date desc')
        if not server:
            raise UserError('Create at least 1 webhook server')

        r = requests.post(self.name + '/public/ui/products/sp/category/brands', json={
            'category_id': category_id,'mp_id': mp_id
        }, headers={
            'X-Openerp-Session-Id': self.session_id,
        })
        res = json.loads(r.text) if r.status_code == 200 else {}
        if res:
            
            # self.get_records('mp.shopee.item.attribute')
            res = res['result']
            server.get_records('mp.shopee.item.brand', force_update=True, domain_url="[('id', 'in', %s)]" % str(
                                    res.get("data")))
            server.get_records('mp.shopee.item.category', force_update=True, domain_url="[('id', '=', %s)]" % str(
                                    category_id))
        return res  

    def lz_get_attribute_category(self,category_id=False,mp_id=False):
        r = requests.post(self.name + '/public/ui/products/lz/category/attributes', json={
            'category_id': category_id,'mp_id': mp_id
        }, headers={
            'X-Openerp-Session-Id': self.session_id,
        })
        res = json.loads(r.text) if r.status_code == 200 else {}
        if res:
            
            # self.get_records('mp.shopee.item.attribute.option')
            # self.get_records('mp.shopee.item.attribute')
            res = res['result']

            def process_model(model_name,data):
                attr_ids = []
                for res_values in data:
                    record = self.get_existing_record(
                        model_name, res_values)
                    if record:
                        if 'izi_md5' in self.env[model_name]._fields:
                            izi_md5 = hashlib.md5(json.dumps(
                                res_values).encode('utf-8')).hexdigest()
                            values = self.mapping_field(
                                model_name, res_values, update=True)
                            values.update({
                                'izi_md5': izi_md5
                            })
                            record.write(values)
                            if model_name == 'mp.lazada.category.attr':
                                attr_ids.append(record.id)
                        else:
                            values = self.mapping_field(
                                model_name, res_values, update=True)
                            record.write(values)
                            if model_name == 'mp.lazada.category.attr':
                                attr_ids.append(record.id)
                    else:
                        values = self.mapping_field(
                            model_name, res_values, update=False)
                        obj = self.env[model_name].create(values)
                        if model_name == 'mp.lazada.category.attr':
                            attr_ids.append(obj.id)
                            
                        # if self.env.user and model_name == 'sale.order':
                        #     self.env.user.notify_info('New Order From Marketplace')
                    # self.env.cr.commit()
                
                if model_name == 'mp.shopee.item.attribute':
                    return attr_ids
            
            process_model('mp.lazada.category.attr.opt', res['options'])
            attribute_proc = process_model('mp.lazada.category.attr', res['data'])

            # category = self.env['mp.lazada.category'].search([('izi_id','=',category_id)])
            # # if category and attribute_proc :
            # #     category.write({
            # #         'attr_ids': [(6, 0, attribute_proc)]
            # #     })
                # #### self.env.cr.commit()
        return res

        
