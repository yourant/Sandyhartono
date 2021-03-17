# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import time
import json
import hashlib
import logging
import requests
from random import choice
from string import digits, ascii_letters
from datetime import datetime, timedelta
from base64 import b64encode, b64decode
# from math import ceil
from odoo import tools
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta as delta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

_logger = logging.getLogger(__name__)
# _chunk = lambda lst, n: [lst[i:i + n] for i in range(0, len(lst), n)]

# Helper Dictionary
code_by_model_name = {
    'uom.uom': 'product.uom',
    'sale.order': 'izi-orders',
    'res.partner': 'izi-partners',
    'mp.shop.address': 'izi-shop-address',
    'sale.order.cancel.reason': 'izi-sale-cancel-reason',
    'sale.order.pickup.info' : 'izi-pickup-info',

    'mp.tokopedia': 'izi-tokopedia',
    'mp.tokopedia.shop': 'izi-tokopedia-shop',
    'mp.tokopedia.etalase': 'izi-tokopedia-etalase',
    'mp.tokopedia.category': 'izi-tokopedia-categories',
    'mp.tokopedia.category.variant': 'izi-tokopedia-category-variants',
    'mp.tokopedia.category.unit': 'izi-tokopedia-category-units',
    'mp.tokopedia.category.value': 'izi-tokopedia-category-values',
    'mp.tokopedia.product': 'izi-tokopedia-products',

    'mp.shopee': 'izi-shopee',
    'mp.shopee.item.category': 'izi-shopee-item-category',
    'mp.shopee.item.attribute': 'izi-shopee-item-attribute',
    'mp.shopee.item.attribute.option': 'izi-shopee-item-attribute-option',
    'mp.shopee.item.attribute.val': 'izi-shopee-item-attribute-val',
    'mp.shopee.logistic': 'izi-shopee-logistc',
    'mp.shopee.logistic.size': 'izi-shopee-logistic-size',
    'mp.shopee.shop.logistic': 'izi-shopee-shop-logistc',
    'mp.shopee.item.logistic': 'izi-shopee-item-logistic',


    'product.category': 'izi-product-categories',
    'product.attribute': 'izi-product-attributes',
    'product.attribute.unit': 'izi-product-attribute-units',
    'product.attribute.value': 'izi-product-attribute-values',
    'product.template.attribute.line': 'product.attribute.line',
    'product.template': 'izi-products',
    'product.product': 'izi-product-variants',
    'product.staging': 'izi-product-stagings',
    'product.image.staging': 'izi-product-image-staging',
    'product.staging.variant': 'izi-product-staging-variants',
    'product.template.wholesale': 'izi-product-wholesales',
    'product.staging.wholesale': 'izi-product-staging-wholesales',
    'product.brand': 'izi-brands',
    'product.image': 'izi-product-image',
}

existing_fields_by_model_name = {
    'product.product': ['default_code', 'barcode'],
    'stock.warehouse': ['code'],
    'res.company': ['name'],
    'res.users': ['name']
}

removed_fields = {
    'product.product': ['uom_id', 'company_id'],
    'product.template': ['image_small', 'image_medium'],
    'product.staging': ['izi_md5', 'mp_type']
}

upload_fields = {
    'product.brand': [
        'name', 'active',
    ],
    'product.template': [
        'active', 'qty_available', 'name', 'categ_id', 'image',
        'default_code', 'barcode', 'description_sale', 'weight', 'length',
        'height', 'width', 'list_price', 'package_content', 'type',
        'product_staging_ids', 'product_image_ids', 'product_wholesale_ids',
    ],
    'product.staging': [
        'active', 'barcode', 'brand_id', 'default_code', 'description_sale',
        'height', 'is_active', 'length', 'list_price', 'min_order',
        'mp_tokopedia_id', 'name', 'package_content',
        'product_template_id', 'product_variant_stg_id',
        'product_image_staging_ids', 'product_wholesale_ids',
        'tp_active_status', 'tp_available_status', 'tp_category_id',
        'tp_condition', 'tp_etalase_id', 'tp_weight_unit', 'weight', 'width',
        'qty_available'
    ],
    # 'varian_list': [
    #     'attribute1', 'attribute_value1', 'attribute2', 'attribute_value2',
    #     'price_custom', 'qty_available', 'default_code', 'image', 'is_active'
    # ],
    'product.template.wholesale': [
        'min_qty', 'max_qty', 'price_wholesale', 'product_tmpl_id',
    ],
    'product.staging.wholesale': [
        'min_qty', 'max_qty', 'price_wholesale', 'product_stg_id',
    ],
    'product.product': [
        'active', 'product_tmpl_id', 'standard_price',
        'qty_available', 'name', 'categ_id',
        'default_code', 'barcode', 'description_sale', 'weight', 'length',
        'height', 'width', 'list_price', 'package_content', 'type',
        'product_staging_ids', 'product_image_ids',
    ],
    'product.image': [
        'image', 'name', 'product_tmpl_id',
    ],
    'product.image.staging': [
        'image', 'name', 'product_stg_id',
    ],
    'product.staging.variant': [
        'lst_price', 'volume', 'weight', 'default_code', 'active',
        'mp_external_id', 'prdp_ids',
        'qty_available', 'price_custom', 'product_stg_id',
    ],
}
restricted_fields = [
    'create_uid', 'write_uid', 'create_date', 'write_date',
    '__last_update',
]

processed_model_with_many2one_itself = [
    # 'mp.tokopedia.category', 'product.category',
]

class IrModelFields(models.Model):
    _inherit = 'ir.model.fields'

    webhook = fields.Boolean(compute='_get_webhook_from_model')

    def _get_webhook_from_model(self):
        for rec in self:
            rec.webhook = rec in rec.model_id.webhook_field_ids

    def toggle_webhook(self):
        for fld in self:
            if fld.webhook:
                fld.model_id.webhook_field_ids = [(3, fld.id)]
            else:
                fld.model_id.webhook_field_ids = [(4, fld.id)]


class IrModel(models.Model):
    _name = 'ir.model'
    _inherit = 'ir.model'

    webhook = fields.Boolean(compute='_get_webhook')
    webhook_mq_ids = fields.One2many('webhook.server.mq', 'res_model_id')
    webhook_field_ids = fields.Many2many(
        'ir.model.fields', domain="[('model_id','=',id), ]")
    webhook_ids = fields.Many2many(
        'webhook.server', 'webhook_model_rel', 'model_id', 'webhook_id')

    def set_default_webhook(self):
        for mdl in self:
            default_fld = upload_fields.get(mdl.model)
            if default_fld:
                fld_ids = mdl.field_id.filtered(
                    lambda fl: fl.name in default_fld)
                mdl.webhook_field_ids = [(6, 0, fld_ids.ids)]

    def _get_webhook(self):
        for rec in self:
            rec.webhook = True if rec.webhook_ids else False

    def init_webhook(self):
        model_objs = [self.env[model_name] for model_name in self.mapped(
            'model')]
        for model_obj in model_objs:
            model_obj.search([]).with_context(lazy=True).create_webhook()


class Base(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def create(self, vals):
        res = super(Base, self).create(vals)
        if vals and self._context.get('webhook', True):
            res.create_webhook(fields=list(vals.keys()))
        return res

    # def write(self, vals):
    #     res = super(Base, self).write(vals)
    #     if vals and self._context.get('webhook', True):
    #         self.create_webhook(fields=list(vals.keys()))
    #     return res

    def unlink(self):
        if self._context.get('webhook', True):
            self.create_webhook(method='unlink')
        res = super(Base, self).unlink()
        return res

    def create_webhook(self, **kw):
        method = kw.get('method', 'export')
        model_obj = self.env['ir.model']
        model_id = model_obj._get(self._name)
        recs = self.filtered(lambda r: isinstance(r.id, int))
        if recs and model_id.webhook:
            if method == 'export':
                field_list = kw.get('fields', list(self._fields.keys()))
                field_webhook = model_id.webhook_field_ids.mapped('name')
                field_list = list(
                    set(field_list) - (set(field_list) - set(field_webhook)))
                if field_list:
                    normal_keys = []
                    x2many_keys = []
                    compat_keys = []
                    for key in field_list:
                        field = self._fields[key]
                        if field.type in ['one2many', 'many2one', 'many2many', 'reference']:
                            if self._context.get('webhook_nested'):
                                comodel_id = recs.mapped(key)
                                if model_obj._get(comodel_id._name).webhook:
                                    comodel_id.create_webhook()
                            key = '%s/id' % (key)
                        if field.type in ['one2many' 'many2many']:
                            x2many_keys.append(key)
                        elif field.name == 'type' and self._name in ['product.template', 'product.product']:
                            fld_adapter = 'field_adapter_' + key
                            if fld_adapter in self._fields.keys():
                                compat_keys.append(fld_adapter)
                            normal_keys.append(key)
                        else:
                            normal_keys.append(key)
                    if normal_keys:
                        normal_keys.append('id')
                        normal_keys = list(set(normal_keys))
                        new_normal_keys = list(normal_keys)
                        for ckey in compat_keys:
                            idx = new_normal_keys.index(ckey[14:])
                            new_normal_keys[idx] = ckey
                        for rec in recs:
                            webhook = {
                                'version': 12,
                                'model': self._name,
                                'method': method,
                                'keys': normal_keys,
                                **rec.export_data(new_normal_keys)
                            }
                            model_id.mapped('webhook_ids')\
                                .filtered(
                                    lambda r:
                                        (r.id in self._context.get(
                                            'webhook_ids'))
                                        if self._context.get('webhook_ids')
                                        else True)\
                                .write({
                                    'mq_ids': [(0, 0, {
                                        'res_model_id': model_id.id,
                                        'res_ids': '%s' % (rec.ids),
                                        'request': json.dumps(
                                            webhook, indent=2)
                                    })]
                                })
                    if x2many_keys:
                        x2many_keys.append('id')
                        x2many_keys = list(set(x2many_keys))
                        for rec in recs:
                            webhook = {
                                'version': 12,
                                'model': self._name,
                                'method': method,
                                'keys': x2many_keys,
                                **rec.export_data(x2many_keys)
                            }
                            model_id.mapped('webhook_ids')\
                                .filtered(
                                    lambda r:
                                        (r.id in self._context.get(
                                            'webhook_ids'))
                                        if self._context.get('webhook_ids')
                                        else True)\
                                .write({
                                    'mq_ids': [(0, 0, {
                                        'res_model_id': model_id.id,
                                        'res_ids': '%s' % (rec.ids),
                                        'request': json.dumps(
                                            webhook, indent=2)
                                    })]
                                })
            elif method == 'unlink':
                keys = ['id', 'display_name']
                webhook = {
                    'version': 12,
                    'model': self._name,
                    'method': method,
                    'keys': keys,
                    **recs.export_data(keys)
                }
                model_id.mapped('webhook_ids')\
                    .filtered(
                        lambda r:
                            self._context.get('webhook_ids')
                            and (r.id in self._context.get('webhook_ids'))
                            or True)\
                    .write({
                        'mq_ids': [(0, 0, {
                            'res_model_id': model_id.id,
                            'res_ids': '%s' % (recs.ids),
                            'request': json.dumps(webhook, indent=2)
                        })]
                    })
            elif method == 'patch':
                patch_method = kw.get('patch_method', None)
                if not (patch_method and recs.ids):
                    return
                keys = ['id']
                webhook = {
                    'version': 12,
                    'model': self._name,
                    'method': patch_method,
                    'keys': keys,
                    **recs.export_data(keys),
                }
                model_id.mapped('webhook_ids').filtered(
                    lambda r: (r.id in self._context.get('webhook_ids'))
                    if self._context.get('webhook_ids') else True)\
                    .write({
                        'mq_ids': [(0, 0, {
                            'is_patch': True,
                            'res_model_id': model_id.id,
                            'res_ids': '%s' % (recs.ids),
                            'request': json.dumps(webhook, indent=2)
                        })]
                    })

class WebhookGetRecordsWizard(models.TransientModel):
    _name = 'webhook.get.records.wizard'

    model_id = fields.Many2one('ir.model', 'Model')
    webhook_server_id = fields.Many2one('webhook.server', 'Webhook Server')

    def process_wizard(self):
        self.webhook_server_id.get_records(self.model_id.model)


class WebhookGetCustomModelRecordsWizard(models.TransientModel):
    _name = 'webhook.get.custom.model.records.wizard'

    custom_model_name = fields.Char('Custom Model Name')
    custom_model_url = fields.Char('Custom Model Url')
    webhook_server_id = fields.Many2one('webhook.server', 'Webhook Server')


    def process_wizard(self):
        self.webhook_server_id.get_records(
            self.custom_model_name, self.custom_model_url)

class WebhookServer(models.Model):
    _name = 'webhook.server'
    _description = 'Webhook Server'

    __CLIENT_URL__ = '{}/webhook/client'
    __TOKEN_URL__ = '{}/api/v1/oauth2'
    __PATCH_URL__ = '{}/webhook/patch'

    name = fields.Char('Client URL', required=True)
    username = fields.Char('Username', required=True)
    password = fields.Char('Password', required=True)
    compress = fields.Boolean()

    mq_ids = fields.One2many('webhook.server.mq', 'config_id')
    model_ids = fields.Many2many(
        'ir.model', 'webhook_model_rel', 'webhook_id', 'model_id')
    token_ids = fields.One2many('webhook.server.token', 'config_id')
    access_token = fields.Char('OAuth Token')
    expires_at = fields.Datetime()
    session_id = fields.Char('Session')

    active = fields.Boolean(default=False)
    is_sync = fields.Boolean(default=True)

    cron_id = fields.Many2one('ir.cron', 'Scheduler')
    #
    # API Auth
    #
    def check_auth(self):
        if not self.name:
            raise UserError('URL not set.')
        if not self.username:
            raise UserError('Username not set.')
        if not self.password:
            raise UserError('Password not set.')

    def auth_login(self):
        self.check_auth()
        r = requests.post(self.name + '/api/ui/login', json={
            'login': self.username,
            'password': self.password,
        })
        res = json.loads(r.text) if r.status_code == 200 else {}
        if res:
            data = res.get('data', {})
            session_id = data.get('session_id', False)
            error = data.get('error_descrip')
            if error:
                raise ValidationError(error + ' for Webhook server : '+ str(self))
            self.session_id = session_id
            return self.session_id
        return False

    def retry_login(self, count_retry):
        for i in range(count_retry):
            session_id = self.auth_login()
            if session_id:
                return session_id
        raise UserError('Please Login Manually.')
        return False

    #
    # API Get Specific
    #
    def initialize(self):
        self.auth_login()
        self.get_records('mp.tokopedia', custom_domain=1)
        self.get_records('mp.shopee', custom_domain=1)
        self.get_product_category()
        self.get_product_dependency()
        self.get_orders_dependency()
        self.get_product_mapping()
    
    def sync_product(self):
        self.get_products()
        self.import_stock()

    def sync_order(self):
        self.get_orders()

    def sync_latest_order(self):
        self.get_orders(domain_code='last_hour')
    
    @api.model
    def sync_order_model(self):
        servers = self.search([])
        for server in servers:
            server.sync_latest_order()
    
    def get_orders(self, domain_code=False):
        self.get_records('sale.order', domain_code=domain_code)
        self.get_records('sale.order.pickup.info')

        # Activate cron for this button
        # if not self._context.get('run_by_cron'):
        #     cron = self.env.ref('juragan_webhook.cron_webhook_get_order')
        #     if not cron.active:
        #         cron.write({'active': True})

    def get_orders_dependency(self):
        self.get_records('mp.shop.address')
        self.get_records('sale.order.cancel.reason')
        self.get_records('res.partner')
        self.get_records('stock.warehouse')

    def get_products(self):
        self.get_records('product.template')
        self.get_records('product.image')
        self.get_records('product.template.wholesale')
        self.get_attribute_line_and_variant()
        
        self.get_records('product.staging')
        self.get_records('product.image.staging')
        self.get_records('product.staging.wholesale')
        self.get_records('product.staging.variant')

    def get_product_category(self):
        self.get_records('mp.tokopedia.category')
        self.get_records('product.category')
        self.get_records('mp.shopee.item.attribute.option')
        self.get_records('mp.shopee.item.attribute')
        self.get_records('mp.shopee.item.category')

    def get_product_dependency(self):
        self.get_records('stock.warehouse')

        self.get_records('mp.tokopedia.shop')
        self.get_records('mp.tokopedia.etalase')

        self.get_records('mp.tokopedia.category.unit')
        self.get_records('mp.tokopedia.category.value')
        self.get_records('mp.tokopedia.category.variant')

        
        self.get_records('mp.shopee.item.attribute.val')

        self.get_records('mp.shopee.logistic.size')
        self.get_records('mp.shopee.logistic')
        self.get_records('mp.shopee.shop.logistic')
        self.get_records('mp.shopee.item.logistic')

        self.get_records('product.attribute')
        self.get_records('product.attribute.unit')
        self.get_records('product.attribute.value')

        self.get_records('product.brand')
    
    def import_stock(self):
        if not self.session_id:
            self.retry_login(3)
        r = requests.get(self.name + '/ui/stock', headers={
            'X-Openerp-Session-Id': self.session_id,
        })
        res = json.loads(r.text) if r.status_code == 200 else {}
        if res:
            # Preparing
            warehouses_by_code = {}
            warehouses = self.env['stock.warehouse'].sudo().search([])
            for wh in warehouses:
                warehouses_by_code[wh.code] = wh

            products_by_izi_id = {}
            products = self.env['product.product'].sudo().search([('izi_id', '!=', False)])
            for pd in products:
                products_by_izi_id[pd.izi_id] = pd

            # Adjust Stock
            line_vals = []
            data = res['data']
            for prod in data['res_products']:
                prod_id = prod['id']
                if prod_id not in products_by_izi_id:
                    raise UserError('Product with this izi_id not found.')
                if products_by_izi_id[prod_id].type != 'product':
                    continue
                for prod_wh_code in data['res_warehouse_codes']:
                    if prod_wh_code not in warehouses_by_code:
                        raise UserError('Warehouse with this code not found.')
                    line_vals.append(
                        (0, 0, {
                            'product_id': products_by_izi_id[prod_id].id,
                            'location_id': warehouses_by_code[prod_wh_code].lot_stock_id.id,
                            'product_qty': prod[prod_wh_code]['qty_total'],
                        })
                    )
            res = self.env['stock.inventory'].sudo().create({
                'name': 'Import Stock Data From IZI',
                'line_ids': line_vals,
            })
            res.action_start()
            res.action_validate()

    def export_stock(self):
        res = []
        for mp_tp in self.mp_tokopedia_ids:
            lot_stock_id = mp_tp.wh_id.lot_stock_id.id

            # Check Quant
            quants = self.env['stock.quant'].sudo().search([('product_id.izi_id', '!=', False), ('location_id','=', lot_stock_id)])
            qty_by_izi_id = {}
            for qt in quants:
                if qt.product_id.izi_id not in qty_by_izi_id:
                    qty_by_izi_id[qt.product_id.izi_id] = 0
                qty_by_izi_id[qt.product_id.izi_id] += (qt.quantity - qt.reserved_quantity)

            # Create Adjustment Data
            adjustment_data = []
            for izi_id in qty_by_izi_id:
                adjustment_data.append({
                    'product_id': izi_id,
                    'product_qty': qty_by_izi_id[izi_id],
                })
            
            wh_res = {
                'wh_code': mp_tp.wh_id.code,
                'adjustment_data': adjustment_data,
            }
            res.append(wh_res)

        for mp_sp in self.mp_shopee_ids:
            lot_stock_id = mp_sp.wh_id.lot_stock_id.id
            pass

        # Access API
        if not self.session_id:
            self.retry_login(3)
        r = requests.post(self.name + '/api/ui/stock/import/data', json={
            'data': res,
        }, headers={
            'X-Openerp-Session-Id': self.session_id,
        })
        res = json.loads(r.text) if r.status_code == 200 else {}
        if res:
            pass

    #
    # Method Generic for API
    #
    def get_records(self, model_name, offset=0, limit=1000, order_field='id', sort='asc', custom_domain=0, retry_login=True, retry_login_count=3, domain_code=False):
        while True:
            if not self.session_id:
                self.retry_login(3)
            code = code_by_model_name[model_name] if model_name in code_by_model_name else model_name
            r = requests.get(self.name + '/api/ui/read/list-detail/%s?offset=%s&limit=%s&order=%s&sort=%s&custom_domain=%s&domain_code=%s' % (
                code, str(offset), str(limit), order_field, sort, str(custom_domain), domain_code),
                headers={'X-Openerp-Session-Id': self.session_id}
            )
            res = r.json() if r.status_code == 200 else {}
            if res.get('code') == 200:
                if len(res.get('data')) == 0:
                    break
                else:
                    offset += limit
                i = 0
                for res_values in res.get('data'):
                    i += 1
                    print('Get Records %s : %s' % (model_name, i))
                    record = self.get_existing_record(
                        model_name, res_values)
                    if record:
                        if 'izi_md5' in self.env[model_name]._fields:
                            izi_md5 = hashlib.md5(json.dumps(
                                res_values).encode('utf-8')).hexdigest()
                            if record.izi_md5 != izi_md5:
                                values = self.mapping_field(
                                    model_name, res_values, update=True)
                                values.update({
                                    'izi_md5': izi_md5
                                })
                                values = self.custom_before_write(model_name, values)
                                record.write(values)
                                self.custom_after_write(model_name, record)
                        else:
                            values = self.mapping_field(
                                model_name, res_values, update=True)
                            record.write(values)
                    else:
                        values = self.mapping_field(
                            model_name, res_values, update=False)
                        values = self.custom_before_create(model_name, values)
                        record = self.env[model_name].create(values)
                        self.custom_after_create(model_name, record)
                    self.env.cr.commit()
            elif res.get('code') == 401:
                if retry_login:
                    self.retry_login(retry_login_count)
                    self.get_records(model_name, offset, limit,
                                     order_field, sort, custom_domain, retry_login=False)
                else:
                    break
            else:
                break

    def custom_after_write(self, model_name, record):
        if model_name == 'sale.order':
            # Action
            record.action_by_order_status()
    
    def custom_before_write(self, model_name, values):
        res = values.copy()
        if model_name == 'sale.order':
            # Sale Order only update order_status and resi
            res = {
                'order_status': res['order_status'],
                'mp_awb_number': res['mp_awb_number'],
            }
        if model_name == 'product.template':
            if 'name' in res:
                del res['name']
            if 'default_code' in res:
                del res['default_code']
        return res
        
    def custom_before_create(self, model_name, values):
        res = values.copy()
        if model_name == 'sale.order':
            # Search Partner With Same Phone / Mobile Or Email For Tokopedia
            partner = False
            if values.get('mp_buyer_id'):
                partner = self.env['res.partner'].sudo().search([('buyer_id', '=', values.get('mp_buyer_id'))], limit=1)
            if not partner and values.get('mp_buyer_username'):
                partner = self.env['res.partner'].sudo().search([('buyer_username', '=', values.get('mp_buyer_username'))], limit=1)
            if not partner and values.get('mp_buyer_phone'):
                partner = self.env['res.partner'].sudo().search([('phone', '=', values.get('mp_buyer_phone'))], limit=1)
            if not partner and values.get('mp_buyer_email'):
                partner = self.env['res.partner'].sudo().search([('email', '=', values.get('mp_buyer_email'))], limit=1)

            # Create Partner From Buyer Information
            if not partner:
                partner = self.env['res.partner'].sudo().create({
                    'name': values.get('mp_buyer_name'),
                    'buyer_id': values.get('mp_buyer_id'),
                    'buyer_username': values.get('mp_buyer_username'),
                    'phone': values.get('mp_buyer_phone'),
                    'email': values.get('mp_buyer_email'),
                })
            # Create Shipping Address Under That Partner
            shipping_address = False
            shipping_address = self.env['res.partner'].sudo().search([('parent_id', '=', partner.id), ('name', '=', values.get('mp_recipient_address_name'))], limit=1)
            if not shipping_address:
                shipping_address = self.env['res.partner'].sudo().create({
                    'type': 'delivery',
                    'parent_id': partner.id,
                    'phone': values.get('mp_recipient_address_phone'),
                    'name': values.get('mp_recipient_address_name'),
                    'street': values.get('mp_recipient_address_full'),
                    'city': values.get('mp_recipient_address_city'),
                    'street2': values.get('mp_recipient_address_district', '') + ' ' + values.get('mp_recipient_address_city', '') + ' ' + values.get('mp_recipient_address_state', '') + ' ' + values.get('mp_recipient_address_country', ''),
                    'zip': values.get('mp_recipient_address_zipcode'),
                })
            # Replace values
            res['partner_id'] = partner.id
            res['partner_shipping_id'] = shipping_address.id
        return res

    def custom_after_create(self, model_name, record):
        if model_name == 'sale.order':
            # Action
            record.action_by_order_status()
            # Notify
            if self.env.user:
                self.env.user.notify_info('New Order From Marketplace')

    def get_existing_record_from_mapping(self, record, model_name, values):
        res = record
        if model_name == 'product.template':
            # Get Record From Product Mapping
            mapping = self.env['product.mapping'].sudo().search([('izi_id', '=', values['id'])], limit=1)
            if mapping and mapping.product_tmpl_id:
                res = mapping.product_tmpl_id
                res.izi_id = values['id']
                print('Product Mapping %s' % mapping.product_tmpl_id.name)
        return res

    def get_existing_record(self, model_name, values, depends=False):
        if 'id' not in values:
            raise UserError('Field id not found in the values.')
        Model = self.env[model_name].sudo()

        domain = [('izi_id', '=', values['id'])]
        if model_name in existing_fields_by_model_name and existing_fields_by_model_name[model_name]:
            for field_name in existing_fields_by_model_name[model_name]:
                if field_name in values and values[field_name]:
                    domain = ['|'] + domain + [(field_name, '=', values[field_name])]

        record = Model.search(domain, limit=1)
        # Mapping
        record = self.get_existing_record_from_mapping(record, model_name, values)

        if not record:
            if depends:
                raise UserError('Record not found model_name: %s, izi_id: %s. Import First.' % (model_name, values['id']))
            # if depends:
            #     self.get_records(model_name, retry_login=False)
            #     record = self.get_existing_record(model_name, values)
            # else:
            #     raise UserError('Record not found model_name: %s, izi_id: %s. Import First.' % (model_name, izi_id))
        return record

    def mapping_field(self, model_name, values, update=False):
        Model = self.env[model_name].sudo()
        res_values = {}
        for key in values:
            if model_name in removed_fields and key in removed_fields[model_name]:
                continue
            if key in Model._fields:
                if key == 'id':
                    res_values[key] = values[key]
                    res_values['izi_id'] = values[key]
                elif isinstance(Model._fields[key], fields.Many2one):
                    if 'id' in values[key]:
                        comodel_name = Model._fields[key].comodel_name
                        if comodel_name == model_name:
                            # If it has relation to itself, skipped, handle manually in custom_mapping_field
                            if model_name not in processed_model_with_many2one_itself:
                                continue
                        record = self.get_existing_record(comodel_name, values[key], depends=True)
                        if record:
                            res_values[key] = record.id
                    else:
                        res_values[key] = False
                elif isinstance(Model._fields[key], fields.Binary):
                    img = False
                    if values[key] and isinstance(values[key], str) and 'http' in values[key]:
                        img = b64encode(requests.get(values[key]).content)
                        res_values[key] = img
                    else:
                        try:
                            img = b64decode(values[key])
                        except Exception:
                            if values[key] != None and values[key] != False: 
                                img = values[key].encode('utf-8')
                        res_values[key] = img

                elif isinstance(Model._fields[key], fields.Selection) and 'value' in values[key]:
                    res_values[key] = str(values[key]['value'])
                elif values[key] and isinstance(Model._fields[key], fields.Many2many):
                    comodel_name = Model._fields[key].comodel_name
                    if comodel_name == model_name:
                        # If it has relation to itself, skipped, handle manually in custom_mapping_field
                        continue
                    val_ids = []
                    for val in values[key]:
                        record = self.get_existing_record(comodel_name, val, depends=True)
                        if record:
                            val_ids.append(record.id)
                    res_values[key] = [(6, 0, val_ids)]
                elif values[key] and isinstance(Model._fields[key], fields.One2many):
                    comodel_name = Model._fields[key].comodel_name
                    inverse_name = Model._fields[key].inverse_name
                    if comodel_name == model_name:
                        # If it has relation to itself, skipped, handle manually in custom_mapping_field
                        continue
                    if not update:
                        # If Create
                        res_values[key] = []
                        for line_values in values[key]:
                            if inverse_name and inverse_name in line_values:
                                del line_values[inverse_name]
                            res_line_values = self.mapping_field(comodel_name, line_values)
                            res_values[key].append((0, 0, res_line_values))
                    else:
                        # If Update, Skip From Now
                        continue
                else:
                    res_values[key] = values[key]
        # Custom Mapping Field
        res_values = self.custom_mapping_field(model_name, res_values)
        return res_values

    def custom_mapping_field(self, model_name, values):
        res_values = values
        if model_name == 'product.template':
            if res_values.get('barcode'):
                res_values.pop('barcode')
        elif model_name == 'product.product':
            if res_values.get('attribute_line_ids'):
                res_values.pop('attribute_line_ids')
            if res_values.get('barcode'):
                # barcode = datetime.now().strftime('%y%m%d%H%M%S%s')
                # barcode += "".join(choice(ascii_letters+digits) for i in range(4))
                # res_values['barcode'] = barcode
                res_values.pop('barcode')
            res_values['type'] = 'product'
        elif model_name == 'product.staging':
            if res_values.get('mp_tokopedia_id'):
                res_values['mp_type'] = 'Tokopedia'
            elif res_values.get('mp_shopee_id'):
                res_values['mp_type'] = 'Shopee'
        elif model_name == 'mp.tokopedia':
            res_values['active'] = True
            res_values['server_id'] = self.id
        elif model_name == 'mp.shopee':
            res_values['active'] = True
            res_values['server_id'] = self.id
        return res_values

    # Deprecated. To be deleted.
    def get_from_izi_id(self, model_name, izi_id):
        Model = self.env[model_name].sudo()
        if 'izi_id' not in Model._fields:
            return False
            # raise UserError('Field izi_id not found in model_name: %s, izi_id: %s.' % (model_name, izi_id))
        record = Model.search([('izi_id', '=', izi_id)], limit=1)
        if not record:
            raise UserError('Record not found model_name: %s, izi_id: %s. Import First.' % (model_name, izi_id))
        return record

    # Deprecated. To be deleted.
    def open_get_records_wizard(self, **kwargs):
        context = {
            'default_webhook_server_id': self.id,
        }
        return {
            'name': _('Get Records Wizard'),
            'context': context,
            'view_mode': 'form',
            'res_model': 'webhook.get.records.wizard',
            'res_id': kwargs.get('res_id', None),
            'type': 'ir.actions.act_window',
            'target': 'new'
        }

    def open_get_custom_model_records_wizard(self, **kwargs):
        context = {
            'default_webhook_server_id': self.id,
        }
        return {
            'name': _('Get Custom Model Records Wizard'),
            'context': context,
            'view_mode': 'form',
            'res_model': 'webhook.get.custom.model.records.wizard',
            'res_id': kwargs.get('res_id', None),
            'type': 'ir.actions.act_window',
            'target': 'new'
        }

    def mapping_field_post(self, model_name, obj_id, child=False, childs=[]):
        field_list = upload_fields.get(model_name, [])
        if not field_list:
            msg = 'Upload Failed. Model %s is not implemented yet.' % model_name
            _logger.error(msg)
            raise ValidationError(msg)
        Model = self.env[model_name].sudo()
        Model_id = Model.browse(obj_id)
        model_fld = Model._fields
        # returns: list of related model of model_name one2many and id
        if child:
            # to_upload_fields = upload_fields.get(model_name)
            for key in field_list:
                comodel_fld = model_fld[key]
                if comodel_fld.type == 'one2many':
                    comodel_name = comodel_fld._related_comodel_name
                    o2m_ids = getattr(Model_id, key)
                    for o2m_id in o2m_ids.ids:
                        childs.append({
                            'model_name': comodel_name,
                            'obj_id': o2m_id })
            return childs

        if 'izi_id' not in field_list:
            field_list.append('izi_id')
        res_values = Model_id.read(field_list)[0]
        for key in field_list:
            if model_name in removed_fields and key in removed_fields[model_name]:
                res_values.pop(key)
                continue
            if key in restricted_fields:
                res_values.pop(key)
                continue
            if key == 'izi_id':
                res_values['id'] = res_values.pop(key)
                continue

            fld_type = model_fld[key].type
            if res_values[key] and fld_type == 'many2one':
                m2o_id = res_values[key][0]
                comodel_name = model_fld[key].comodel_name
                comodel_id = self.env[comodel_name].sudo().browse(m2o_id)
                res_values[key] = comodel_id.izi_id or False
            elif fld_type == 'binary':
                img = False
                if res_values[key]:
                    img = res_values[key].decode('ascii')
                if model_name == 'product.image' and key == 'image' and not img:
                        img = Model_id.image_variant and Model_id.image_variant.decode('ascii')
                res_values[key] = img
            elif fld_type == 'many2many':
                if res_values[key]:
                    m2m_ids = res_values[key]
                    comodel_name = model_fld[key].comodel_name
                    comodel_ids = self.env[comodel_name].sudo().browse(m2m_ids)
                    not_imported_ids = comodel_ids.filtered(lambda x: not x.izi_id)
                    if not_imported_ids:
                        msg = 'Not imported: %s with this izi_id %s not imported yet.' % (model_fld[key].string, str(not_imported_ids))
                        _logger.warning(msg=msg)
                    res_values[key] = [(6, 0, comodel_ids)]
                else:
                    res_values.pop(key)
            elif fld_type == 'one2many':
                o2m_ids = res_values[key]
                if o2m_ids:
                    comodel_fld = model_fld[key]
                    comodel_name = comodel_fld._related_comodel_name
                    for o2m_id in o2m_ids:
                        childs.append({
                            'model_name': comodel_name, 'obj_id': o2m_id})
                        childs = self.mapping_field_post(
                            comodel_name, o2m_id, True, childs)
                res_values.pop(key)
        # Custom Mapping Field
        # res_values = self.custom_mapping_field(model_name, res_values)
        res_values['obj_id'] = obj_id
        return res_values, childs

    def mapping_field_post_one(self, model_name, obj_id):
        field_list = upload_fields.get(model_name, [])
        if not field_list:
            msg = 'Upload Failed. Model %s is not implemented yet.' % model_name
            _logger.error(msg)
            raise ValidationError(msg)

        if 'izi_id' not in field_list:
            field_list.append('izi_id')

        Model = self.env[model_name].sudo()
        Model_id = Model.browse(obj_id)
        model_fld = Model._fields
        res_values = Model_id.read(field_list)[0]
        m2m_vals = set()
        for key in field_list:
            if model_name in removed_fields and key in removed_fields[model_name]:
                res_values.pop(key)
                continue
            if key in restricted_fields:
                res_values.pop(key)
                continue
            if key == 'izi_id':
                res_values['id'] = res_values.pop(key)
                continue

            fld_type = model_fld[key].type
            if res_values[key] and fld_type == 'many2one':
                m2o_id = res_values[key][0]
                rel_model = Model._fields[key]
                comodel_name = rel_model.comodel_name
                comodel_id = self.env[comodel_name].sudo().browse(m2o_id)
                res_values[key] = comodel_id.izi_id or False
            elif res_values[key] and fld_type == 'binary':
                img = False
                if res_values[key]:
                    img = res_values[key].decode('ascii')
                if model_name == 'product.image' and key == 'image' and not img:
                        img = Model_id.image_variant and Model_id.image_variant.decode('ascii')
                res_values[key] = img
            elif res_values[key] and fld_type == 'many2many':
                res_values.pop(key)
                # skip dulu :: TODO
            elif res_values[key] and fld_type == 'one2many':
                res_values.pop(key)
        res_values['obj_id'] = obj_id
        return res_values

    #
    # Upload Manual
    #
    def upload_products(self, model_name, obj_id):
        if not model_name:
            return
        jsondata, post_process = self.mapping_field_post(model_name, obj_id)
        is_success = self.post_records(model_name, jsondata, True)
        if is_success[0]:
            self._cr.commit()
        for obj in post_process:
            data, _ = self.mapping_field_post(obj['model_name'], obj['obj_id'])
            is_success = self.post_records(obj['model_name'], data, True)
            if is_success[0]:
                self._cr.commit()
        return is_success

    def get_limit(self, day=1):
        # default last edited kemarin_dinihari
        return datetime.today() + delta(days=-day)

    def upload_to_izi(self, model_name='product.template'):
        limit_date = self.get_limit()
        Model = self.env[model_name].sudo()
        domain = [('write_date', '>', limit_date), ]
        if 'active' in Model._fields.keys():
            domain += [('active', 'in', [True, False])]
        Model_ids = Model.search(domain, order='write_date', limit=20)
        if model_name == 'product.template':
            for obj_id in Model_ids.ids:
                self.upload_products(model_name, obj_id)
        return True

    def upload_to_izi_one(self, model_name):
        limit_date = self.get_limit()
        Model = self.env[model_name].sudo()
        domain = [('write_date', '>', limit_date), ]
        if 'active' in Model._fields.keys():
            domain += [('active', 'in', [True, False])]
        Model_ids = Model.search(domain, order='write_date', limit=80)
        for obj_id in Model_ids.ids:
            data = self.mapping_field_post_one(model_name, obj_id)
            is_success = self.post_records(model_name, data, True)
            if is_success[0]:
                self._cr.commit()
        return True

    def get_updated_izi_id(self, Model_id, data):
        flds = Model_id.fields_get([],['name', 'type'])
        data_keys = set(data.keys())
        for key in data_keys:
            if key in restricted_fields:
                continue
            if flds.get(key) and flds[key]['type'] == 'many2one':
                comodel_id = getattr(Model_id, key)
                if comodel_id:
                    data[key] = comodel_id.izi_id or False
        return data

    def post_records(self, model_name, jsondata, recheck_m2o_id=True):
        is_success = (False, "Unknown error.")
        if jsondata.get('obj_id'):
            model_id = jsondata.pop('obj_id')
        else:
            model_id = jsondata.get('id')
        _logger.info('Uploading %s(%s)...' % (model_name, model_id))
        Model = self.env[model_name].sudo()
        Model_id = Model.browse(model_id)

        if recheck_m2o_id:
            jsondata = self.get_updated_izi_id(Model_id, jsondata)

        if Model_id.izi_id:
            url = '{}/api/ui/update/{}/{}'.format(
                self.name, model_name, Model_id.izi_id)
            jsondata['record_was_exist'] = Model_id.izi_id
        else:
            url = '{}/api/ui/create/{}'.format(self.name, model_name)
        try:
            req = requests.post(
                url,
                headers={'X-Openerp-Session-Id': self.session_id, },
                json=jsondata)
            if req.status_code == 200:
                response = req.json()
                data = response.get('data')
                error = data.get('error_descrip')
                izi_id = data.get('id')
                if izi_id and not error:
                    Model_id.izi_id = izi_id
                    is_success = (True, "Uploaded successfully.")
                    self._cr.commit()
                elif error:
                    is_success = (False, "Pesan dari IZI : " + error)
        except Exception as e:
            _logger.warn(e)
            is_success = (False, e)
        return is_success

    # @api.model
    def _sync_data(self, bulk=False):
        start_time = time.time()
        _logger.info('----- Upload started -----')
        records = self.search([
            ('is_sync', '=', True),
            ('active', 'in', [False, True]),],
            limit=1)
        if bulk:
            records[0].upload_to_izi()
        else:
            records[0].upload_to_izi_one('product.brand')
            records[0].upload_to_izi_one('product.template')
            records[0].upload_to_izi_one('product.product')
            records[0].upload_to_izi_one('product.staging')
            records[0].upload_to_izi_one('product.staging.variant')
            records[0].upload_to_izi_one('product.image')
            records[0].upload_to_izi_one('product.template.wholesale')
            records[0].upload_to_izi_one('product.staging.wholesale')
            records[0].upload_to_izi_one('product.image.staging')
        _logger.info(
            '----- Upload successfull in %0.2f seconds -----' %
            (time.time()  - start_time))

    def execute_action(self, model_name, model_id, method):
        is_success = (False, "Unknown error.")
        Model = self.env[model_name].sudo()
        data = self.mapping_field_post_one(model_name, model_id)
        self.post_records(model_name, data, True)
        self._cr.commit()
        Model_id = Model.browse(model_id)
        izi_id = Model_id.izi_id
        if izi_id != 0:
            try:
                url = self.__PATCH_URL__.format(self.name)
                req = requests.patch(
                    url + '/{}/{}'.format(model_name, method),
                    headers={'X-Openerp-Session-Id': self.session_id, },
                    json={'ids': [izi_id], })
                if req.status_code == 200:
                    response = req.json()
                    error = data.get('error_descrip')
                    result = response.get('result', {})
                    data = result.get('response', {})
                    status = data.get('status', 500)
                    msg = data.get('message', '')
                    if status == 200:
                        is_success = (True, "Uploaded successfully.")
                    else:
                        is_success = (False, msg)
            except Exception as e:
                _logger.warn(e)
                is_success = (False, e)
        return is_success

    #
    # Webhook
    #
    def set_default_available_webhook(self):
        self.ensure_one()
        model_obj = self.env['ir.model']
        model_ids = model_obj.search([('model', 'in', [fld for fld in upload_fields.keys()])])
        # self.active = True
        self.model_ids = [(6, 0, model_ids.ids)]
        for mdl in model_ids:
            mdl.set_default_webhook()

    def build_dependency_field(self):
        self.build_dependency(field=True)

    def build_dependency(self, **kwargs):
        model_obj = self.env['ir.model']
        for rec in self:
            models = rec.model_ids.mapped('model') + rec.model_ids.mapped(
                'webhook_field_ids').mapped('relation')
            rec.model_ids = [(6, 0, model_obj.search(
                [('model', 'in', models)]).ids)]
            if kwargs.get('field'):
                for model_id in rec.model_ids:
                    model_id.webhook_field_ids = [
                        (4, field_id.id, 0) for field_id in model_id.field_id.filtered(lambda r:r.required)]

    def clear_dependency(self):
        for rec in self:
            empty_models = rec.model_ids.filtered(
                lambda r: len(r.webhook_field_ids) == 0).mapped('model')
            rec.model_ids = [(6, 0, rec.model_ids.filtered(
                lambda r:r.model not in empty_models).ids)]
            for model_id in rec.model_ids:
                model_id.webhook_field_ids = [(3, field_id.id, 0) for field_id in model_id.webhook_field_ids.filtered(
                    lambda r:r.relation and (r.relation not in rec.model_ids.mapped('model')))]

    def init_webhook(self):
        self.mapped('model_ids').with_context(
            webhook_ids=self.ids).init_webhook()

    def get_access_token(self, **kwargs):
        token_obj = self.env['webhook.server.token']
        for rec in self:
            if rec.username and rec.password and isinstance(rec.id, int):
                try:
                    token_id = token_obj.search([
                        ('config_id', '=', rec.id),
                        ('expires_at', '>', fields.Datetime.now())
                    ], limit=1, order='expires_at desc')
                    if token_id and token_id.access_token and token_id.expires_at and '<html>' not in token_id.access_token:
                        pass
                    else:
                        req = requests.post(
                            self.__TOKEN_URL__.format(rec.name),
                            headers={
                                'Authorization': 'Basic %s' % (b64encode(('%s:%s' % (rec.username, rec.password)).encode('utf-8')).decode('utf-8')),
                                'Content-Length': '0',
                                'User-Agent': 'PostmanRuntime/7.26.1',
                            }
                        )
                        token_data = json.loads(
                            req.text) if req.status_code == 200 else {}
                        if token_data.get('access_token') and token_data.get(
                                'expires_in'):
                            token_data['config_id'] = rec.id
                            token_id = token_obj.create(token_data)
                    rec.access_token = token_id.access_token
                    rec.expires_at = token_id.expires_at
                except Exception as e:
                    _logger.warn(e)

    #
    # Cron
    #
    def _run_get_orders(self):
        webhook_servers = self.search([('active', '=', True)])
        for webhook_server in webhook_servers:
            webhook_server.with_context({'run_by_cron': True}).get_orders()


class WebhookServerToken(models.Model):
    _name = 'webhook.server.token'
    _description = 'Webhook Server Token'

    access_token = fields.Char(required=True)
    expires_in = fields.Integer()
    expires_at = fields.Datetime(compute='_get_expires_at', store=True)
    config_id = fields.Many2one(
        'webhook.server', required=True, ondelete='cascade')

    @api.depends('expires_in')
    def _get_expires_at(self, **kwargs):
        for rec in self:
            expires_at = datetime.now() + timedelta(seconds=rec.expires_in)
            rec.expires_at = fields.Datetime.to_string(expires_at)


class WebhookServerMQ(models.Model):
    _name = 'webhook.server.mq'
    _description = 'Webhook Server MQ'
    _rec_name = 'write_date'
    _order = 'write_date desc'

    config_id = fields.Many2one(
        'webhook.server', required=True, ondelete='cascade')
    res_model_id = fields.Many2one(
        'ir.model', required=True, ondelete='cascade')
    res_ids = fields.Text()
    request = fields.Text()
    response = fields.Text()
    status_code = fields.Integer(required=True, default=0)
    status_history = fields.One2many('webhook.server.mq.status', 'mq_id')
    retry = fields.Boolean(compute='_is_retry', store=True)
    is_patch = fields.Boolean('Patch', readonly=True)

    @api.depends('response', 'status_code')
    def _is_retry(self):
        wingi = fields.Datetime.to_string(datetime.now() - timedelta(days=1))
        mq_ids = self.search([
            '|',
            '|',
            ('status_code', '!=', 200),
            ('response', 'ilike', '{"jsonrpc": "2.0", "id": null, "error":'),
            ('response', 'ilike', '"type": "error"'),
            ('write_date', '>=', wingi)
        ], order='write_date').ids
        for rec in self:
            rec.retry = True if rec.id in mq_ids else False

    @api.model
    def create(self, vals):
        res = super(WebhookServerMQ, self).create(vals)
        if not self._context.get('lazy'):
            if res.config_id.access_token and res.request:
                if not res.is_patch:
                    try:
                        r = requests.post(
                            res.config_id.__CLIENT_URL__.format(
                                res.config_id.name),
                            json=json.loads(res.request),
                            headers={
                                'Authorization': 'Bearer %s' %
                                (res.config_id.access_token)
                            }
                        )
                        response = r.text
                        try:
                            response = json.dumps(
                                json.loads(response), indent=2)
                        except Exception:
                            pass
                        res.write({
                            'response': response,
                            'status_code': r.status_code,
                            'status_history': [(0, 0, {
                                'response': response,
                                'status_code': r.status_code
                            })]
                        })
                    except Exception as e:
                        _logger.warn(e)
                else:
                    try:
                        raw_request = json.loads(res.request)
                        patch_url = '/{}/{}'.format(
                            raw_request.get('model'),
                            raw_request.get('method'))
                        r = requests.patch(
                            res.config_id.__PATCH_URL__.format(
                                res.config_id.name) + patch_url,
                            json=json.loads(res.request),
                            headers={
                                'Authorization': 'Bearer %s' %
                                (res.config_id.access_token)
                            }
                        )
                        response = r.text
                        try:
                            response = json.dumps(
                                json.loads(response), indent=2)
                        except Exception:
                            pass
                        res.write({
                            'response': response,
                            'status_code': r.status_code,
                            'status_history': [(0, 0, {
                                'response': response,
                                'status_code': r.status_code
                            })]
                        })
                    except Exception as e:
                        _logger.warn(e)

        return res

    def send_request(self):
        for mq_id in self:
            if mq_id.config_id.access_token and mq_id.request:
                if not mq_id.is_patch:
                    try:
                        req = requests.post(
                            mq_id.config_id.__CLIENT_URL__.format(
                                mq_id.config_id.name),
                            json=json.loads(mq_id.request),
                            headers={
                                'Authorization': 'Bearer %s' % (mq_id.config_id.access_token)
                            }
                        )
                        response = req.text
                        try:
                            response = json.dumps(json.loads(response), indent=2)
                        except Exception:
                            pass
                        mq_id.write({
                            'response': response,
                            'status_code': req.status_code,
                            'status_history': [(0, 0, {
                                'response': response,
                                'status_code': req.status_code
                            })]
                        })
                        self._cr.commit()
                    except Exception as e:
                        _logger.warn(e)
                else:
                    try:
                        raw_request = json.loads(mq_id.request)
                        patch_url = mq_id.config_id.__PATCH_URL__.format(
                            mq_id.config_id.name) + '/{}/{}'.format(
                                raw_request.get('model'),
                                raw_request.get('method'))
                        r = requests.patch(
                            patch_url,
                            json=json.loads(mq_id.request),
                            headers={
                                'Authorization': 'Bearer %s' %
                                (mq_id.config_id.access_token)
                            }
                        )
                        response = r.text
                        try:
                            response = json.dumps(
                                json.loads(response), indent=2)
                        except Exception:
                            pass
                        mq_id.write({
                            'response': response,
                            'status_code': r.status_code,
                            'status_history': [(0, 0, {
                                'response': response,
                                'status_code': r.status_code
                            })]
                        })
                    except Exception as e:
                        _logger.warn(e)

    @api.model
    def retry_requests(self, **kwargs):
        wingi_nane = fields.Datetime.to_string(
            datetime.now() - timedelta(days=2))
        mq_ids = self.search([
            '|',
            '|',
            ('status_code', '!=', 200),
            ('response', 'ilike', '{"jsonrpc": "2.0", "id": null, "error":'),
            ('response', 'ilike', '"type": "error"'),
            ('write_date', '>=', wingi_nane)
        ], order='write_date')
        for mq_id in mq_ids:
            if mq_id.config_id.access_token and mq_id.request:
                try:
                    r = requests.post(
                        mq_id.config_id.__CLIENT_URL__.format(
                            mq_id.config_id.name),
                        json=json.loads(mq_id.request),
                        headers={
                            'Authorization': 'Bearer %s' % (mq_id.config_id.access_token)
                        }
                    )
                    response = r.text
                    try:
                        response = json.dumps(json.loads(response), indent=2)
                    except Exception:
                        pass
                    mq_id.write({
                        'response': response,
                        'status_code': r.status_code,
                        'status_history': [(0, 0, {
                            'response': response,
                            'status_code': r.status_code
                        })]
                    })
                    self._cr.commit()
                except Exception as e:
                    _logger.warn(e)
        ahad_wingi = fields.Datetime.to_string(
            datetime.now() - timedelta(days=7))
        self.search([('write_date', '<', ahad_wingi)]).unlink()


class WebhookServerMQStatus(models.Model):
    _name = 'webhook.server.mq.status'
    _description = 'Webhook Server MQ Status History'
    _rec_name = 'status_code'
    _order = 'create_date desc'

    mq_id = fields.Many2one('webhook.server.mq', 'MQ', ondelete='cascade')
    status_code = fields.Integer(required=True, default=0)
    response = fields.Text()
