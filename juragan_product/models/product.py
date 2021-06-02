# -*- coding: utf-8 -*-
# import base64
from odoo import models, fields, api, tools, _
from odoo.modules import get_resource_path
from odoo.tools import pycompat, file_open
# from odoo.addons.juragan_webhook import BigMany2many

import json
import hashlib
import logging
import requests
from datetime import datetime, timedelta
from base64 import b64encode
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ProductMapping(models.Model):
    _name = 'product.mapping'

    product_product_izi_id = fields.Integer()
    product_template_izi_id = fields.Integer()
    reference = fields.Char()
    name = fields.Char()
    default_code = fields.Char()
    product_id = fields.Many2one('product.product', 'Product')
    server_id = fields.Many2one('webhook.server', 'Server')


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


class ProductTemplate(models.Model):
    _name = 'product.template'
    _inherit = ['product.template']

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

    def _get_image_url(self):
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        for rec in self:
            if rec.image:
                rec.image_url = '%s/jpg/product.template/image/%s.jpg' % (
                    base_url, str(rec.id))
            elif rec.image_url_external:
                rec.image_url = rec.image_url_external

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

    def _get_image_url(self):
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        for rec in self:
            if rec.image:
                rec.image_url = '%s/jpg/product.product/image/%s.jpg' % (
                    base_url, str(rec.id))
            elif rec.image_url_external:
                rec.image_url = rec.image_url_external

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
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        for rec in self:
            if rec.image:
                rec.url = '%s/jpg/product.image/image/%s.jpg' % (
                    base_url, str(rec.id))
            elif rec.url_external:
                rec.url = rec.url_external


class ProductImageStaging(models.Model):
    _name = 'product.image.staging'

    name = fields.Char('Name')
    image = fields.Binary('Image', attachment=True)
    product_stg_id = fields.Many2one('product.staging')
    url_external = fields.Char('URL External')
    url = fields.Char('URL', compute='_get_image_url')
    active = fields.Boolean(related='product_stg_id.active')

    izi_id = fields.Integer('Izi ID', copy=False)
    izi_md5 = fields.Char()

    def _get_image_url(self):
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        for rec in self:
            if rec.image:
                rec.url = '%s/jpg/product.image.staging/image/%s.jpg' % (
                    base_url, str(rec.id))
            elif rec.url_external:
                rec.url = rec.url_external

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


class WebhookServer(models.Model):
    _inherit = 'webhook.server'

    product_mapping_ids = fields.One2many('product.mapping', 'server_id', 'Product Mapping')
    category_mapping_ids = fields.One2many('product.category.mapping', 'server_id','Product Category Mapping')
    warehouse_mapping_ids = fields.One2many('warehouse.mapping', 'server_id', 'Warehouse Mapping')
    location_mapping_ids = fields.One2many('location.mapping', 'server_id', 'Location Mapping')

    def start_product_mapping(self):
        # GET existing 
        pm_by_izi_id = {}
        product_mappings = self.env['product.mapping'].sudo().search([])
        for pm in product_mappings:
            if pm.product_product_izi_id:
                pm_by_izi_id[pm.product_product_izi_id] = pm
        # GET existing product.product
        pp_by_name = {}
        pp_by_default_code = {}
        product_products = self.env['product.product'].sudo().search([])
        for pp in product_products:
            # if pp.izi_id:
            #     # Skip product product with izi_id
            #     continue
            if pp.name:
                pp_by_name[pp.name] = pp
            if pp.default_code:
                pp_by_default_code[pp.default_code] = pp
        
        loop = True
        offset = 0
        limit = 1000
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
                    if pd.get('type') and pd['type']['value'] == 'service':
                        continue
                    # Search for product template that has same name or default code
                    product_product = False
                    if pd['name'] in pp_by_name:
                        product_product = pp_by_name[pd['name']]
                    if pd['default_code'] in pp_by_default_code:
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
                        if product_product:
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
                            values['product_id'] = product_product.id
                        pm_by_izi_id[pd['id']].write(values)
            else:
                loop = False
    
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
            r = requests.get(self.name + '/api/ui/read/list-detail/stock.warehouse?offset=%s&limit=%s' % (
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

    def get_product_category_mapping(self):
        # GET existing 
        pcm_by_izi_id = {}
        product_category_mappings = self.env['product.category.mapping'].sudo().search([])
        for pcm in product_category_mappings:
            if pcm.izi_id:
                pcm_by_izi_id[pcm.izi_id] = pcm

    def get_product_categories(self, loop=True, offset=0, limit=100, order_field='id', sort='asc', retry_login_count=3, retry_login=True):

        def recursion_create_parent_product_category(exist_category_by_izi_id, res_category_values, category_id, retry_login_count, retry_login):
            try:
                r = requests.get(self.name + '/api/ui/read/detail/izi-product-categories/' + str(category_id), headers={
                    'X-Openerp-Session-Id': self.session_id,
                })
                res = r.json() if r.status_code == 200 else {}
                if res['code'] == 401:
                    if retry_login:
                        self.retry_login(retry_login_count)
                        recursion_create_parent_product_category(
                            exist_category_by_izi_id, res_category_values, category_id, retry_login_count, retry_login=False)
                if res['code'] == 200:
                    izi_md5 = hashlib.md5(json.dumps(
                        res.get('data')).encode('utf-8')).hexdigest()
                    res_values = self.mapping_field(
                        'mp.tokopedia.category', res.get('data'))
                    res_values.update({
                        'izi_md5': izi_md5
                    })
                    product_category_id = self.env['product.category'].create(
                        res_values)
                    exist_category_by_izi_id[product_category_id.izi_id] = product_category_id

                    izi_md5 = hashlib.md5(json.dumps(
                        res_category_values).encode('utf-8')).hexdigest()
                    res_values = self.mapping_field(
                        'mp.tokopedia.category', res_category_values)
                    res_values.update({
                        'izi_md5': izi_md5
                    })

                    product_category_id = self.env['product.category'].create(
                        res_values)
                    exist_category_by_izi_id[product_category_id.izi_id] = product_category_id
                self.env.cr.commit()
            except Exception as e:
                if len(e.args) > 0:
                    for args in e.args:
                        if 'Import First' in args:
                            exist_category_by_izi_id = recursion_create_parent_product_category(
                                exist_category_by_izi_id, res.get('data'), str(res.get('data').get('parent_id').get('id')), retry_login_count, retry_login)
            return exist_category_by_izi_id

        try:
            while loop:
                r = requests.get(self.name + '/api/ui/read/list-detail/izi-product-categories?offset=%s&limit=%s&order=%s&sort=%s' % (
                    str(offset), str(limit), order_field, sort),
                    headers={'X-Openerp-Session-Id': self.session_id}
                )
                res = r.json() if r.status_code == 200 else {}
                if res.get('code') == 401:
                    if retry_login:
                        self.retry_login(retry_login_count)
                        self.get_product_categories(
                            offset=offset, retry_login=False)
                    else:
                        loop = False
                elif res.get('code') == 200:
                    if len(res.get('data')) < limit:
                        loop = False
                    else:
                        offset += limit
                    ProductCategory = self.env['product.category']
                    product_category_ids = ProductCategory.search([])
                    exist_category_by_izi_id = {}
                    for cat_id in product_category_ids:
                        exist_category_by_izi_id[cat_id.izi_id] = cat_id
                    for res_category_values in res.get('data'):
                        izi_md5 = hashlib.md5(json.dumps(
                            res_category_values).encode('utf-8')).hexdigest()
                        if res_category_values.get('id') in exist_category_by_izi_id:
                            try:
                                if izi_md5 != exist_category_by_izi_id.get(res_category_values.get('id')).izi_md5:
                                    res_values = self.mapping_field(
                                        'product.category', res_category_values)
                                    res_values.update({
                                        'izi_md5': izi_md5
                                    })
                                    exist_category_by_izi_id.get(
                                        res_category_values.get('id')).write(res_values)
                            except Exception as e:
                                if len(e.args) > 0:
                                    for args in e.args:
                                        if 'Import First' in args:
                                            exist_category_by_izi_id = recursion_create_parent_product_category(
                                                exist_category_by_izi_id, res_category_values, str(res_category_values.get('parent_id').get('id')), retry_login_count, retry_login)
                        else:
                            try:
                                res_values = self.mapping_field(
                                    'product.category', res_category_values)
                                res_values.update({
                                    'izi_md5': izi_md5
                                })
                                ProductCategory.create(res_values)
                            except Exception as e:
                                if len(e.args) > 0:
                                    for args in e.args:
                                        if 'Import First' in args:
                                            exist_category_by_izi_id = recursion_create_parent_product_category(
                                                exist_category_by_izi_id, res_category_values, str(res_category_values.get('parent_id').get('id')), retry_login_count, retry_login)
                self.env.cr.commit()
        except Exception as e:
            raise UserError(e)

    def get_tokopedia_categories(self, loop=True, offset=0, limit=100, order_field='id', sort='asc', retry_login_count=3, retry_login=False):

        def recursion_create_parent_tokopedia_category(exist_category_by_izi_id, res_category_values, category_id, retry_login_count, retry_login):
            try:
                r = requests.get(self.name + '/api/ui/read/detail/izi-tokopedia-categories/' + str(category_id), headers={
                    'X-Openerp-Session-Id': self.session_id,
                })
                res = r.json() if r.status_code == 200 else {}
                if res.get('code') == 401:
                    if retry_login:
                        self.retry_login(retry_login_count)
                        recursion_create_parent_tokopedia_category(
                            exist_category_by_izi_id, res_category_values, category_id, retry_login_count, retry_login=False)
                elif res.get('code') == 200:
                    izi_md5 = hashlib.md5(json.dumps(
                        res.get('data')).encode('utf-8')).hexdigest()
                    res_values = self.mapping_field(
                        'mp.tokopedia.category', res.get('data'))
                    res_values.update({
                        'izi_md5': izi_md5
                    })
                    tokopedia_category_id = self.env['mp.tokopedia.category'].create(
                        res_values)
                    exist_category_by_izi_id[tokopedia_category_id.izi_id] = tokopedia_category_id

                    izi_md5 = hashlib.md5(json.dumps(
                        res_category_values).encode('utf-8')).hexdigest()
                    res_values = self.mapping_field(
                        'mp.tokopedia.category', res_category_values)
                    res_values.update({
                        'izi_md5': izi_md5
                    })

                    tokopedia_category_id = self.env['mp.tokopedia.category'].create(
                        res_values)
                    exist_category_by_izi_id[tokopedia_category_id.izi_id] = tokopedia_category_id
                self.env.cr.commit()
            except Exception as e:
                if len(e.args) > 0:
                    for args in e.args:
                        if 'Import First' in args:
                            exist_category_by_izi_id = recursion_create_parent_tokopedia_category(
                                exist_category_by_izi_id, res.get('data'), str(res.get('data').get('parent_id').get('id')), retry_login_count, retry_login)
            return exist_category_by_izi_id

        try:
            while loop:
                r = requests.get(self.name + '/api/ui/read/list-detail/izi-tokopedia-categories?offset=%s&limit=%s&order=%s&sort=%s' % (
                    str(offset), str(limit), order_field, sort),
                    headers={'X-Openerp-Session-Id': self.session_id}
                )
                res = r.json() if r.status_code == 200 else {}
                if res.get('code') == 401:
                    if retry_login:
                        self.retry_login(retry_login_count)
                        self.get_tokopedia_categories(
                            offset=offset, retry_login=False)
                    else:
                        loop = False
                elif res.get('code') == 200:
                    if len(res.get('data')) == 0:
                        loop = False
                    else:
                        offset += limit
                    TokopediaCategory = self.env['mp.tokopedia.category']
                    tokopedia_category_ids = TokopediaCategory.search([])
                    exist_category_by_izi_id = {}
                    for cat_id in tokopedia_category_ids:
                        exist_category_by_izi_id[cat_id.izi_id] = cat_id
                    for res_category_values in res.get('data'):
                        izi_md5 = hashlib.md5(json.dumps(
                            res_category_values).encode('utf-8')).hexdigest()
                        if res_category_values.get('id') in exist_category_by_izi_id:
                            try:
                                if izi_md5 != exist_category_by_izi_id.get(res_category_values.get('id')).izi_md5:
                                    res_values = self.mapping_field(
                                        'mp.tokopedia.category', res_category_values)
                                    res_values.update({
                                        'izi_md5': izi_md5
                                    })
                                    exist_category_by_izi_id.get(
                                        res_category_values.get('id')).write(res_values)
                            except Exception as e:
                                if len(e.args) > 0:
                                    for args in e.args:
                                        if 'Import First' in args:
                                            exist_category_by_izi_id = recursion_create_parent_tokopedia_category(
                                                exist_category_by_izi_id, res_category_values, str(res_category_values.get('parent_id').get('id')), retry_login_count, retry_login)
                        else:
                            try:
                                res_values = self.mapping_field(
                                    'mp.tokopedia.category', res_category_values)
                                res_values.update({
                                    'izi_md5': izi_md5
                                })
                                TokopediaCategory.create(res_values)
                            except Exception as e:
                                if len(e.args) > 0:
                                    for args in e.args:
                                        if 'Import First' in args:
                                            exist_category_by_izi_id = recursion_create_parent_tokopedia_category(
                                                exist_category_by_izi_id, res_category_values, str(res_category_values.get('parent_id').get('id')), retry_login_count, retry_login)
                else:
                    loop = False
                self.env.cr.commit()
        except Exception as e:
            raise UserError(e)

    def get_attribute_line_and_variant(self, offset=0, limit=100, order_field='id', sort='asc', retry_login_count=3, retry_login=False):
        # Temporary Product Templates
        product_templates = self.env['product.template'].search(
            [('izi_id', '!=', False)])
        product_templates_by_izi_id = {}
        for pt in product_templates:
            product_templates_by_izi_id[pt.izi_id] = pt

        # Temporary Attributes
        attributes = self.env['product.attribute'].search(
            [('izi_id', '!=', False)])
        attributes_by_izi_id = {}
        for at in attributes:
            attributes_by_izi_id[at.izi_id] = at

        # Temporary Attribute Values
        attribute_values = self.env['product.attribute.value'].search(
            [('izi_id', '!=', False)])
        attribute_values_by_izi_id = {}
        for av in attribute_values:
            attribute_values_by_izi_id[av.izi_id] = av

         # Temporary Attribute Lines
        attribute_lines = self.env['product.template.attribute.line'].search(
            [('izi_id', '!=', False)])
        attribute_lines_by_izi_id = {}
        for al in attribute_lines:
            attribute_lines_by_izi_id[al.izi_id] = al

         # Temporary Product Products
        product_products = self.env['product.product'].search(
            [('izi_id', '!=', False), '|', ('active', '=', True), ('active', '=', False)])
        product_products_by_izi_id = {}
        for pp in product_products:
            product_products_by_izi_id[pp.izi_id] = pp

        # GET Attribute Lines
        def get_attribute_lines(offset, limit, order_field, sort, retry_login_count, retry_login):
            try:
                while True:
                    r = requests.get(self.name + '/api/ui/read/list-detail/product.attribute.line?offset=%s&limit=%s&order=%s&sort=%s' % (
                        str(offset), str(limit), order_field, sort),
                        headers={'X-Openerp-Session-Id': self.session_id}
                    )
                    res = r.json() if r.status_code == 200 else {}
                    if res.get('code') == 200:
                        if len(res.get('data')) == 0:
                            break
                        else:
                            offset += limit
                        for atline in res.get('data'):
                            if atline.get('product_tmpl_id').get('id') not in product_templates_by_izi_id:
                                raise UserError(
                                    'Product Template with this izi_id not imported yet.')

                            # Unlink existing template attribute value
                            self.env['product.template.attribute.value'].search(
                                [('product_tmpl_id', '=', product_templates_by_izi_id.get(atline.get('product_tmpl_id').get('id')).id)]).unlink()

                            # Create Template Attribute Value First
                            template_attribute_value_ids = []
                            attribute_value_ids = []
                            for atvalue in atline.get('value_ids'):
                                if atvalue.get('id') not in attribute_values_by_izi_id:
                                    raise UserError(
                                        'Attribute Value with this izi_id not imported yet.')
                                template_attribute_value = self.env['product.template.attribute.value'].create({
                                    'name': attribute_values_by_izi_id.get(atvalue.get('id')).name,
                                    'product_attribute_value_id': attribute_values_by_izi_id.get(atvalue.get('id')).id,
                                    'product_tmpl_id': product_templates_by_izi_id.get(atline.get('product_tmpl_id').get('id')).id,
                                })
                                template_attribute_value_ids.append(
                                    template_attribute_value.id)
                                attribute_value_ids.append(
                                    attribute_values_by_izi_id.get(atvalue.get('id')).id)

                            # Create Template Attribute Line, Link to Product Template
                            if atline.get('attribute_id').get('id') not in attributes_by_izi_id:
                                raise UserError(
                                    'Attributes with this izi_id not imported yet.')
                            if atline.get('id') not in attribute_lines_by_izi_id:
                                self.env['product.template.attribute.line'].create({
                                    'izi_id': atline.get('id'),
                                    'izi_md5': hashlib.md5(json.dumps(atline).encode('utf-8')).hexdigest(),
                                    'product_tmpl_id': product_templates_by_izi_id.get(atline.get('product_tmpl_id').get('id')).id,
                                    'attribute_id': attributes_by_izi_id.get(atline.get('attribute_id').get('id')).id,
                                    'product_template_value_ids': [(6, 0, template_attribute_value_ids)],
                                    'value_ids': [(6, 0, attribute_value_ids)]
                                })
                            else:
                                if attribute_lines_by_izi_id.get(atline.get('id')).izi_md5 != hashlib.md5(json.dumps(atline).encode('utf-8')).hexdigest():
                                    attribute_lines_by_izi_id.get(atline.get('id')).write({
                                        'izi_md5': hashlib.md5(json.dumps(atline).encode('utf-8')).hexdigest(),
                                        'product_tmpl_id': product_templates_by_izi_id.get(atline.get('product_tmpl_id').get('id')).id,
                                        'attribute_id': attributes_by_izi_id.get(atline.get('attribute_id').get('id')).id,
                                        'product_template_value_ids': [(6, 0, template_attribute_value_ids)],
                                        'value_ids': [(6, 0, attribute_value_ids)]
                                    })
                                attribute_lines_by_izi_id.pop(atline.get('id'))
                    elif res.get('code') == 401:
                        if retry_login:
                            self.retry_login(retry_login_count)
                            get_attribute_lines(
                                offset, limit, order_field, sort, retry_login_count, retry_login=False)
                        else:
                            break
                    else:
                        break
                    self.env.cr.commit()
            except Exception as e:
                raise UserError(e)

        # GET Product Product to Update izi_id
        # GET Attribute Lines
        def get_product_variants(offset, limit, order_field, sort, retry_login_count, retry_login):
            try:
                while True:
                    r = requests.get(self.name + '/api/ui/read/list-detail/izi-product-variants?domain_code=all_active&offset=%s&limit=%s&order=%s&sort=%s' % (
                        str(offset), str(limit), order_field, sort),
                        headers={'X-Openerp-Session-Id': self.session_id}
                    )
                    res = r.json() if r.status_code == 200 else {}
                    if res.get('code') == 200:
                        if len(res.get('data')) == 0:
                            break
                        else:
                            offset += limit
                        variants_by_product_template = {}
                        for variant in res.get('data'):
                            if variant.get('product_tmpl_id').get('id') not in product_templates_by_izi_id:
                                raise UserError(
                                    'Product template with this izi_id not imported yet.')
                            if variant.get('product_tmpl_id').get('id') not in variants_by_product_template:
                                variants_by_product_template[variant.get(
                                    'product_tmpl_id').get('id')] = []
                            variants_by_product_template[variant.get(
                                'product_tmpl_id').get('id')].append(variant)

                        for template_id in variants_by_product_template:
                            variants = variants_by_product_template[template_id]
                            existing_product_id = self.env['product.product'].search(
                                [('product_tmpl_id.izi_id', '=', template_id)])
                            for variant in variants:
                                attribute_value_ids = []
                                for attval in variant.get('attribute_value_ids'):
                                    if attval.get('id') not in attribute_values_by_izi_id:
                                        raise UserError(
                                            'Attribute Value with this izi_id not imported yet.')
                                    attribute_value_ids.append(
                                        attribute_values_by_izi_id.get(attval.get('id')).id)

                                varian_values = {
                                    'izi_id': variant.get('id'),
                                    'default_code': variant.get('default_code'),
                                    'product_tmpl_id': product_templates_by_izi_id.get(variant.get('product_tmpl_id').get('id')).id,
                                    'barcode': False if variant.get('barcode') == '' or variant.get('barcode') == ' ' else variant.get('barcode'),
#                                     'volume': variant.get('volume'),
#                                     'weight': variant.get('weight'),
                                    'price_custom': variant.get('price_custom'),
                                    'attribute_value_ids': [(6, 0, attribute_value_ids)],
                                    'active': variant.get('active')
                                }

                                if variant.get('id') not in product_products_by_izi_id:
                                    self.env['product.product'].create(
                                        varian_values)
                                    if len(existing_product_id) == 1:
                                        existing_product_id.active = False
                                else:
                                    product_products_by_izi_id.get(
                                        variant.get('id')).write(varian_values)
                    elif res.get('code') == 401:
                        if retry_login:
                            self.retry_login(retry_login_count)
                            get_product_variants(
                                offset, limit, order_field, sort, retry_login_count, retry_login=False)
                    else:
                        break
                    self.env.cr.commit()
            except Exception as e:
                raise UserError(e)

        get_attribute_lines(offset, limit, order_field, sort,
                            retry_login_count, retry_login)
        get_product_variants(offset, limit, order_field, sort,
                            retry_login_count, retry_login)

        # for attline in attribute_lines_by_izi_id:
        #     attribute_lines_by_izi_id[attline].unlink()
    
    def get_staging_attribute_line_and_staging_variant(self, offset=0, limit=100, order_field='id', sort='asc', retry_login_count=3, retry_login=False,domain_url_attr=False, domain_url_var=False,mp_type=False):
         # Temporary Product Templates
        product_staging = self.env['product.staging'].search(
            [('izi_id', '!=', False), '|', ('active','=',True), ('active','=',False)])
        product_staging_by_izi_id = {}
        for pt in product_staging:
            product_staging_by_izi_id[pt.izi_id] = pt

        # Temporary Shopee Attributes
        sp_var_attributes = self.env['mp.shopee.item.var.attribute'].search(
            [('izi_id', '!=', False)])
        sp_var_attributes_by_izi_id = {}
        for at in sp_var_attributes:
            sp_var_attributes_by_izi_id[at.izi_id] = at

        # Temporary Shopee Attribute Values
        sp_var_attribute_values = self.env['mp.shopee.item.var.attribute.value'].search(
            [('izi_id', '!=', False)])
        sp_var_attribute_values_by_izi_id = {}
        for av in sp_var_attribute_values:
            sp_var_attribute_values_by_izi_id[av.izi_id] = av

         # Temporary Shopee Attribute Lines
        sp_var_attribute_lines = self.env['mp.shopee.attribute.line'].search(
            [('izi_id', '!=', False)])
        sp_var_attribute_lines_by_izi_id = {}
        for al in sp_var_attribute_lines:
            sp_var_attribute_lines_by_izi_id[al.izi_id] = al
        
        # Temporary Lazada Attributes
        lz_var_attributes = self.env['mp.lazada.category.attr'].search(
            [('izi_id', '!=', False),('is_sale_prop','=',True)])
        lz_var_attributes_by_izi_id = {}
        for at in lz_var_attributes:
            lz_var_attributes_by_izi_id[at.izi_id] = at

        # Temporary Lazada Attribute Values
        lz_var_attribute_values = self.env['mp.lazada.variant.value'].search(
            [('izi_id', '!=', False)])
        lz_var_attribute_values_by_izi_id = {}
        for av in lz_var_attribute_values:
            lz_var_attribute_values_by_izi_id[av.izi_id] = av

        # Temporary Lazada Attribute Lines
        lz_var_attribute_lines = self.env['mp.lazada.attribute.line'].search(
            [('izi_id', '!=', False)])
        lz_var_attribute_lines_by_izi_id = {}
        for al in lz_var_attribute_lines:
            lz_var_attribute_lines_by_izi_id[al.izi_id] = al

        # Temporary Product Products
        product_products = self.env['product.product'].search(
            [('izi_id', '!=', False), '|', ('active', '=', True), ('active', '=', False)])
        product_products_by_izi_id = {}
        for pp in product_products:
            product_products_by_izi_id[pp.izi_id] = pp

         # Temporary Product Variant Staging
        product_stg_var = self.env['product.staging.variant'].search(
            [('izi_id', '!=', False), '|', ('active', '=', True), ('active', '=', False)])
        product_stg_var_by_izi_id = {}
        for pp in product_stg_var:
            product_stg_var_by_izi_id[pp.izi_id] = pp
        
        def get_sp_attribute_lines(offset, limit, order_field, sort, retry_login_count, retry_login, domain_url_attr):
            try:
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
                        for atline in res.get('data'):
                            if atline.get('product_staging_id').get('id') not in product_staging_by_izi_id:
                                raise UserError(
                                    'Product Staging with this izi_id not imported yet.')                            

                            # Create Template Attribute Value First
                            sp_var_attribute_value_ids = []
                            for atvalue in atline.get('value_ids'):
                                if atvalue.get('id') not in sp_var_attribute_values_by_izi_id:
                                    raise UserError(
                                        'Attribute Value with this izi_id not imported yet.')
                                sp_var_attribute_value_ids.append(
                                    sp_var_attribute_values_by_izi_id.get(atvalue.get('id')).id)

                            # Create Template Attribute Line, Link to Product Template
                            if atline.get('attribute_id').get('id') not in sp_var_attributes_by_izi_id:
                                raise UserError(
                                    'Attributes with this izi_id not imported yet.')
                            if atline.get('id') not in sp_var_attribute_lines_by_izi_id:
                                self.env['mp.shopee.attribute.line'].create({
                                    'izi_id': atline.get('id'),
                                    'izi_md5': hashlib.md5(json.dumps(atline).encode('utf-8')).hexdigest(),
                                    'product_staging_id': product_staging_by_izi_id.get(atline.get('product_staging_id').get('id')).id,
                                    'attribute_id': sp_var_attributes_by_izi_id.get(atline.get('attribute_id').get('id')).id,
                                    'value_ids': [(6, 0, sp_var_attribute_value_ids)]
                                })
                            else:
                                if sp_var_attribute_lines_by_izi_id.get(atline.get('id')).izi_md5 != hashlib.md5(json.dumps(atline).encode('utf-8')).hexdigest():
                                    sp_var_attribute_lines_by_izi_id.get(atline.get('id')).write({
                                        'izi_md5': hashlib.md5(json.dumps(atline).encode('utf-8')).hexdigest(),
                                        'product_staging_id': product_staging_by_izi_id.get(atline.get('product_staging_id').get('id')).id,
                                        'attribute_id': sp_var_attributes_by_izi_id.get(atline.get('attribute_id').get('id')).id,
                                        'value_ids': [(6, 0, sp_var_attribute_value_ids)]
                                    })
                                sp_var_attribute_lines_by_izi_id.pop(atline.get('id'))
                    elif res.get('code') == 401:
                        if retry_login:
                            self.retry_login(retry_login_count)
                            get_sp_attribute_lines(
                                offset, limit, order_field, sort, retry_login_count, retry_login=False,domain_url_attr=domain_url_attr)
                        else:
                            break
                    else:
                        break
                    self.env.cr.commit()
            except Exception as e:
                raise UserError(e)
        
        def get_lz_attribute_lines(offset, limit, order_field, sort, retry_login_count, retry_login, domain_url_attr):
            try:
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
                        for atline in res.get('data'):
                            if atline.get('product_staging_id').get('id') not in product_staging_by_izi_id:
                                raise UserError(
                                    'Product Staging with this izi_id not imported yet.')                            

                            # Create Template Attribute Value First
                            lz_var_attribute_value_ids = []
                            for atvalue in atline.get('lz_variant_value_ids'):
                                if atvalue.get('id') not in lz_var_attribute_values_by_izi_id:
                                    raise UserError(
                                        'Attribute Value with this izi_id not imported yet.')
                                lz_var_attribute_value_ids.append(
                                    lz_var_attribute_values_by_izi_id.get(atvalue.get('id')).id)

                            # Create Template Attribute Line, Link to Product Template
                            if atline.get('attribute_id').get('id') not in lz_var_attributes_by_izi_id:
                                raise UserError(
                                    'Attributes with this izi_id not imported yet.')
                            if atline.get('id') not in lz_var_attribute_lines_by_izi_id:
                                self.env['mp.lazada.attribute.line'].create({
                                    'izi_id': atline.get('id'),
                                    'izi_md5': hashlib.md5(json.dumps(atline).encode('utf-8')).hexdigest(),
                                    'product_staging_id': product_staging_by_izi_id.get(atline.get('product_staging_id').get('id')).id,
                                    'attribute_id': lz_var_attributes_by_izi_id.get(atline.get('attribute_id').get('id')).id,
                                    'lz_variant_value_ids': [(6, 0, lz_var_attribute_value_ids)]
                                })
                            else:
                                if lz_var_attribute_lines_by_izi_id.get(atline.get('id')).izi_md5 != hashlib.md5(json.dumps(atline).encode('utf-8')).hexdigest():
                                    lz_var_attribute_lines_by_izi_id.get(atline.get('id')).write({
                                        'izi_md5': hashlib.md5(json.dumps(atline).encode('utf-8')).hexdigest(),
                                        'product_staging_id': product_staging_by_izi_id.get(atline.get('product_staging_id').get('id')).id,
                                        'attribute_id': lz_var_attributes_by_izi_id.get(atline.get('attribute_id').get('id')).id,
                                        'lz_variant_value_ids': [(6, 0, lz_var_attribute_value_ids)]
                                    })
                                lz_var_attribute_lines_by_izi_id.pop(atline.get('id'))
                    elif res.get('code') == 401:
                        if retry_login:
                            self.retry_login(retry_login_count)
                            get_lz_attribute_lines(
                                offset, limit, order_field, sort, retry_login_count, retry_login=False,domain_url_attr=domain_url_attr)
                        else:
                            break
                    else:
                        break
                    self.env.cr.commit()
            except Exception as e:
                raise UserError(e)
        
        def get_product_staging_variants(offset, limit, order_field, sort, retry_login_count, retry_login, domain_url_var):
            try:
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
                                    'product_id': product_products_by_izi_id.get(variant.get('product_id').get('id')).id
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
                    self.env.cr.commit()
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
        r = requests.post(self.name + '/ui/products/import/all', headers={
                          'X-Openerp-Session-Id': self.session_id, 'Content-type': 'application/json'}, json={'mp_list': mp_list})
        res = r.json()
        if r.status_code == 200:
            if res.get('result').get('status') != 200:
                raise UserError('Error when IZI get product from marketplace')
        else:
            raise UserError('Error when IZI get product from marketplace')

    def get_products(self):
        try:
            self.with_context(create_product_product=False).get_records('product.template', domain_code='all_active', force_update=True, limit=500)
            self.get_records('product.image', force_update=True, limit=500)
            self.get_records('product.template.wholesale', force_update=True, limit=500)
            self.with_context(get_products=True).get_records('product.staging', force_update=True, domain_code='all_active', limit=500)
            self.get_records('product.image.staging', force_update=True, limit=500)
            self.get_records('product.staging.wholesale', force_update=True, limit=500)

            self.get_records('product.product', force_update=True, domain_code='all_active', limit=500)
            self.get_records('mp.tokopedia.variant.value', force_update=True, limit=500)
            self.get_records('mp.tokopedia.attribute.line', force_update=True, limit=500)
            self.get_records('product.staging.variant', force_update=True, limit=500)

            self.after_get_products()
            # self.get_attribute_line_and_variant(custom_domain=1)

            self.get_staging_attribute_line_and_staging_variant(limit=500)
            self.get_records('mp.shopee.item.attribute.val', force_update=True, limit=500)
            self.get_records('mp.shopee.item.logistic', force_update=True, limit=500)

            self.with_context(create_product_attr=True).get_records('mp.lazada.product.attr',force_update=True, limit=500)
        except Exception as e:
            raise UserError(e)

    def get_product_category(self):
        self.get_records('mp.tokopedia.category',
                         domain_url="[('parent_id', '=', False)]", limit=1000)
        self.get_records('mp.tokopedia.category',
                         domain_url="[('parent_id', '!=', False), ('child_ids', '!=', False)]", limit=1000)
        self.get_records('mp.tokopedia.category',
                         domain_url="[('child_ids', '=', False)]", limit=1000)
        self.get_records('mp.shopee.item.attribute.option', limit=1000)
        self.get_records('mp.shopee.item.attribute', limit=1000, domain_code='all_active')
        self.get_records('mp.shopee.item.category', limit=1000, domain_code='has_children')

        if not self.env['mp.lazada.brand'].search([]):
            self.get_records('mp.lazada.brand', limit=10000)
        self.get_records('mp.lazada.category.attr.opt', limit=1000)
        self.get_records('mp.lazada.variant.value', limit=1000)
        self.get_records('mp.lazada.category', limit=1000, domain_code='has_children')
        self.get_records('mp.lazada.category.attr', limit=1000)



    def get_product_dependency(self):
        self.get_records('mp.tokopedia.shop')
        self.get_records('mp.tokopedia.etalase', domain_code='all_active')

        self.trigger_import_product_izi()

        self.get_records('mp.tokopedia.category.value', limit=1000)
        self.get_records('mp.tokopedia.category.unit', limit=1000)
        self.get_records('mp.tokopedia.category.variant', limit=1000)

        self.get_records('mp.shopee.logistic.size', limit=1000)
        self.get_records('mp.shopee.logistic', limit=1000)
        self.get_records('mp.shopee.shop.logistic', limit=1000)

        self.get_records('mp.shopee.item.var.attribute', limit=1000)
        self.get_records('mp.shopee.item.var.attribute.value', limit=1000)

    def sp_get_attribute_category(self,category_id=False,mp_id=False):
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

            def process_model(model_name, data):
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
                            if model_name == 'mp.shopee.item.attribute':
                                attr_ids.append(record.id)
                        else:
                            values = self.mapping_field(
                                model_name, res_values, update=True)
                            record.write(values)
                            if model_name == 'mp.shopee.item.attribute':
                                attr_ids.append(record.id)
                    else:
                        values = self.mapping_field(
                            model_name, res_values, update=False)
                        obj = self.env[model_name].create(values)
                        if model_name == 'mp.shopee.item.attribute':
                            attr_ids.append(obj.id)
                            
                    self.env.cr.commit()
                
                if model_name == 'mp.shopee.item.attribute':
                    return attr_ids
            
            process_model('mp.shopee.item.attribute.option', res['options'])
            attribute_proc = process_model('mp.shopee.item.attribute', res['data'])

            category = self.env['mp.shopee.item.category'].search([('izi_id', '=', category_id)])
            if category and attribute_proc:
                category.write({
                    'attributes': [(6, 0, attribute_proc)]
                })
                self.env.cr.commit()
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
                            
                        if self.env.user and model_name == 'sale.order':
                            self.env.user.notify_info('New Order From Marketplace')
                    self.env.cr.commit()
                
                if model_name == 'mp.shopee.item.attribute':
                    return attr_ids
            
            process_model('mp.lazada.category.attr.opt', res['options'])
            attribute_proc = process_model('mp.lazada.category.attr', res['data'])

            # category = self.env['mp.lazada.category'].search([('izi_id','=',category_id)])
            # # if category and attribute_proc :
            # #     category.write({
            # #         'attr_ids': [(6, 0, attribute_proc)]
            # #     })
                # self.env.cr.commit()
        return res

        
