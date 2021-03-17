# -*- coding: utf-8 -*-
# import base64
from odoo import models, fields, api, tools, _
from odoo.tools import pycompat
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

    izi_id = fields.Integer(required=True)
    name = fields.Char()
    default_code = fields.Char()
    product_tmpl_id = fields.Many2one('product.template', 'Product Template')
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
        'product.staging', 'product_template_id', 'Product Staging',
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
    mp_shopee_ids = fields.Many2many(
        'mp.shopee', string='Shopee Account',
        domain=['|', ('active', '=', False), ('active', '=', True), ],
        context={'active_test': False})
    mp_lazada_ids = fields.Many2many(
        'mp.lazada', string='Lazada Account',
        domain=['|', ('active', '=', False), ('active', '=', True), ],
        context={'active_test': False})
    field_adapter_type = fields.Selection(
        [('consu', 'Consumable'),
         ('service', 'Service'), ('product', 'Stockable Product')],
        'Product Type Adapter', compute='set_type_adapter')
    product_wholesale_ids = fields.One2many(
        'product.template.wholesale', 'product_tmpl_id')
    default_code = fields.Char('Default Code')
    condition = fields.Selection([
        ('1', 'NEW'),
        ('2', 'USED')
    ], string="Condition")
    min_order = fields.Integer('Mininum Order')

    izi_id = fields.Integer('Izi ID', copy=False)
    izi_md5 = fields.Char()

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
                raise UserError('Buatkan minimal 1 webhook server!')
            uploaded = server.upload_products(obj._name, obj.id)
            if uploaded[0]:
                obj.message_post(body=uploaded[1], subject=_("Upload to IZI"))
            else:
                raise ValidationError(uploaded[1])


class ProductProduct(models.Model):
    _inherit = 'product.product'

    price_custom = fields.Float('Price Custom')
    product_variant_stg_id = fields.One2many(
        'product.staging.variant', 'prdp_ids', 'Product Variant Staging')

    izi_id = fields.Integer('Izi ID', copy=False)
    izi_md5 = fields.Char()

    def upload_self(self):
        for obj in self:
            server = self.env['webhook.server'].search(
                [('active', 'in', [False, True])],
                limit=1, order='write_date desc')
            if not server:
                raise UserError('Buatkan minimal 1 webhook server!')
            uploaded = server.upload_products(obj._name, obj.id)
            if uploaded[0]:
                obj.message_post(body=uploaded[1], subject=_("Upload to IZI"))
            else:
                raise ValidationError(uploaded[1])


class ProductImage(models.Model):
    _name = 'product.image'
    _description = 'Product Image [duplicate website_sale]'

    name = fields.Char()
    variant_name = fields.Char('New Name' )
    image = fields.Binary(
        "Image", attachment=True,
        help='Clear me to reset image to already uploaded image.')
    image_variant = fields.Binary(
        'Preview', attachment=False, compute='_compute_images',
        inverse='_set_image', )

    product_tmpl_id = fields.Many2one(
        'product.template', 'Related Product', copy=True)
    
    url_external = fields.Char('URL External')

    izi_id = fields.Integer('Izi ID', copy=False)
    izi_md5 = fields.Char()

    def _compute_images(self):
        for image in self:
            if image.name and 'http' in image.name:
                try:
                    image.image_variant = b64encode(requests.get(image.name).content).replace(b'\n', b'')
                    image.image = image.image_variant
                except Exception:
                    pass
            else:
                image.image_variant = tools.image_resize_image_big(image.image)

    def _set_image(self):
        self.name = self.variant_name
        self._set_image_value(self.image_variant)

    def _set_image_value(self, value):
        if isinstance(value, pycompat.text_type):
            value = value.encode('ascii')
        image = tools.image_resize_image_big(value)
        if self.product_tmpl_id and self.product_tmpl_id.product_variant_count <= 1:
            self.product_tmpl_id.image = image
        self.image = image


class ProductImageStaging(models.Model):
    _name = 'product.image.staging'

    name = fields.Char('Name')
    variant_name = fields.Char('New Name')
    image_variant = fields.Binary(
        "Update/Reset Image", attachment=True,
        help='Clear me to reset image to already uploaded image.')
    image = fields.Binary(
        'Preview', attachment=False, compute='_compute_images',
        inverse='_set_image', )
    product_stg_id = fields.Many2one('product.staging')
    url_external = fields.Char('URL External')
    
    izi_id = fields.Integer('Izi ID', copy=False)
    izi_md5 = fields.Char()

    @api.depends('variant_name')
    @api.onchange('variant_name')
    def compute_name(self):
        for obj in self:
            if obj.variant_name and not obj.name:
                obj.name = obj.variant_name

    @api.depends('name', 'image_variant')
    def _compute_images(self):
        for image in self:
            if image.image_variant:
                image.image = image.image_variant
            elif image.name and 'https' in image.name:
                img_req = requests.get(image.name)
                if img_req.status_code == 200:
                    img = b64encode(img_req.content).replace(b'\n', b'')
                    image.image = img

    # def _set_image(self):
    #     value = self.image_variant
    #     if not value:
    #         return
    #     if isinstance(self.image_variant, pycompat.text_type):
    #         value = value.encode('ascii')
    #     image = tools.image_resize_image_big(value)
    #     self.image = image

    def _set_image(self):
        self._set_image_value(self.image_variant)

    def _set_image_value(self, value):
        if not value:
            image = False
        elif isinstance(value, pycompat.text_type):
            value = value.encode('ascii')
            image = tools.image_resize_image_big(value)
            self.image = image



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

# class ProductTemplateAttributeValue(models.Model):
#     _inherit = 'product.template.attribute.value'

#     izi_id = fields.Integer('Izi ID')
#     izi_md5 = fields.Char()


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

    def get_product_mapping(self):
        # GET existing 
        pm_by_izi_id = {}
        product_mappings = self.env['product.mapping'].sudo().search([])
        for pm in product_mappings:
            if pm.izi_id:
                pm_by_izi_id[pm.izi_id] = pm
        # GET existing product.template
        pt_by_name = {}
        pt_by_default_code = {}
        product_templates = self.env['product.template'].sudo().search([])
        for pt in product_templates:
            if pt.izi_id:
                # Skip product template with izi_id
                continue
            if pt.name:
                pt_by_name[pt.name] = pt
            if pt.default_code:
                pt_by_default_code[pt.default_code] = pt
        
        loop = True
        offset = 0
        limit = 1000
        while loop:
            r = requests.get(self.name + '/api/ui/read/list-detail/izi-products?offset=%s&limit=%s' % (
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
                    product_template = False
                    if pd['name'] in pt_by_name:
                        product_template = pt_by_name[pd['name']]
                    if pd['default_code'] in pt_by_default_code:
                        product_template = pt_by_default_code[pd['default_code']]
                    # Create or Update
                    if pd['id'] not in pm_by_izi_id:
                        values = {
                            'izi_id': pd['id'],
                            'name': pd['name'],
                            'default_code': pd['default_code'],
                            'server_id': self.id,
                        }
                        if product_template:
                            values['product_tmpl_id'] = product_template.id
                        self.env['product.mapping'].sudo().create(values)
                    else:
                        values = {
                            'izi_id': pd['id'],
                            'name': pd['name'],
                            'default_code': pd['default_code'],
                            'server_id': self.id,
                        }
                        if not pm_by_izi_id[pd['id']].product_tmpl_id and product_template:
                            values['product_tmpl_id'] = product_template.id
                        pm_by_izi_id[pd['id']].write(values)
            else:
                loop = False

    def get_product_categories(self, loop=True, offset=0, limit=100, order_field='id', sort='asc', custom_domain=0, retry_login_count=3, retry_login=True):

        def recursion_create_parent_product_category(exist_category_by_izi_id, res_category_values, category_id, retry_login_count, retry_login):
            try:
                if not self.session_id:
                    self.retry_login(retry_login_count)
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
                if not self.session_id:
                    self.retry_login(retry_login_count)
                r = requests.get(self.name + '/api/ui/read/list-detail/izi-product-categories?offset=%s&limit=%s&order=%s&sort=%s&custom_domain=%s' % (
                    str(offset), str(limit), order_field, sort, str(custom_domain)),
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

    def get_tokopedia_categories(self, loop=True, offset=0, limit=100, order_field='id', sort='asc', custom_domain=0, retry_login_count=3, retry_login=False):

        def recursion_create_parent_tokopedia_category(exist_category_by_izi_id, res_category_values, category_id, retry_login_count, retry_login):
            try:
                if not self.session_id:
                    self.retry_login(retry_login_count)
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
                if not self.session_id:
                    self.retry_login(retry_login_count)
                r = requests.get(self.name + '/api/ui/read/list-detail/izi-tokopedia-categories?offset=%s&limit=%s&order=%s&sort=%s&custom_domain=%s' % (
                    str(offset), str(limit), order_field, sort, str(custom_domain)),
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

    def get_attribute_line_and_variant(self, loop=True, offset=0, limit=100, order_field='id', sort='asc', custom_domain=0, retry_login_count=3, retry_login=False):
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
            [('izi_id', '!=', False)])
        product_products_by_izi_id = {}
        for pp in product_products:
            product_products_by_izi_id[pp.izi_id] = pp

        # GET Attribute Lines
        def get_attribute_lines(loop, offset, limit, order_field, sort, custom_domain, retry_login_count, retry_login):
            try:
                while loop:
                    if not self.session_id:
                        self.retry_login(retry_login_count)
                    r = requests.get(self.name + '/api/ui/read/list-detail/product.attribute.line?offset=%s&limit=%s&order=%s&sort=%s&custom_domain=%s' % (
                        str(offset), str(limit), order_field, sort, str(custom_domain)),
                        headers={'X-Openerp-Session-Id': self.session_id}
                    )
                    res = r.json() if r.status_code == 200 else {}
                    if res.get('code') == 401:
                        if retry_login:
                            self.retry_login(retry_login_count)
                            get_attribute_lines(
                                loop, offset, limit, order_field, sort, custom_domain, retry_login_count, retry_login=False)
                    if res.get('code') == 200:
                        if len(res.get('data')) == 0:
                            loop = False
                        else:
                            offset += limit
                        for atline in res.get('data'):
                            if atline.get('product_tmpl_id').get('id') not in product_templates_by_izi_id:
                                raise UserError(
                                    'Product Template with this izi_id not imported yet.')

                            # Create Template Attribute Value First
                            attribute_value_ids = []
                            for atvalue in atline.get('value_ids'):
                                if atvalue.get('id') not in attribute_values_by_izi_id:
                                    raise UserError(
                                        'Attribute Value with this izi_id not imported yet.')
                                attribute_value_ids.append(
                                    attribute_values_by_izi_id.get(atvalue.get('id')).id)

                            # Create Template Attribute Line, Link to Product Template
                            if atline.get('attribute_id').get('id') not in attributes_by_izi_id:
                                raise UserError(
                                    'Attributes with this izi_id not imported yet.')
                            if atline.get('id') not in attribute_lines_by_izi_id:
                                attribute_line = self.env['product.template.attribute.line'].create({
                                    'izi_id': atline.get('id'),
                                    'izi_md5': hashlib.md5(json.dumps(atline).encode('utf-8')).hexdigest(),
                                    'product_tmpl_id': product_templates_by_izi_id.get(atline.get('product_tmpl_id').get('id')).id,
                                    'attribute_id': attributes_by_izi_id.get(atline.get('attribute_id').get('id')).id,
                                    'value_ids': [(6, 0, attribute_value_ids)]
                                })
                            else:
                                if attribute_lines_by_izi_id.get(atline.get('id')).izi_md5 != hashlib.md5(json.dumps(atline).encode('utf-8')).hexdigest():
                                    attribute_lines_by_izi_id.get(atline.get('id')).write({
                                        'izi_md5': hashlib.md5(json.dumps(atline).encode('utf-8')).hexdigest(),
                                        'product_tmpl_id': product_templates_by_izi_id.get(atline.get('product_tmpl_id').get('id')).id,
                                        'attribute_id': attributes_by_izi_id.get(atline.get('attribute_id').get('id')).id,
                                        'value_ids': [(6, 0, attribute_value_ids)]
                                    })
                                attribute_line = attribute_lines_by_izi_id.get(atline.get('id'))

                            # Unlink existing template attribute value
                            # attribute_line.product_template_value_ids.unlink()

                            # Create Template Attribute Value
                            for atvalue in atline.get('value_ids'):
                                if atvalue.get('id') not in attribute_values_by_izi_id:
                                    raise UserError(
                                        'Attribute Value with this izi_id not imported yet.')
                                atvalue_id = attribute_values_by_izi_id.get(atvalue.get('id')).id
                                found = False
                                for ptv in attribute_line.product_template_value_ids:
                                    if atvalue_id == ptv.product_attribute_value_id.id:
                                        found = True
                                if not found:
                                    template_attribute_value = self.env['product.template.attribute.value'].create({
                                        'name': attribute_values_by_izi_id.get(atvalue.get('id')).name,
                                        'product_attribute_value_id': atvalue_id,
                                        'product_tmpl_id': product_templates_by_izi_id.get(atline.get('product_tmpl_id').get('id')).id,
                                        'attribute_line_id': attribute_line.id,
                                    })

                    self.env.cr.commit()
            except Exception as e:
                raise UserError(e)

        # GET Product Product to Update izi_id
        # GET Attribute Lines
        def get_product_variants(loop, offset, limit, order_field, sort, custom_domain, retry_login_count, retry_login):
            try:
                # Create Variants
                i = 0
                for izi_id in product_templates_by_izi_id:
                    if product_templates_by_izi_id[izi_id].attribute_line_ids:
                        i += 1
                        print('Create Variants %s' % i)
                        product_templates_by_izi_id[izi_id]._create_variant_ids()
                # Product Template Attribute Value By Template ID By Product Attribute Value ID
                ptav_by_tmpl_id_by_pav_id = {}
                for ptav in self.env['product.template.attribute.value'].sudo().search([]):
                    if ptav.product_tmpl_id.id not in ptav_by_tmpl_id_by_pav_id:
                        ptav_by_tmpl_id_by_pav_id[ptav.product_tmpl_id.id] = {}
                    ptav_by_tmpl_id_by_pav_id[ptav.product_tmpl_id.id][ptav.product_attribute_value_id.id] = ptav
                while loop:
                    if not self.session_id:
                        self.retry_login(retry_login_count)
                    r = requests.get(self.name + '/api/ui/read/list-detail/izi-product-variants?offset=%s&limit=%s&order=%s&sort=%s&custom_domain=%s' % (
                        str(offset), str(limit), order_field, sort, str(custom_domain)),
                        headers={'X-Openerp-Session-Id': self.session_id}
                    )
                    res = r.json() if r.status_code == 200 else {}
                    if res.get('code') == 401:
                        if retry_login:
                            self.retry_login(retry_login_count)
                            get_product_variants(loop, offset, limit, order_field,
                                                 sort, custom_domain, retry_login_count, retry_login=False)
                    if res.get('code') == 200:
                        if len(res.get('data')) == 0:
                            loop = False
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
                            existing_template = product_templates_by_izi_id[template_id]
                            existing_variants = self.env['product.product'].search(
                                [('product_tmpl_id.izi_id', '=', template_id)])
                            for variant in variants:
                                attribute_value_ids = []
                                template_attribute_value_ids = []
                                for attval in variant.get('attribute_value_ids'):
                                    if attval.get('id') not in attribute_values_by_izi_id:
                                        raise UserError(
                                            'Attribute Value with this izi_id not imported yet.')
                                    av_id = attribute_values_by_izi_id.get(attval.get('id')).id
                                    attribute_value_ids.append(av_id)
                                    if av_id in ptav_by_tmpl_id_by_pav_id[existing_template.id]:
                                        template_attribute_value_ids.append(ptav_by_tmpl_id_by_pav_id[existing_template.id][av_id].id)
                                
                                # Search For Variant That Has Those Template Attribute Values
                                right_variant = False
                                for ev in existing_variants:
                                    if set(ev.product_template_attribute_value_ids.ids) == set(template_attribute_value_ids):
                                        print('Found the right product.product!')
                                        right_variant = ev
                                if not right_variant:
                                    raise UserError(
                                        'Variant with this combination is not created yet.')

                                varian_values = {
                                    'izi_id': variant.get('id'),
                                    'default_code': variant.get('default_code'),
                                    'product_tmpl_id': product_templates_by_izi_id.get(variant.get('product_tmpl_id').get('id')).id,
                                    'barcode': False if variant.get('barcode') == '' or variant.get('barcode') == ' ' else variant.get('barcode'),
                                    'volume': variant.get('volume'),
                                    'weight': variant.get('weight'),
                                    'price_custom': variant.get('price_custom'),
                                }
                                right_variant.write(varian_values)
                    self.env.cr.commit()
            except Exception as e:
                raise UserError(e)

        get_attribute_lines(loop, offset, limit, order_field,
                            sort, custom_domain, retry_login_count, retry_login)
        get_product_variants(loop, offset, limit, order_field,
                             sort, custom_domain, retry_login_count, retry_login)
