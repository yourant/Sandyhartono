# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import time
import json
import hashlib
import logging
import requests
import base64
from random import choice
from string import digits, ascii_letters
from datetime import datetime, timedelta
from base64 import b64encode, b64decode
# from math import ceil
from odoo import tools
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta as delta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.models import NewId

_logger = logging.getLogger(__name__)
# _chunk = lambda lst, n: [lst[i:i + n] for i in range(0, len(lst), n)]

# Helper Dictionary
code_by_model_name = {
    'uom.uom': 'product.uom',
    'sale.order': 'izi-orders',
    'res.partner': 'izi-partners',
    'mp.shop.address': 'izi-shop-address',
    'sale.order.cancel.reason': 'izi-sale-cancel-reason',
    'sale.order.pickup.info': 'izi-pickup-info',

    'mp.tokopedia': 'izi-tokopedia',
    'mp.tokopedia.shop': 'izi-tokopedia-shop',
    'mp.tokopedia.etalase': 'izi-tokopedia-etalase',
    'mp.tokopedia.category': 'izi-tokopedia-categories',
    'mp.tokopedia.category.variant': 'izi-tokopedia-category-variants',
    'mp.tokopedia.category.unit': 'izi-tokopedia-category-units',
    'mp.tokopedia.category.value': 'izi-tokopedia-category-values',
    'mp.tokopedia.variant.value': 'izi-tokopedia-variant-values',
    'mp.tokopedia.attribute.line': 'izi-tokopedia-attribute-line',

    'mp.shopee': 'izi-shopee',
    'mp.shopee.item.category': 'izi-shopee-item-category',
    'mp.shopee.item.attribute': 'izi-shopee-item-attribute',
    'mp.shopee.item.brand': 'izi-shopee-item-brand',
    'mp.shopee.item.attribute.option': 'izi-shopee-item-attribute-option',
    'mp.shopee.item.attribute.val': 'izi-shopee-item-attribute-val',
    'mp.shopee.logistic': 'izi-shopee-logistic',
    'mp.shopee.logistic.size': 'izi-shopee-logistic-size',
    'mp.shopee.shop.logistic': 'izi-shopee-shop-logistic',
    'mp.shopee.item.logistic': 'izi-shopee-item-logistic',

    'mp.shopee.item.var.attribute': 'izi-shopee-item-var-attribute',
    'mp.shopee.item.var.attribute.value': 'izi-shopee-item-var-attribute-value',
    'mp.shopee.attribute.line': 'izi-shopee-item-attribute-line',

    'mp.lazada': 'izi-lazada',
    'mp.lazada.brand': 'izi-lazada-brand',
    'mp.lazada.category': 'izi-lazada-category',
    'mp.lazada.category.attr': 'izi-lazada-category-attr',
    'mp.lazada.category.attr.opt': 'izi-lazada-category-attr-opt',
    'mp.lazada.product.attr': 'izi-lazada-product-attr',

    'mp.lazada.variant.value': 'izi-lazada-variant-value',
    'mp.lazada.attribute.line': 'izi-lazada-attribute-line',

    'mp.blibli': 'izi-blibli',
    'mp.blibli.item.category': 'izi-blibli-item-category',
    'mp.blibli.item.category.attr': 'izi-blibli-item-category-attribute',
    'mp.blibli.item.attr.option': 'izi-blibli-item-attribute-option',
    'mp.blibli.brand': 'izi-blibli-item-brand',
    'mp.blibli.item.attribute.val': 'izi-blibli-item-attribute-val',
    'mp.blibli.logistic': 'izi-blibli-logistic',
    'mp.blibli.attribute.line': 'izi-blibli-attribute-line',
    'mp.blibli.variant.value': 'izi-blibli-variant-value',

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

    'mp.product.discount': 'izi-product-discounts',
    'mp.product.discount.line': 'izi-product-discount-lines'
}

existing_fields_by_model_name = {
    'stock.warehouse': ['code'],
    'res.company': ['name'],
    'res.users': ['name'],
    'mp.lazada.category.attr.opt': ['name'],
    'mp.blibli.item.attr.option': ['name'],
    'product.template': ['name'],
    'product.product': ['name'],
}

removed_fields = {
    'product.product': ['uom_id', 'barcode'],
    'product.template': ['image_small', 'image_medium', 'barcode'],
    'product.staging': ['izi_md5'],
    'mp.lazada.product.attr': ['option_id'],
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
        'attribute_line_ids'
    ],
    'product.staging': [
        'active', 'barcode', 'brand_id', 'default_code', 'description_sale',
        'height', 'is_active', 'length', 'list_price', 'min_order',
        'name', 'package_content',
        'product_template_id', 'product_variant_stg_ids',
        'weight', 'width', 'qty_available', 'mp_type'
    ],
    'Tokopedia': [
        'mp_tokopedia_id', 'tp_active_status', 'tp_available_status', 'tp_category_id',
        'tp_condition', 'tp_etalase_id', 'tp_weight_unit',
    ],
    'Lazada': [
        'mp_lazada_id'
    ],
    'Shopee': [
        'mp_shopee_id', 'sp_is_pre_order', 'sp_category_int',
        'sp_days_to_ship', 'sp_condition'
    ],
    'Blibli': [
        'mp_blibli_id'
    ],
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
        'product_staging_ids', 'product_image_ids', 'attribute_value_ids',
    ],
    'product.image': [
        'image', 'name', 'product_tmpl_id', 'url_external'
    ],
    'product.image.staging': [
        'image', 'name', 'product_stg_id',
    ],
    'product.staging.variant': [
        'default_code', 'active', 'mp_external_id', 'product_id', 'qty_available', 'price_custom', 'product_stg_id',
    ],
    'product.attribute': [
        'type', 'name', 'create_variant', 'value_ids',
    ],
    'product.attribute.value': [
        'name', 'html_color', 'attribute_id'
    ],
    'product.template.attribute.line': [
        'attribute_id', 'value_ids', 'product_tmpl_id',
    ],
    'mp.shopee.item.logistic': [
        'id', 'item_id_staging', 'logistic_id', 'enabled', 'shipping_fee', 'size_id',
        'is_free', 'estimated_shipping_fee'
    ],
    'mp.shopee.item.attribute.val': [
        'id', 'attribute_int', 'attribute_id', 'attribute_value', 'item_id_staging'
    ],
}
restricted_fields = [
    'create_uid', 'write_uid', 'create_date', 'write_date',
    '__last_update',
]

processed_model_with_many2one_itself = [
    'mp.tokopedia.category'
]

response_fields_by_model = {
    'product.template': [
        'product_image_ids', 'product_wholesale_ids'
    ],
    'product.staging': [
        'product_variant_ids', 'product_image_staging_ids', 'product_wholesale_ids', 'product_variant_stg_ids', 'tp_variant_value_ids', 'tp_attribute_line_ids'
    ],
}


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
        vals2 = {}
        if self._name in code_by_model_name.keys():
            for k, v in vals.items():
                if v == {}:
                    continue
                elif (self._name == 'product.product') and (k == 'attribute_value_ids') and (not v):
                    continue
                vals2[k] = v
                if self._fields[k].type == 'selection':
                    if not isinstance(v, str) and not isinstance(v, bool):
                        vals2[k] = '%s' % (v)
        else:
            vals2 = vals
        res = super(Base, self).create(vals2)
        # if vals2 and self._context.get('webhook', True):
        #     res.create_webhook(fields=list(vals2.keys()))
        return res

    def write(self, vals):
        vals2 = {}
        if self._name in code_by_model_name.keys():
            for k, v in vals.items():
                if v == {}:
                    continue
                elif (self._name == 'product.product') and (k == 'attribute_value_ids') and (not v):
                    continue
                vals2[k] = v
                if self._fields[k].type == 'selection':
                    if not isinstance(v, str):
                        vals2[k] = '%s' % (v)
        else:
            vals2 = vals
        res = super(Base, self).write(vals2)
        return res

    # def write(self, vals):
    #     res = super(Base, self).write(vals)
    #     if vals and self._context.get('webhook', True):
    #         self.create_webhook(fields=list(vals.keys()))
    #     return res

    # def unlink(self):
    #     if self._context.get('webhook', True):
    #         self.create_webhook(method='unlink')
    #     res = super(Base, self).unlink()
    #     return res

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
    webhook_server_id = fields.Many2one('webhook.server', 'Webhook Server')

    def process_wizard(self):
        self.webhook_server_id.get_records(
            self.custom_model_name, force_update=True)


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
    session_id = fields.Char('Session', readonly=True, compute='_get_session')

    active = fields.Boolean(default=False)
    is_skip_error = fields.Boolean('Skip Error', default=False)
    is_skip_image = fields.Boolean('Skip Product Image', default=False)
    is_skip_product_not_mapping = fields.Boolean('Skip Not Mapped', default=False)
    is_quotation_only = fields.Boolean('Always Quotation', default=True)
    skip_cancel_order = fields.Boolean('Skip Cancelled Order', default=False)
    skip_waiting_order = fields.Boolean('Skip Unpaid Order', default=True)
    no_action_marketplace = fields.Boolean('Unsync All Action', default=False)
    no_action_picking_marketplace = fields.Boolean('Unsync Delivery Action', default=False)
    check_invoice_number = fields.Boolean('Check Invoice Number', default=False)
    is_shipping_address = fields.Boolean('Use Shipping Address', default=False)

    get_records_time_limit = fields.Selection([
        ('last_hour', 'Last Hour'),
        ('last_3_days', 'Last 3 Days'),
        ('last_7_days', 'Last 7 Days'),
    ], default='last_hour', required=True, string='Time Limit')

    log_ids = fields.One2many('webhook.server.log', 'server_id', string='Records Logs')
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

    def _get_session(self):
        try:
            self.check_auth()
            if self.name[-1] == '/':
                self.write({
                    'name': self.name[:-1]
                })
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
                    raise ValidationError(error + ' for Webhook server : ' + str(self))
                self.session_id = session_id
                return self.session_id
            self.session_id = ''
            return False
        except Exception as e:
            _logger.error(str(e))
            self.session_id = ''
            return False

    def retry_login(self, count_retry=1):
        session_id = False
        for i in range(count_retry):
            session_id = self._get_session()
            if session_id:
                return session_id
            else:
                time.sleep(1)
        if not session_id:
            raise UserError('Failed when trying to login to IZI server, please make sure you enter the correct server url, username, and password')
        return False
    
    def delete_staging_and_attribute(self):
        self.env.cr.execute('''
            UPDATE product_template SET izi_id = NULL;
            UPDATE product_product SET izi_id = NULL;
            DELETE FROM product_staging_variant;
            DELETE FROM product_staging_wholesale;
            DELETE FROM product_image_staging;
            DELETE FROM product_staging;
            
            DELETE FROM mp_tokopedia_attribute_line;
            DELETE FROM mp_tokopedia_variant_value;
            DELETE FROM mp_tokopedia_category_value;
            DELETE FROM mp_tokopedia_category_unit;
            DELETE FROM mp_tokopedia_category_variant;
            DELETE FROM mp_tokopedia_category;

            DELETE FROM mp_shopee_attribute_line;
            DELETE FROM mp_shopee_item_attribute_option;
            DELETE FROM mp_shopee_item_attribute_val;
            DELETE FROM mp_shopee_item_attribute;
            DELETE FROM mp_shopee_item_var_attribute_value;
            DELETE FROM mp_shopee_item_var_attribute;
            DELETE FROM mp_shopee_item_logistic;
            DELETE FROM mp_shopee_item_category;
            DELETE FROM mp_shopee_shop_logistic;
            DELETE FROM mp_shopee_logistic;
            DELETE FROM mp_shopee_logistic_size;

            DELETE FROM mp_lazada_attribute_line;
            DELETE FROM mp_lazada_variant_value;
            DELETE FROM mp_lazada_category_attr_opt;
            DELETE FROM mp_lazada_category_attr;
            DELETE FROM mp_lazada_category;
            DELETE FROM mp_lazada_brand;
        ''')
    
    def delete_data(self):
        pp_ids = self.env['product.product'].sudo().search([('izi_id', '!=', False), '|', ('active', '=', True), ('active', '=', False)]).ids
        pt = self.env['product.template'].sudo().search([('izi_id', '!=', False), '|', ('active', '=', True), ('active', '=', False)])
        pt_ids = pt.ids

        for p in pt:
            for v in p.product_variant_ids:
                if v.id not in pp_ids:
                    pp_ids.append(v.id)

        so_ids = self.env['sale.order'].sudo().search([('izi_id', '!=', False)]).ids
        
        sol = self.env['sale.order.line'].sudo().search([('order_id', 'in', so_ids)])
        pol = self.env['purchase.order.line'].sudo().search([('product_id', 'in', pp_ids)])
        sml = self.env['stock.move.line'].sudo().search([('product_id', 'in', pp_ids)])
        sil = self.env['stock.inventory.line'].sudo().search([('product_id', 'in', pp_ids)])

        ai = []
        ai_ids = []
        ail_ids = []
        for s in sol:
            for i in s.order_id.invoice_ids:
                if i not in ai:
                    ai.append(i)
                    ai_ids.append(i.id)
                    for l in i.invoice_line_ids:
                        if l.id not in ail_ids:
                            ail_ids.append(l.id)
        
        ail = self.env['account.invoice.line'].sudo().search([('product_id', 'in', pp_ids)])
        for l in ail:
            if l.id not in ail_ids:
                ail_ids.append(l.id)
            if l.invoice_id.id not in ai_ids:
                ai_ids.append(l.invoice_id.id)

        sp = []
        sp_ids = []
        for s in sol:
            for p in s.order_id.picking_ids:
                if p not in sp:
                    sp.append(p)
                    sp_ids.append(p.id)

        sol_ids = sol.ids
        sol_from_product = self.env['sale.order.line'].sudo().search([('product_id', 'in', pp_ids)])
        for l in sol_from_product:
            if l.id not in sol_ids:
                sol_ids.append(l.id)
            if l.order_id.id not in so_ids:
                so_ids.append(l.order_id.id)

        pol_ids = pol.ids
        sml_ids = sml.ids
        sil_ids = sil.ids
        sm = self.env['stock.move'].sudo().search([('product_id', 'in', pp_ids)])
        sm_ids = sm.ids
        sq_ids = self.env['stock.quant'].sudo().search(['|', ('product_id', 'in', pp_ids), ('product_tmpl_id', 'in', pt_ids)]).ids

        for s in sm:
            if s.picking_id and s.picking_id.id not in sp_ids:
                sp_ids.append(s.picking_id.id)
        
        po_ids = []
        for p in pol:
            if p.order_id.id not in po_ids:
                po_ids.append(p.order_id.id)

        si_ids = []
        for s in sil:
            if s.inventory_id.id not in si_ids:
                si_ids.append(s.inventory_id.id)
        
        am = []
        am_ids = []
        aml_ids = []
        for a in ai:
            if a.move_id and a.move_id not in am:
                am.append(a.move_id)
                am_ids.append(a.move_id.id)
                for l in a.move_id.line_ids:
                    if l.id not in aml_ids:
                        aml_ids.append(l.id)

        psv_ids = self.env['product.staging.variant'].sudo().search([('izi_id', '!=', False)]).ids
        ps_ids = self.env['product.staging'].sudo().search([('izi_id', '!=', False)]).ids
        ru_ids = self.env['res.users'].sudo().search([('izi_id', '!=', False), '|', ('active', '=', True), ('active', '=', False)]).ids
        rp_ids = self.env['res.partner'].sudo().search([('izi_id', '!=', False), '|', ('active', '=', True), ('active', '=', False)]).ids
        
        sl = self.env['stock.location'].sudo().search([('izi_id', '!=', False), '|', ('active', '=', True), ('active', '=', False)])
        sw = self.env['stock.warehouse'].sudo().search([('izi_id', '!=', False), '|', ('active', '=', True), ('active', '=', False)])
        sl_ids = sl.ids
        sw_ids = sw.ids

        for s in sw:
            if s.lot_stock_id and s.lot_stock_id.id not in sl_ids:
                sl_ids.append(s.lot_stock_id.id)
            if s.view_location_id and s.view_location_id.id not in sl_ids:
                sl_ids.append(s.view_location_id.id)
            if s.wh_input_stock_loc_id and s.wh_input_stock_loc_id.id not in sl_ids:
                sl_ids.append(s.wh_input_stock_loc_id.id)
            if s.wh_output_stock_loc_id and s.wh_output_stock_loc_id.id not in sl_ids:
                sl_ids.append(s.wh_output_stock_loc_id.id)
            if s.wh_pack_stock_loc_id and s.wh_pack_stock_loc_id.id not in sl_ids:
                sl_ids.append(s.wh_pack_stock_loc_id.id)
            if s.wh_qc_stock_loc_id and s.wh_qc_stock_loc_id.id not in sl_ids:
                sl_ids.append(s.wh_qc_stock_loc_id.id)
        
        sr_ids = self.env['stock.rule'].sudo().search([('warehouse_id', 'in', sw_ids), '|', ('active', '=', True), ('active', '=', False)]).ids
        spt_ids = self.env['stock.picking.type'].sudo().search([('warehouse_id', 'in', sw_ids), '|', ('active', '=', True), ('active', '=', False)]).ids

        sp_from_spt = self.env['stock.picking'].sudo().search([('picking_type_id', 'in', spt_ids)])
        for s in sp_from_spt:
            if s.id not in sp_ids:
                sp_ids.append(s.id)

        po_from_spt = self.env['purchase.order'].sudo().search([('picking_type_id', 'in', spt_ids)])
        for p in po_from_spt:
            if p.id not in po_ids:
                po_ids.append(p.id)

        si_from_sl = self.env['stock.inventory'].sudo().search([('location_id', 'in', sl_ids)])
        for s in si_from_sl:
            if s.id not in si_ids:
                si_ids.append(s.id)
        
        sr_from_spt = self.env['stock.rule'].sudo().search(['|', '|', ('location_id', 'in', sl_ids), ('location_src_id', 'in', sl_ids), ('picking_type_id', 'in', spt_ids)])
        for s in sr_from_spt:
            if s.id not in sr_ids:
                sr_ids.append(s.id)
        
        sm_from_sl = self.env['stock.move'].sudo().search(['|', ('location_id', 'in', sl_ids), ('location_dest_id', 'in', sl_ids)])
        for s in sm_from_sl:
            if s.id not in sm_ids:
                sm_ids.append(s.id)
        
        sml_from_sl = self.env['stock.move.line'].sudo().search(['|', ('location_id', 'in', sl_ids), ('location_dest_id', 'in', sl_ids)])
        for s in sml_from_sl:
            if s.id not in sml_ids:
                sml_ids.append(s.id)
        
        apr_ids = self.env['account.partial.reconcile'].sudo().search(['|', ('credit_move_id', 'in', am_ids), ('debit_move_id', 'in', am_ids)])

        # Change to String
        self.env.cr.execute('DELETE FROM mp_tokopedia;DELETE FROM mp_shopee;DELETE FROM product_mapping;DELETE FROM warehouse_mapping;DELETE FROM stock_change_product_qty;DELETE FROM stock_distribution;')
        if ail_ids:
            self.env.cr.execute('DELETE FROM account_invoice_line WHERE id IN (%s);' % (','.join(list(map(str, ail_ids)))))
        if ai_ids:
            self.env.cr.execute('DELETE FROM account_invoice WHERE id IN (%s);' % (','.join(list(map(str, ai_ids)))))
        if sq_ids:
            self.env.cr.execute('DELETE FROM stock_quant WHERE id IN (%s);' % (','.join(list(map(str, sq_ids)))))
        if sm_ids:
            self.env.cr.execute('DELETE FROM stock_move WHERE id IN (%s);' % (','.join(list(map(str, sm_ids)))))
        if sml_ids:
            self.env.cr.execute('DELETE FROM stock_move_line WHERE id IN (%s);' % (','.join(list(map(str, sml_ids)))))
        if sil_ids:
            self.env.cr.execute('DELETE FROM stock_inventory_line WHERE id IN (%s);' % (','.join(list(map(str, sil_ids)))))
        if si_ids:
            self.env.cr.execute('DELETE FROM stock_inventory WHERE id IN (%s);' % (','.join(list(map(str, si_ids)))))
        if pol_ids:
            self.env.cr.execute('DELETE FROM purchase_order_line WHERE id IN (%s);' % (','.join(list(map(str, pol_ids)))))
        if po_ids:
            self.env.cr.execute('DELETE FROM purchase_order WHERE id IN (%s);' % (','.join(list(map(str, po_ids)))))
        if sp_ids:
            self.env.cr.execute('DELETE FROM stock_picking WHERE id IN (%s);' % (','.join(list(map(str, sp_ids)))))
        if sol_ids:
            self.env.cr.execute('DELETE FROM sale_order_line WHERE id IN (%s);' % (','.join(list(map(str, sol_ids)))))
        if so_ids:
            self.env.cr.execute('DELETE FROM sale_order WHERE id IN (%s);' % (','.join(list(map(str, so_ids)))))
        if pp_ids:
            self.env.cr.execute('DELETE FROM product_product WHERE id IN (%s);' % (','.join(list(map(str, pp_ids)))))
        if pt_ids:
            self.env.cr.execute('DELETE FROM product_template WHERE id IN (%s);' % (','.join(list(map(str, pt_ids)))))
        if psv_ids:
            self.env.cr.execute('DELETE FROM product_staging_variant WHERE id IN (%s);' % (','.join(list(map(str, psv_ids)))))
        if ps_ids:
            self.env.cr.execute('DELETE FROM product_staging WHERE id IN (%s);' % (','.join(list(map(str, ps_ids)))))
        if apr_ids:
            self.env.cr.execute('DELETE FROM account_partial_reconcile WHERE id IN (%s);' % (','.join(list(map(str, apr_ids)))))
        if aml_ids:
            self.env.cr.execute('DELETE FROM account_move_line WHERE id IN (%s);' % (','.join(list(map(str, aml_ids)))))
        if am_ids:
            self.env.cr.execute('DELETE FROM account_move WHERE id IN (%s);' % (','.join(list(map(str, am_ids)))))
        # TODO: Do Not Delete Res Users and Res Partner
        # if ru_ids:
        #     self.env.cr.execute('DELETE FROM res_users WHERE id IN (%s);' % (','.join(list(map(str, ru_ids)))))
        # if rp_ids:
        #     self.env.cr.execute('DELETE FROM res_partner WHERE id IN (%s);' % (','.join(list(map(str, rp_ids)))))
        if sr_ids:
            self.env.cr.execute('DELETE FROM stock_rule WHERE id IN (%s);' % (','.join(list(map(str, sr_ids)))))
        if spt_ids:
            self.env.cr.execute('DELETE FROM stock_picking_type WHERE id IN (%s);' % (','.join(list(map(str, spt_ids)))))
        if sw_ids:
            self.env.cr.execute('DELETE FROM stock_warehouse WHERE id IN (%s);' % (','.join(list(map(str, sw_ids)))))
        if sl_ids:
            self.env.cr.execute('DELETE FROM stock_location WHERE id IN (%s);' % (','.join(list(map(str, sl_ids)))))
        self.env.cr.execute('DELETE FROM mp_tokopedia_variant_value;')
        self.env.cr.execute('DELETE FROM mp_shopee_item_attribute_option;')
        self.env.cr.execute('DELETE FROM mp_shopee_item_var_attribute_value;')

    #
    # API Get Specific
    #
    def initialize(self):
        self.get_accounts()
        self.get_product_category()
        self.get_dependency()
        self.syncronize()

    def syncronize(self):
        self.get_products()
        self.get_orders()
        self.import_stock()

    def get_accounts(self):
        self.get_companies()
        self.get_warehouses()
        self.get_records('res.partner', loop_commit=False)
        self.get_records('mp.tokopedia', force_update=True, domain_code='all_active', loop_commit=False)
        self.get_records('mp.shopee', force_update=True, domain_code='all_active', loop_commit=False)
        self.get_records('mp.lazada', force_update=True, domain_code='all_active', loop_commit=False)
        self.get_records('mp.blibli', force_update=True, domain_code='all_active', loop_commit=False)

    def get_dependency(self):
        self.get_product_dependency()
        self.get_orders_dependency()

    def remote(self):
        self.ensure_one()
        access_token = False
        r = requests.get(self.name + '/api/v1/dbname', json={}, headers={
            'X-Openerp-Session-Id': self.session_id,
        } if self.session_id else None)
        res = json.loads(r.text) if r.status_code == 200 else {}
        if self.username and self.password:
            dbname = self.name.split('//')[1] if not res else res.get('response', {}).get('dbname')
            get_token = requests.post(self.name + '/api/auth/get_tokens', json={
                    "db":dbname,
                    "username": self.username,
                    "password": self.password
                }, headers={
                    'X-Openerp-Session-Id': self.session_id,
                } if self.session_id else None)
            token_res = json.loads(get_token.text) if get_token.status_code == 200 else {}
            if token_res:
                access_token = token_res.get('response', {}).get('access_token')
        else:
            raise UserError('Username and Password not is set.')
        
        if access_token:
            return {                   
                'name': 'Go to website',
                'res_model': 'ir.actions.act_url',
                'type': 'ir.actions.act_url',
                'target': 'new',
                'url': '%s/web/login/token/%s?db=%s' % (self.name, access_token, self.name.split('//')[1]),
            }
        else:
            raise UserError('Invalid token.')
        
    @api.model
    def remote_action(self, obj_id):
        action = {}
        if isinstance(obj_id, int):
            obj_id = self.browse(obj_id)
        if obj_id.ensure_one():
            module_obj = self.env['ir.module.module']
            try:
                action = obj_id.remote_rsa()
            except:
                action = obj_id.remote()
        
            module_web_enterprise = module_obj.search([('name', '=', 'web_enterprise')])
            if module_web_enterprise and module_web_enterprise.state == 'installed':
                action['target'] = 'self'
                
        return action
    
    def upsert_menu(self):
        act_obj = self.env['ir.actions.server']
        menu_obj = self.env['ir.ui.menu']
        model_id = self.env['ir.model']._get_id(self._name)
        for rec in self:
            action_code = 'action = model.remote_action(%s)' % (rec.id)
            menu_name = rec.name
            try:
                menu_name = menu_name.split('//')[1]
                menu_name = menu_name.split('.')[0]
                menu_name = menu_name.upper()
            except Exception as e:
                _logger.warn(e)
            act_id = act_obj.search([
                ('model_id', '=', model_id),
                ('code', 'ilike', action_code)
            ])
            if not act_id:
                act_id = act_obj.create({
                    'name': menu_name,
                    'model_id': model_id,
                    'state': 'code',
                    'code': action_code,
                })
            else:
                act_id.write({'name': menu_name})
            menu_id = menu_obj.search([('action', '=', '%s,%s' % (act_id._name, act_id.id))])
            if not menu_id:
                menu_id = menu_obj.create({
                    'name': menu_name,
                    'action': '%s,%s' % (act_id._name, act_id.id),
                    'web_icon': 'juragan_webhook,static/img/izi_access.png',
                })
            else:
                menu_id.write({'name': menu_name})
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
                
    def delete_menu(self):
        act_obj = self.env['ir.actions.server']
        menu_obj = self.env['ir.ui.menu']
        model_id = self.env['ir.model']._get_id(self._name)
        for rec in self:
            action_code = 'action = model.remote_action(%s)' % (rec.id)
            act_id = act_obj.search([
                ('model_id', '=', model_id),
                ('code', 'ilike', action_code)
            ])
            if not act_id:
                continue
            menu_id = menu_obj.search([('action', '=', '%s,%s' % (act_id._name, act_id.id))])
            if not menu_id:
                act_id.unlink()
            else:
                menu_id.unlink()
                act_id.unlink()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def sync_order(self):
        if self.get_records_time_limit:
            self.get_orders(domain_code=self.get_records_time_limit)

    @api.model
    def sync_order_model(self):
        servers = self.search([])
        for server in servers:
            server.sync_order()

    def get_orders(self, domain_code=False):
        self.get_records('sale.order', domain_code=domain_code)
        self.get_records('sale.order.pickup.info')

        # Activate cron for this button. TODO: Commented Out to Check Issues.
        # if not self._context.get('run_by_cron'):
        #     cron = self.env.ref('juragan_webhook.cron_webhook_get_order')
        #     if not cron.active:
        #         cron.write({'active': True})
        #     self.cron_id = cron.id

    def get_orders_dependency(self):
        self.get_records('mp.shop.address', loop_commit=False)
        self.get_records('sale.order.cancel.reason', loop_commit=False)
    
    def trigger_import_stock_izi(self):
        mp_list = []
        mp_tokopedia_ids = self.env['mp.tokopedia'].search([])
        for mp_tokopedia_id in mp_tokopedia_ids:
            mp_list.append({
                'channel': 'tokopedia',
                'mp_id': mp_tokopedia_id.izi_id
            })
        mp_shopee_ids = self.env['mp.shopee'].search([])
        for mp_shopee_id in mp_shopee_ids:
            mp_list.append({
                'channel': 'shopee',
                'mp_id': mp_shopee_id.izi_id
            })
        mp_lazada_ids = self.env['mp.lazada'].search([])
        for mp_lazada_id in mp_lazada_ids:
            mp_list.append({
                'channel': 'lazada',
                'mp_id': mp_lazada_id.izi_id
            })
        mp_blibli_ids = self.env['mp.blibli'].search([])
        for mp_blibli_id in mp_blibli_ids:
            mp_list.append({
                'channel': 'blibli',
                'mp_id': mp_blibli_id.izi_id
            })
        r = requests.post(self.name + '/api/ui/stock/import', headers={
            'X-Openerp-Session-Id': self.session_id, 'Content-type': 'application/json'}, json={'data': mp_list})
        res = r.json()
        if r.status_code == 200:
            if res.get('code') != 200:
                raise UserError('Error when IZI get stock from marketplace')
        else:
            raise UserError('Error when IZI get stock from marketplace')

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
            warehouses_by_izi_id = {}
            warehouses = self.env['stock.warehouse'].sudo().search([])
            for wh in warehouses:
                warehouses_by_code[wh.code] = wh
                warehouses_by_izi_id[wh.izi_id] = wh

            products_by_izi_id = {}
            products = self.env['product.product'].sudo().search([('izi_id', '!=', False)])
            for pd in products:
                products_by_izi_id[pd.izi_id] = pd

            # Adjust Stock
            line_vals_by_company_id = {}
            data = res['data']
            for prod in data['res_products_by_wh_id']:
                prod_id = prod['id']
                if prod_id not in products_by_izi_id:
                    raise UserError('Product with izi_id %s not found.' % str(prod_id))
                if products_by_izi_id[prod_id].type != 'product':
                    continue
                for index, rw in enumerate(data['res_warehouse_ids']):
                    wh_id = data['res_warehouse_ids'][index]
                    wh_code = data['res_warehouse_codes'][index]
                    found_warehouse = False

                    if wh_id in warehouses_by_izi_id:
                        found_warehouse = warehouses_by_izi_id[wh_id]
                    elif wh_code in warehouses_by_code:
                        found_warehouse = warehouses_by_code[wh_code]
                        
                    if not found_warehouse:
                        raise UserError('Warehouse not found.')

                    company = found_warehouse.company_id

                    if company.id in line_vals_by_company_id:
                        line_vals_by_company_id[company.id].append((0, 0, {
                            'product_id': products_by_izi_id[prod_id].id,
                            'location_id': found_warehouse.lot_stock_id.id,
                            'company_id': company.id,
                            'product_qty': prod[str(wh_id)]['qty_total'],
                        }))
                    else:
                        line_vals_by_company_id[company.id] = [(0, 0, {
                            'product_id': products_by_izi_id[prod_id].id,
                            'location_id': found_warehouse.lot_stock_id.id,
                            'company_id': company.id,
                            'product_qty': prod[str(wh_id)]['qty_total'],
                        })]

            for company_id in line_vals_by_company_id.keys():
                res = self.env['stock.inventory'].sudo().create({
                    'name': 'Import Stock Data From IZI',
                    # 'location_id': lot_stock_id,
                    # 'filter': 'none',
                    'line_ids': line_vals_by_company_id[company_id],
                    'company_id': company_id
                })
                res.action_start()
                res.with_context(no_push=True).action_validate()

    def export_stock(self):
        res = []
        for mp_tp in self.mp_tokopedia_ids:
            lot_stock_id = mp_tp.wh_id.lot_stock_id.id

            # Check Quant
            quants = self.env['stock.quant'].sudo().search([('product_id.izi_id', '!=', False), ('location_id', '=', lot_stock_id)])
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
        r = requests.post(self.name + '/api/ui/stock/import/data', json={
            'data': res,
        }, headers={
            'X-Openerp-Session-Id': self.session_id,
        })
        res = json.loads(r.text) if r.status_code == 200 else {}
        if res:
            pass

    def retry_get_records(self):
        for log in self.log_ids:
            if log.status == 'failed':
                domain_url = "[('id', '=', %i)]" % int(log.izi_id)
                self.get_records(log.model_name, domain_url=domain_url)

    #
    # Method Generic for API
    #
    def get_records(self, model_name, force_update=False, offset=0, limit=100, order_field='id', sort='asc',
                    retry_login=True, retry_login_count=3, domain_code=False, domain_url=False, loop_commit=True,
                    commit_every=False, commit_on_finish=True):
        """
        Get any records from IZI to store in Odoo.
        :param model_name: model name or code/alias
        :param force_update: record with MD5 hash will not be updated except the hash is different or
                             forced to update with this paramater
        :param offset: index number where to start to paginate
        :param limit: number of record
        :param order_field: order by this field
        :param sort: sort method asc/desc
        :param retry_login:
        :param retry_login_count:
        :param domain_code: custom domain code
        :param domain_url:
        :param loop_commit:
        :param commit_every:
        :param commit_on_finish:
        :return:
        """
        i = 0
        commit_counter = 0
        # Set Default Context
        self = self.set_default_context(model_name)
        while True:
            # check for model code (alias) or model name
            code = code_by_model_name[model_name] if model_name in code_by_model_name else model_name
            # prepare URL to request
            url = self.name + '/api/ui/read/list-detail/%s?offset=%s&limit=%s&order=%s&sort=%s&domain_code=%s' % (
                code, str(offset), str(limit), order_field, sort, domain_code)
            if domain_url:
                url = self.name + '/api/ui/read/list-detail/%s/%s?offset=%s&limit=%s&order=%s&sort=%s&domain_code=%s' % (
                    code, domain_url, str(offset), str(limit), order_field, sort, domain_code)
            # do request
            r = requests.get(url, headers={'X-Openerp-Session-Id': self.session_id})
            # getting response data
            res = r.json() if r.status_code == 200 else {}
            # do process response data
            if res.get('code') == 200:
                get_number = offset if res['meta']['total_item'] > offset else res['meta']['total_item']
                if get_number:
                    self.env.user.notify_info('Get Records from IZI App and Marketplace: %s (%s)' % (
                        model_name.replace('.', ' ').title(), get_number))
                if len(res.get('data')) == 0:
                    break
                else:
                    offset += limit
                # Prepare Server Log
                ServerLog = self.env['webhook.server.log'].sudo()
                server_logs = ServerLog.search([('model_name', '=', model_name), ('status', '=', 'failed')])
                server_logs_by_izi_id = {}
                for sl in server_logs:
                    server_logs_by_izi_id[sl.izi_id] = sl
                # Start Read Record
                for res_values in res.get('data'):
                    i += 1
                    commit_counter += 1
                    error_message = False
                    izi_id = res_values.get('id')
                    _logger.info('(%s) Get record %s IZI ID %s' % (i, model_name, izi_id))
                    # Detail Log
                    self.log_record(model_name, res_values)
                    # Check Existing Record
                    record = self.get_existing_record(
                        model_name, res_values)
                    if self.check_skip(model_name, record, res_values):
                        continue
                    # Start Save Record
                    try:
                        # do update if record is already exists
                        if record:
                            # store MD5 hash of data if the field is available in the current model
                            if 'izi_md5' in self.env[model_name]._fields:
                                is_update = False
                                izi_md5 = hashlib.md5(json.dumps(
                                    res_values).encode('utf-8')).hexdigest()
                                if force_update:
                                    # need update if forced by parameter
                                    is_update = True
                                else:
                                    # need update if current hash is different
                                    if record.izi_md5 != izi_md5:
                                        is_update = True
                                if is_update:
                                    # do update
                                    values = self.mapping_field(
                                        model_name, res_values, update=True)
                                    values.update({
                                        'izi_md5': izi_md5
                                    })
                                    values = self.custom_before_write(
                                        model_name, values)
                                    record.sudo().write(values)
                                    self.custom_after_write(model_name, record, values)
                            else:
                                # always update the data if there's no MD5 hash field in the current model
                                values = self.mapping_field(
                                    model_name, res_values, update=True)
                                values = self.custom_before_write(
                                    model_name, values)
                                record.sudo().write(values)
                                self.custom_after_write(model_name, record, values)
                        else:
                            # do create if there's no existing record
                            values = self.mapping_field(
                                model_name, res_values, update=False)
                            if 'izi_md5' in self.env[model_name]._fields:
                                values.update({
                                    'izi_md5': hashlib.md5(json.dumps(res_values).encode('utf-8')).hexdigest()
                                })
                            values = self.custom_before_create(model_name, values)
                            if self.check_skip_before_create(model_name, values):
                                continue
                            record = self.env[model_name].sudo().create(values)
                            self.custom_after_create(model_name, record, values)
                        if commit_every:
                            if isinstance(commit_every, int):
                                if commit_every == commit_counter:
                                    # self.env.cr.commit()
                                    commit_counter = 0
                        elif loop_commit:
                            # self.env.cr.commit()
                            pass
                    except Exception as e:
                        _logger.info('Failed Create / Update %s. Cause %s' % (model_name, str(e)))
                        if not self.is_skip_error:
                            raise UserError(str(e))
                        else:
                            error_message = str(e)
                    # Check Log
                    if not error_message:
                        if izi_id in server_logs_by_izi_id:
                            server_logs_by_izi_id[izi_id].write({
                                'res_id': record.id,
                                'status': 'success',
                                'last_retry_time': fields.Datetime.now(),
                            })
                    else:
                        log_values = {
                            'name': '%s %s' % (str(model_name), str(izi_id)),
                            'server_id': self.id,
                            'model_name': model_name,
                            'izi_id': izi_id,
                            'status': 'failed',
                            'res_id': False,
                            'notes': self.get_notes(model_name, res_values),
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
                    self.get_records(model_name, offset, limit,
                                     order_field, sort, retry_login=False)
                else:
                    break
            else:
                break
        if commit_on_finish:
            #### self.env.cr.commit()
            pass  ####
    
    def set_default_context(self, model_name):
        if model_name == 'sale.order':
            self = self.with_context(get_orders=True)
        return self

    def get_notes(self, model_name, values):
        notes = False
        if model_name == 'sale.order':
            if values.get('mp_invoice_number', False):
                notes = values.get('mp_invoice_number')
        return str(notes)

    def check_skip(self, model_name, record, values):
        if self.env.context.get('get_products') and self.is_skip_product_not_mapping \
            and model_name in ('product.product', 'product.template') and not record:
            return True
        return False

    def check_skip_before_create(self, model_name, values):
        # Skip create order that is not draft or cancel if quotation only.
        if model_name == 'sale.order':
            if self.skip_cancel_order and values.get('order_status', False) == 'cancel':
                return True
            if self.skip_waiting_order and values.get('order_status', False) == 'waiting':
                return True
        return False

    def custom_after_write(self, model_name, record, values):
        if model_name == 'sale.order':
            # Action. Only allow action_cancel if quotation only.
            if not self.is_quotation_only or record.order_status == 'cancel':
                _logger.info('Action By Order Status')
                record.with_context(no_push=True).action_by_order_status()
        if model_name == 'product.staging':
            if record.sp_attributes:
                for attribute in record.sp_attributes:
                    attribute.sudo().unlink()
            if record.sp_logistics:
                for logistic in record.sp_logistics:
                    logistic.sudo().unlink()
            if self.env.context.get('get_products'):
                if record.product_image_staging_ids:
                    for image in record.product_image_staging_ids:
                        image.sudo().unlink()
            if record.lz_attributes:
                for attr in record.lz_attributes:
                    attr.sudo().unlink()

    def custom_before_write(self, model_name, values):
        res = values.copy()
            
        if model_name == 'sale.order':
            # Get Account
            mp_tokopedia_id = values.get('mp_tokopedia_id', False)
            mp_shopee_id = values.get('mp_shopee_id', False)
            mp_lazada_id = values.get('mp_lazada_id', False)
            mp_blibli_id = values.get('mp_blibli_id', False)
            mp_account = False
            if mp_tokopedia_id:
                mp_account = self.env['mp.tokopedia'].sudo().browse(mp_tokopedia_id)
            elif mp_shopee_id:
                mp_account = self.env['mp.shopee'].sudo().browse(mp_shopee_id)
            elif mp_lazada_id:
                mp_account = self.env['mp.lazada'].sudo().browse(mp_lazada_id)
            elif mp_blibli_id:
                mp_account = self.env['mp.blibli'].sudo().browse(mp_blibli_id)
            if not mp_account:
                raise UserError('Marketplace Account not found!')

            # CUSTOM FASTPRINT -> ONLY CREATE PARENT PARTNER, NOT DELIVERY PARTNER
            # Get Partner From Account or Search Partner With Same Phone / Mobile Or Email For Tokopedia
            _logger.info('Create Customer')
            partner = self.env['res.partner'].sudo().search([('phone', '=', values.get('mp_recipient_address_phone'))], limit=1)
            if not partner:
                partner = self.env['res.partner'].sudo().search([('street', '=', values.get('mp_recipient_address_full').upper())], limit=1)

            res_country = self.env['res.country'].sudo().search([('name', '=ilike', values.get('mp_recipient_address_country'))], limit=1)
            if not res_country:
                res_country = self.env['res.country'].sudo().search([('code', '=ilike', values.get('mp_recipient_address_country'))], limit=1)
            
            res_country_state = self.env['res.country.state'].sudo().search([('name', '=ilike', values.get('mp_recipient_address_state'))], limit=1)
            if not res_country_state:
                res_country_state = self.env['res.country.state'].sudo().search([('code', '=ilike', values.get('mp_recipient_address_state'))], limit=1)

            if not partner:
                partner = self.env['res.partner'].sudo().create({
                    'name': values.get('mp_recipient_address_name').upper() if (values.get('mp_recipient_address_name') != None and values.get('mp_recipient_address_name') != False) else False,
                    'street': values.get('mp_recipient_address_full').upper() if (values.get('mp_recipient_address_full') != None and values.get('mp_recipient_address_full') != False) else False,
                    'city': values.get('mp_recipient_address_city').upper() if (values.get('mp_recipient_address_city') != None and values.get('mp_recipient_address_city') != False) else False,
                    'phone': values.get('mp_recipient_address_phone'),
                    'zip': values.get('mp_recipient_address_zipcode'),
                    'state_id': res_country_state.id if res_country_state else False,
                    'country_id': res_country.id if res_country else False,
                })
            else:
                partner.sudo().write({
                    'name': values.get('mp_recipient_address_name').upper() if (values.get('mp_recipient_address_name') != None and values.get('mp_recipient_address_name') != False) else False,
                    'street': values.get('mp_recipient_address_full').upper() if (values.get('mp_recipient_address_full') != None and values.get('mp_recipient_address_full') != False) else False,
                    'city': values.get('mp_recipient_address_city').upper() if (values.get('mp_recipient_address_city') != None and values.get('mp_recipient_address_city') != False) else False,
                    'phone': values.get('mp_recipient_address_phone'),
                    'zip': values.get('mp_recipient_address_zipcode'),
                    'state_id': res_country_state.id if res_country_state else False,
                    'country_id': res_country.id if res_country else False,
                })

            # Sale Order only update order_status and resi
            res = {
                'order_status': res['order_status'],
                'order_status_notes': res['order_status_notes'],
                'mp_awb_number': res['mp_awb_number'],
                'mp_delivery_carrier_name': res['mp_delivery_carrier_name'],
                'mp_delivery_carrier_type': res['mp_delivery_carrier_type'],
                'mp_awb_url': res['mp_awb_url'],
                'tp_cancel_request_create_time': res['tp_cancel_request_create_time'],
                'tp_cancel_request_reason': res['tp_cancel_request_reason'],
                'tp_cancel_request_status': res['tp_cancel_request_status'],
                'tp_comment': res['tp_comment'],
                'mp_delivery_type': res['mp_delivery_type'],
                'mp_recipient_address_city': res['mp_recipient_address_city'],
                'mp_recipient_address_name': res['mp_recipient_address_name'],
                'mp_recipient_address_district': res['mp_recipient_address_district'],
                'mp_recipient_address_country': res['mp_recipient_address_country'],
                'mp_recipient_address_zipcode': res['mp_recipient_address_zipcode'],
                'mp_recipient_address_phone': res['mp_recipient_address_phone'],
                'mp_recipient_address_state': res['mp_recipient_address_state'],
                'mp_recipient_address_full': res['mp_recipient_address_full'],
                'shipping_date': res['shipping_date'],
                'mp_accept_deadline': res['mp_accept_deadline'],
                'partner_id': partner.id,
                'partner_invoice_id': partner.id,
                'company_id': res['company_id'],
            }
            # for shopee
            if values['sp_order_status']:
                res['sp_order_status'] = values['sp_order_status']
            if values['cancel_by_customer']:
                res['cancel_by_customer'] = values['cancel_by_customer']
            if values['sp_cancel_by']:
                res['sp_cancel_by'] = values['sp_cancel_by']
            # for lazada
            if values['lz_order_status']:
                res['lz_order_status'] = values['lz_order_status']
            # for blibli
            if values['bli_order_status']:
                res['bli_order_status'] = values['bli_order_status']

            # update delivery info
            order_obj = self.env['sale.order'].search([('izi_id','=',values['id'])], limit=1)
            if order_obj and order_obj.mp_delivery_carrier_name != values['mp_delivery_carrier_name']:
                product_delivery = self.env['product.product'].search([('name','=ilike',values['mp_delivery_carrier_name'])], limit=1)
                for order_line in order_obj.order_line:
                    if order_line.is_delivery:
                        order_line.name = values['mp_delivery_carrier_name']
                        if product_delivery:
                            order_line.product_id = product_delivery.id
                            order_line.product_template_id = product_delivery.product_tmpl_id

        elif model_name == 'product.template':
            if 'name' in res:
                del res['name']
            if 'default_code' in res:
                del res['default_code']
            if 'list_price' in res:
                del res['list_price']

        elif model_name == 'product.product':
            if 'name' in res:
                del res['name']
            if 'default_code' in res:
                del res['default_code']
            if 'list_price' in res:
                del res['list_price']
        return res
        
    def log_record(self, model_name, values):
        if model_name == 'sale.order':
            _logger.info('Start Create Sale Order %s' % str(values.get('mp_invoice_number')))

    def custom_before_create(self, model_name, values):
        res = values.copy()

        if model_name == 'sale.order':
            # Don't include SO number from IZI
            res.pop('name')

            mp_tokopedia_id = values.get('mp_tokopedia_id', False)
            mp_shopee_id = values.get('mp_shopee_id', False)
            mp_lazada_id = values.get('mp_lazada_id', False)
            mp_blibli_id = values.get('mp_blibli_id', False)
            mp_account = False
            marketplace = False
            if mp_tokopedia_id:
                mp_account = self.env['mp.tokopedia'].sudo().browse(mp_tokopedia_id)
                marketplace = 'TOKOPEDIA'
            elif mp_shopee_id:
                mp_account = self.env['mp.shopee'].sudo().browse(mp_shopee_id)
                marketplace = 'SHOPEE'
            elif mp_lazada_id:
                mp_account = self.env['mp.lazada'].sudo().browse(mp_lazada_id)
                marketplace = 'LAZADA'
            elif mp_blibli_id:
                mp_account = self.env['mp.blibli'].sudo().browse(mp_blibli_id)
                marketplace = 'BLIBLI'
            if not mp_account:
                raise UserError('Marketplace Account not found!')
            
            # Get Warehouse
            if mp_account.wh_id:
                res['warehouse_id'] = mp_account.wh_id.id
            
            # Get Company
            if mp_account.company_id:
                res['company_id'] = mp_account.company_id.id

            # CUSTOM FASTPRINT -> ONLY CREATE PARENT PARTNER, NOT DELIVERY PARTNER
            # Get Partner From Account or Search Partner With Same Phone / Mobile Or Email For Tokopedia
            _logger.info('Create Customer')
            partner = self.env['res.partner'].sudo().search([('phone', '=', values.get('mp_recipient_address_phone'))], limit=1)
            if not partner:
                partner = self.env['res.partner'].sudo().search([('street', '=', values.get('mp_recipient_address_full').upper())], limit=1)

            res_country = self.env['res.country'].sudo().search([('name', '=ilike', values.get('mp_recipient_address_country'))], limit=1)
            if not res_country:
                res_country = self.env['res.country'].sudo().search([('code', '=ilike', values.get('mp_recipient_address_country'))], limit=1)
            
            res_country_state = self.env['res.country.state'].sudo().search([('name', '=ilike', values.get('mp_recipient_address_state'))], limit=1)
            if not res_country_state:
                res_country_state = self.env['res.country.state'].sudo().search([('code', '=ilike', values.get('mp_recipient_address_state'))], limit=1)

            if not partner:
                partner = self.env['res.partner'].sudo().create({
                    'name': values.get('mp_recipient_address_name').upper() if (values.get('mp_recipient_address_name') != None and values.get('mp_recipient_address_name') != False) else False,
                    'street': values.get('mp_recipient_address_full').upper() if (values.get('mp_recipient_address_full') != None and values.get('mp_recipient_address_full') != False) else False,
                    'city': values.get('mp_recipient_address_city').upper() if (values.get('mp_recipient_address_city') != None and values.get('mp_recipient_address_city') != False) else False,
                    'phone': values.get('mp_recipient_address_phone'),
                    'zip': values.get('mp_recipient_address_zipcode'),
                    'state_id': res_country_state.id if res_country_state else False,
                    'country_id': res_country.id if res_country else False,
                })
            else:
                partner.sudo().write({
                    'name': values.get('mp_recipient_address_name').upper() if (values.get('mp_recipient_address_name') != None and values.get('mp_recipient_address_name') != False) else False,
                    'street': values.get('mp_recipient_address_full').upper() if (values.get('mp_recipient_address_full') != None and values.get('mp_recipient_address_full') != False) else False,
                    'city': values.get('mp_recipient_address_city').upper() if (values.get('mp_recipient_address_city') != None and values.get('mp_recipient_address_city') != False) else False,
                    'phone': values.get('mp_recipient_address_phone'),
                    'zip': values.get('mp_recipient_address_zipcode'),
                    'state_id': res_country_state.id if res_country_state else False,
                    'country_id': res_country.id if res_country else False,
                })
            res['partner_id'] = partner.id
            res['partner_invoice_id'] = partner.id

            # Add Order Component
            _logger.info('Add Order Component')
            component_configs = self.env['order.component.config'].sudo().search([('active', '=', True),
                '|', '|', '|', ('mp_tokopedia_ids', 'in', values.get('mp_tokopedia_id')),
                ('mp_shopee_ids', 'in', values.get('mp_shopee_id')),
                ('mp_lazada_ids', 'in', values.get('mp_lazada_id')),
                ('mp_blibli_ids', 'in', values.get('mp_blibli_id'))])
            for component_config in component_configs:
                if values.get('date_order', False):
                    if component_config.date_start and values['date_order'] < component_config.date_start.strftime('%Y-%m-%d %H:%M:%S'):
                        continue    
                    if component_config.date_end and values['date_order'] > component_config.date_end.strftime('%Y-%m-%d %H:%M:%S'):
                        continue
                # Process to Remove Product First
                for line in component_config.line_ids:
                    if line.component_type == 'remove_product':
                        new_order_line = []
                        for index, val in enumerate(values['order_line']):
                            if val[2].get('is_discount') and line.remove_discount:
                                continue
                            if val[2].get('is_delivery') and line.remove_delivery:
                                continue
                            if val[2].get('is_insurance') and line.remove_insurance:
                                continue
                            if val[2].get('is_adjustment') and line.remove_adjustment:
                                continue
                            if val[2].get('product_id') in line.remove_product_ids.ids:
                                continue
                            new_order_line.append(val)
                        values['order_line'] = new_order_line.copy()
                # Then Discount
                for line in component_config.line_ids:
                    if line.component_type == 'discount_line':
                        for index, val in enumerate(values['order_line']):
                            if val[2].get('is_discount', False) or val[2].get('is_delivery', False) or val[2].get('is_insurance', False):
                                continue
                            if line.discount_line_method == 'input':
                                if line.discount_line_product_type == 'all' or (val[2].get('product_id', False) and val[2].get('product_id') in line.discount_line_product_ids.ids):
                                    price_unit = val[2]['price_unit']
                                    if 100 - line.percentage_value > 0:
                                        new_price_unit = round(100 * price_unit / (100 - line.percentage_value))
                                    values['order_line'][index][2].update({
                                        'price_unit': new_price_unit,
                                        'discount': line.percentage_value,
                                    })
                            elif line.discount_line_method == 'calculated':
                                if line.discount_line_product_type == 'all' or (val[2].get('product_id', False) and val[2].get('product_id') in line.discount_line_product_ids.ids):
                                    price_unit = val[2]['price_unit']
                                    product_id = val[2]['product_id']
                                    product = self.env['product.product'].sudo().browse(product_id)
                                    if product:
                                        normal_price = 0
                                        if product.product_variant_stg_ids:
                                            normal_price = product.product_variant_stg_ids[0].price_custom
                                        if normal_price == 0 and product.product_tmpl_id.product_staging_ids:
                                            for staging in product.product_tmpl_id.product_staging_ids:
                                                if (values['mp_tokopedia_id'] and values['mp_tokopedia_id'] == staging.mp_tokopedia_id.id) \
                                                    or (values['mp_shopee_id'] and values['mp_shopee_id'] == staging.mp_shopee_id.id) \
                                                    or (values['mp_lazada_id'] and values['mp_lazada_id'] == staging.mp_lazada_id.id) \
                                                    or (values['mp_blibli_id'] and values['mp_blibli_id'] == staging.mp_blibli_id.id): 
                                                    normal_price = staging.list_price
                                                    break
                                        if normal_price == 0:
                                            normal_price = product.product_tmpl_id.list_price
                                            for tax in product.product_tmpl_id.taxes_id:
                                                if tax.price_include:
                                                    continue
                                                elif tax.amount_type == 'percent' and tax.amount > 0:
                                                    normal_price = int(round(normal_price * (100 + tax.amount) / 100))
                                        # Calculate Discount %
                                        discount_percentage = 0
                                        if normal_price > 0 and price_unit > 0:
                                            discount_percentage = int(round((normal_price - price_unit) * 100 / normal_price))
                                            if discount_percentage > 0:
                                                values['order_line'][index][2].update({
                                                    'price_unit': normal_price,
                                                    'discount': discount_percentage,
                                                })
                # Then Add Tax
                for line in component_config.line_ids:
                    if line.component_type == 'tax_line':
                        for index, val in enumerate(values['order_line']):
                            if val[2].get('is_discount', False) or val[2].get('is_delivery', False) or val[2].get('is_insurance', False):
                                continue
                            if line.account_tax_id and line.account_tax_id.amount_type == 'percent':
                                percentage = line.account_tax_id.amount
                                if percentage > 0:
                                    price_unit = val[2]['price_unit']
                                    new_price = (price_unit * 100) / (100 + percentage)
                                    values['order_line'][index][2].update({
                                        'price_unit': new_price,
                                        'tax_id': [(6, 0, [line.account_tax_id.id])],
                                    })
                # Then Add Product
                for line in component_config.line_ids:
                    if line.component_type == 'add_product':
                        # Calculate Total Price
                        amount_total = 0
                        for index, val in enumerate(values['order_line']):
                            amount_total += val[2].get('price_total')

                        if line.additional_product_id:
                            price_unit = 0
                            if line.fixed_value:
                                price_unit = line.fixed_value
                            elif line.percentage_value:
                                price_unit = round(line.percentage_value * amount_total / 100)
                            values['order_line'].append((0, 0, {
                                'name': line.name,
                                'product_id': line.additional_product_id.id,
                                'product_uom_qty': 1.0,
                                'price_subtotal': price_unit,
                                'price_total': price_unit,
                                'price_unit': price_unit,
                                'discount': 0.0,
                                'is_discount': True,
                            }))

            res['order_line'] = values['order_line']

            # CUSTOM FASTPRINT -> SET CRM TEAM 
            res['team_id'] = 6

            # CUSTOM FASTPRINT -> SET NOTE ORDER
            res['note'] = '- PAID VIA %s %s\n' % (marketplace, self.env['res.company'].sudo().search([('id', '=', values.get('company_id'))], limit=1).name)
            res['note'] += '- %s\n' % (res['mp_invoice_number'])

            _logger.info('Preparation Done')
        return res

    def custom_after_create(self, model_name, record, values):
        if model_name == 'sale.order':
            # Action. Only allow action_cancel if quotation only.
            if not self.is_quotation_only or record.order_status == 'cancel':
                _logger.info('Action By Order Status')
                record.with_context(no_push=True).action_by_order_status()
            # Notify
            _logger.info('Notify')
            if self.env.user:
                self.env.user.notify_info('New Order from Marketplace %s, with total amount %s. Delivery to %s.' % (record.mp_invoice_number, record.amount_total, record.mp_recipient_address_city))
            _logger.info('Create Sales Order Done')

    def get_existing_record_from_mapping(self, record, model_name, values):
        res = record
        if model_name == 'product.template':
            mapping = self.env['product.mapping'].sudo().search([('product_template_izi_id', '=', values['id'])], limit=1)
            if mapping and mapping.product_id and mapping.product_id.product_tmpl_id:
                res = mapping.product_id.product_tmpl_id

                # Check if exist record with izi and record from mapping are different
                if record and record.id != res.id:
                    record.izi_id = False 

                res.izi_id = values['id']
                print('Product Template Mapping %s' % mapping.product_id.product_tmpl_id.name)
        if model_name == 'product.product':
            mapping = self.env['product.mapping'].sudo().search([('product_product_izi_id', '=', values['id'])], limit=1)
            if mapping:
                # Check Product Mapping for Order When Has Context get_orders. BUT Do Not Set izi_id!
                if self.env.context.get('get_orders') and mapping.order_product_id:
                    res = mapping.order_product_id
                    print('Product in Order Mapping %s' % mapping.order_product_id.name)
                elif mapping.product_id:
                    res = mapping.product_id

                    # Check if exist record with izi and record from mapping are different
                    if record and record.id != res.id:
                        record.izi_id = False 

                    res.izi_id = values['id']
                    print('Product Variant Mapping %s' % mapping.product_id.name)
        if model_name == 'stock.warehouse':
            mapping = self.env['warehouse.mapping'].sudo().search([('warehouse_izi_id', '=', values['id'])], limit=1)
            if mapping and mapping.warehouse_id:
                res = mapping.warehouse_id

                # Check if exist record with izi and record from mapping are different
                if record and record.id != res.id:
                    record.izi_id = False

                res.izi_id = values['id']
                print('Warehouse Mapping %s' % mapping.warehouse_id.name)
        if model_name == 'res.company':
            mapping = self.env['company.mapping'].sudo().search([('company_izi_id', '=', values['id'])], limit=1)
            if mapping and mapping.company_id:
                res = mapping.company_id

                # Check if exist record with izi and record from mapping are different
                if record and record.id != res.id:
                    record.izi_id = False

                res.izi_id = values['id']
                print('Company Mapping %s' % mapping.company_id.name)
        if model_name == 'mp.lazada.product.attr':
            if 'id' in values['item_id_staging']:
                prod_staging_by_izi_id = values['item_id_staging']['id']
                prod_staging = self.env['product.staging'].sudo().search([('izi_id', '=', prod_staging_by_izi_id)])
                for attr in prod_staging.lz_attributes:
                    if attr.attribute_id.izi_id == values['attribute_id']['id'] and attr.attribute_id.name == values['attribute_id']['name']:
                        res = attr
                        res.izi_id = values['id']
                        break
        if model_name == 'sale.order':
            if self.check_invoice_number and 'mp_invoice_number' in values and values.get('mp_invoice_number'):
                order = self.env['sale.order'].search([('mp_invoice_number', '=', values.get('mp_invoice_number'))], limit=1)
                if order:
                    res = order[0]
        if model_name == 'mp.lazada.category.attr.opt':
            if res:
                if res.name != values['name']:
                    res = self.env[model_name].sudo().search([('name','=',values['name'])])
        if model_name == 'mp.blibli.item.attr.option':
            if res:
                if res.name != values['name']:
                    res = self.env[model_name].sudo().search([('name','=',values['name'])])
        return res

    def get_existing_record(self, model_name, values, mandatory=False):
        if 'id' not in values:
            raise UserError('Field id not found in the values.')
        Model = self.env[model_name].sudo()

        # check record exist with izi_id
        if 'active' in Model._fields:
            domain = ['&', ('izi_id', '=', values['id']), '|', ('active', '=', True), ('active', '=', False)]
        else:
            domain = [('izi_id', '=', values['id'])]
        record = Model.search(domain, limit=1)
        
        record = self.get_existing_record_from_mapping(record, model_name, values)
        
        if not record:
            if model_name in existing_fields_by_model_name and existing_fields_by_model_name[model_name]:
                for field_name in existing_fields_by_model_name[model_name]:
                    if field_name in values and values[field_name]:
                        domain = ['|'] + domain + [(field_name, '=', values[field_name])]
                record = Model.search(domain, limit=1)

        if not record and mandatory:
            # Except,
            # If Get Products and Skip Product Mapping. Do not Raise Error.
            if self.env.context.get('get_products') and self.is_skip_product_not_mapping:
                return record
            
            raise UserError('Record not found model_name: %s, izi_id: %s. Import First.' % (model_name, values['id']))
        return record

    def mapping_field(self, model_name, values, update=False):
        """
        Prepare values to store into Odoo
        :param model_name: model name
        :param values: record values from IZI or external resources
        :param update: If is is True then prepare the values for updating the existing records
        :return: dict
        """
        Model = self.env[model_name].sudo()
        res_values = {}

        if model_name in ['product.template']:
            values['image_1920'] = values.pop('image')

        for key in values:
            # skip the field-value if it's declared in removed fields
            if model_name in removed_fields and key in removed_fields[model_name]:
                continue
            if key in Model._fields:
                if key == 'id':
                    res_values[key] = values[key]
                    res_values['izi_id'] = values[key]
                elif isinstance(Model._fields[key], fields.Selection) and isinstance(values[key], int):
                    values[key] = str(values[key])  # Since Odoo 13.0 all selection should be string.
                elif isinstance(Model._fields[key], fields.Many2one):
                    if values[key] and 'id' in values[key]:
                        comodel_name = Model._fields[key].comodel_name
                        if comodel_name == model_name:
                            # If it has relation to itself, skipped, handle manually in custom_mapping_field
                            if model_name not in processed_model_with_many2one_itself:
                                continue
                        record = self.get_existing_record(comodel_name, values[key], mandatory=True)
                        if record:
                            res_values[key] = record.id
                    else:
                        res_values[key] = False
                elif isinstance(Model._fields[key], fields.Binary):
                    img = False
                    if not self.is_skip_image:
                        if values[key] and isinstance(values[key], str) and ('http://' in values[key] or 'https://' in values[key]):
                            try:
                                img = b64encode(requests.get(values[key]).content)
                            except Exception as e:
                                try:
                                    img = values[key].encode('utf-8')
                                except Exception as ex:
                                    _logger.error(str(ex))
                        else:
                            if values[key] != None and values[key] != False:
                                img = values[key].encode('utf-8')
                        if not img:
                            if key in ['image', 'image_1920']:
                                if model_name in ['product.template', 'product.staging', 'product.product', 'product.staging.variant']:
                                    if values.get('image_url_external') and isinstance(values.get('image_url_external'), str) and ('http://' in values.get('image_url_external') or 'https://' in values.get('image_url_external')) and values.get('image_url_external') != None and values.get('image_url_external') != False:
                                        img = b64encode(requests.get(values.get('image_url_external')).content)
                                elif model_name in ['product.image', 'product.image.staging']:
                                    if values.get('url_external') and isinstance(values.get('url_external'), str) and ('http://' in values.get('url_external') or 'https://' in values.get('url_external')) and values.get('url_external') != None and values.get('url_external') != False:
                                        img = b64encode(requests.get(values.get('url_external')).content)
                    res_values[key] = img

                elif isinstance(Model._fields[key], fields.Selection) and values[key] and 'value' in values[key]:
                    res_values[key] = values[key]['value']
                elif values[key] and isinstance(Model._fields[key], fields.Many2many):
                    comodel_name = Model._fields[key].comodel_name
                    if comodel_name == model_name:
                        # If it has relation to itself, skipped, handle manually in custom_mapping_field
                        continue
                    val_ids = []
                    for val in values[key]:
                        record = self.get_existing_record(comodel_name, val, mandatory=True)
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
        elif model_name == 'product.staging':
            if res_values.get('mp_tokopedia_id'):
                res_values['mp_type'] = 'Tokopedia'
            elif res_values.get('mp_shopee_id'):
                res_values['mp_type'] = 'Shopee'
            elif res_values.get('mp_lazada_id'):
                res_values['mp_type'] = 'Lazada'
            elif res_values.get('mp_blibli_id'):
                res_values['mp_type'] = 'Blibli'
        elif model_name == 'mp.tokopedia':
            res_values['active'] = True
            res_values['server_id'] = self.id
        elif model_name == 'mp.shopee':
            res_values['active'] = True
            res_values['server_id'] = self.id
        elif model_name == 'mp.lazada':
            res_values['active'] = True
            res_values['server_id'] = self.id
        elif model_name == 'mp.blibli':
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
            'view_type': 'form',
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
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'webhook.get.custom.model.records.wizard',
            'res_id': kwargs.get('res_id', None),
            'type': 'ir.actions.act_window',
            'target': 'new'
        }

    def get_companies(self):
        url = self.name + '/api/ui/read/list-detail/%s?offset=%s&limit=%s&order=%s&sort=%s' % (
            'res.company', 0, 1000, 'id', 'asc')
        r = requests.get(url, headers={'X-Openerp-Session-Id': self.session_id})
        res = r.json() if r.status_code == 200 else {}
        if res.get('code') == 200:
            for res_values in res.get('data'):
                company = self.get_existing_record('res.company', res_values)
                if not company:
                    self.env['res.company'].sudo().create({
                        'name': res_values.get('name'),
                        'street': res_values.get('street'),
                        'street2': res_values.get('street2'),
                        'city': res_values.get('city'),
                        'state_id': res_values.get('state_id') if res_values.get('state_id') else False,
                        'zip': res_values.get('zip'),
                        'website': res_values.get('website'),
                        'email': res_values.get('email'),
                        'izi_id': res_values.get('id'),
                    })
                else:
                    company.sudo().write({
                        'izi_id': res_values.get('id')
                    })

    def get_warehouses(self):
        url = self.name + '/api/ui/read/list-detail/%s?offset=%s&limit=%s&order=%s&sort=%s&domain_code=%s' % (
            'stock.warehouse', 0, 1000, 'id', 'asc', 'marketplace')
        r = requests.get(url, headers={'X-Openerp-Session-Id': self.session_id})
        res = r.json() if r.status_code == 200 else {}
        if res.get('code') == 200:
            for res_values in res.get('data'):
                wh = self.get_existing_record('stock.warehouse', res_values)
                if not wh:
                    company = self.get_existing_record('res.company', res_values.get('company_id'))
                    wh = self.env['stock.warehouse'].sudo().create({
                        'name': res_values.get('name'),
                        'company_id': company.id,
                        'partner_id': company.partner_id.id,
                        'code': res_values.get('code'),
                        'izi_id': res_values.get('id'),
                    })
                if wh.lot_stock_id and res_values.get('lot_stock_id'):
                    izi_location_id = res_values.get('lot_stock_id')
                    wh.lot_stock_id.izi_id = izi_location_id

    # Deprecated
    def mapping_field_post(self, model_name, obj_id):
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
                res_values[key] = img
            # elif fld_type == 'many2many':
            #     if res_values[key]:
            #         m2m_ids = res_values[key]
            #         comodel_name = model_fld[key].comodel_name
            #         comodel_ids = self.env[comodel_name].sudo().browse(m2m_ids)
            #         not_imported_ids = comodel_ids.filtered(lambda x: not x.izi_id)
            #         if not_imported_ids:
            #             msg = 'Not imported: %s with this izi_id %s not imported yet.' % (model_fld[key].string, str(not_imported_ids))
            #             _logger.warning(msg=msg)
            #         res_values[key] = [(6, 0, comodel_ids)]
            #     else:
            #         res_values.pop(key)
            elif fld_type == 'one2many':
                o2m_ids = res_values[key]
                comodel_fld = model_fld[key]
                comodel_name = comodel_fld._related_comodel_name
                if o2m_ids and key == 'attribute_line_ids':
                    attr_vals = []
                    for res_id in res_values[key]:
                        attr_id = self.env[comodel_name].sudo().browse(res_id)
                        attr_vals.append({
                            'attribute_id': attr_id.attribute_id.izi_id,
                            'attribute_value_ids': attr_id.value_ids.mapped('izi_id'),
                        })
                    res_values['varian_table'] = {'attribute_lines': attr_vals}
                elif o2m_ids and key == 'product_wholesale_ids':
                    for whsl in res_values[key]:
                        whsl_id = self.env[comodel_name].sudo().browse(whsl)
                        whsl_vals = whsl_id.read(
                            ['izi_id', 'min_qty', 'max_qty',
                             'price_wholesale'])[0]
                        if res_values.get('wholesale'):
                            res_values['wholesale'].append({
                                "id": whsl_vals.get('izi_id'),
                                "min_qty": whsl_vals.get('min_qty', 0),
                                "max_qty": whsl_vals.get('max_qty', 0),
                                "price_wholesale": whsl_vals.get('price_wholesale', 0),
                            })
                        else:
                            res_values['wholesale'] = [{
                                "id": whsl_vals.get('izi_id'),
                                "min_qty": whsl_vals.get('min_qty', 0),
                                "max_qty": whsl_vals.get('max_qty', 0),
                                "price_wholesale": whsl_vals.get('price_wholesale', 0),
                            }]
                elif o2m_ids:
                    for o2m_id in o2m_ids:
                        childs.append({
                            'model_name': comodel_name, 'obj_id': o2m_id})
                        childs = self.mapping_field_post(
                            comodel_name, o2m_id, True, childs)
                res_values.pop(key)
        # Custom Mapping Field, not needed
        # res_values = self.custom_mapping_field(model_name, res_values)
        res_values['obj_id'] = obj_id
        return res_values, childs

    def before_send_product(self, model_name, obj_id):
        res_values = {}
        if model_name == 'product.template':
            Model = self.env[model_name].sudo()
            Model_id = Model.browse(obj_id)
            if Model_id.product_image_ids:
                for att_ids in Model_id.product_image_ids:
                    attr_data = self.mapping_field_post_one('product.image', att_ids.id)
                    self.post_records('product.image', attr_data, True)
            if Model_id.product_variant_ids:
                varian_list = []
                len_value_ids = 0
                for prd_id in Model_id.product_variant_ids:
                    prd_vals = {}
                    value_ids = prd_id.attribute_value_ids
                    if len(value_ids) == 1:
                        prd_vals['attribute1'] = value_ids.attribute_id.izi_id
                        prd_vals['attribute_value1'] = value_ids.izi_id
                        len_value_ids = 1
                    elif len(value_ids) >= 2:
                        prd_vals['attribute1'] = value_ids[0].attribute_id.izi_id
                        prd_vals['attribute_value1'] = value_ids[0].izi_id
                        prd_vals['attribute2'] = value_ids[1].attribute_id.izi_id
                        prd_vals['attribute_value2'] = value_ids[1].izi_id
                        len_value_ids = 2
                    prd_vals.update({
                        "price_custom": prd_id.lst_price,
                        "qty_available": prd_id.qty_available,
                        "default_code": prd_id.default_code,
                        "image": '',
                        "is_active": prd_id.active and 'true' or 'false'
                    })
                    varian_list.append(prd_vals)
                res_values['varian_table'] = {'varian_list': varian_list}
                res_values['varian_table']['attribute_length'] = len_value_ids
                # print("varian_table", res_values['varian_table'])
            if Model_id.attribute_line_ids:
                attribute_lines = []
                for att_ids in Model_id.attribute_line_ids.mapped('attribute_id'):
                    attr_data = self.mapping_field_post_one('product.attribute', att_ids.id)
                    # attr_data['create_variant'] = False
                    self.post_records('product.attribute', attr_data, True)
                    for att_value in att_ids.mapped('value_ids'):
                        val_data = self.mapping_field_post_one(
                            'product.attribute.value', att_value.id)
                        self.post_records(
                            'product.attribute.value', val_data, True)
                for att_ids in Model_id.attribute_line_ids:
                    attribute_lines.append({
                        'attribute_id': att_ids.attribute_id.izi_id,
                        'attribute_value_ids': att_ids.value_ids and att_ids.value_ids.mapped('izi_id')})
                if res_values.get('varian_table') and attribute_lines:
                    res_values['varian_table']['attribute_lines'] = attribute_lines
                # print("res_values:varian_table\n", res_values['varian_table'])
            if Model_id.product_wholesale_ids:
                for whsl_id in Model_id.product_wholesale_ids:
                    whsl_vals = whsl_id.read(
                        ['izi_id', 'min_qty', 'max_qty',
                         'price_wholesale'])[0]
                    if res_values.get('wholesale'):
                        res_values['wholesale'].append({
                            "id": whsl_vals.get('izi_id'),
                            "min_qty": whsl_vals.get('min_qty', 0),
                            "max_qty": whsl_vals.get('max_qty', 0),
                            "price_wholesale": whsl_vals.get('price_wholesale', 0),
                        })
                    else:
                        res_values['wholesale'] = [{
                            "id": whsl_vals.get('izi_id'),
                            "min_qty": whsl_vals.get('min_qty', 0),
                            "max_qty": whsl_vals.get('max_qty', 0),
                            "price_wholesale": whsl_vals.get('price_wholesale', 0),
                        }]
        return res_values

    def mapping_field_post_one(self, model_name, obj_id, field_list=[]):
        if not field_list:
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
                res_values[key] = img
            elif fld_type in ['many2many', 'one2many']:
                res_values.pop(key)
        if not self._context.get('no_loop'):
            res_values = self.custom_mapping_field_post(
                model_name, obj_id, res_values)
        res_values['obj_id'] = obj_id
        return res_values

    def custom_mapping_field_post(self, model_name, obj_id, res_values):
        if model_name == 'product.staging' and res_values.get('mp_type'):
            field_list = upload_fields.get(res_values.get('mp_type'), [])
            res = self.with_context({'no_loop': True}).mapping_field_post_one(
                model_name, obj_id, field_list=field_list)
            Model = self.env[model_name].sudo()
            Model_id = Model.browse(obj_id)
            images = []
            sp_attributes = []
            sp_logistics = []
            if res_values.get('mp_type') == 'Shopee':
                for img in Model_id.product_image_staging_ids:
                    if 'http' in img.name:
                        images.append({
                            'src': img.name,
                            'id': img.izi_id,
                            'name': img.name,
                        })
                    else:
                        images.append({
                            'src':img.image and img.image.decode('ascii'),
                        })
                for att in Model_id.sp_attributes:
                    sp_attributes.append({
                        "attr_id":att.attribute_id and att.attribute_id.izi_id,
                        "attr_value":att.attribute_value,
                    })
                for line in Model_id.sp_logistics:
                    sp_logistics.append({
                        "logistic_name": line.logistic_id and line.logistic_id.izi_id,
                        "estimated_shipping_fee": line.estimated_shipping_fee,
                        "is_free": line.is_free,
                        "is_active": line.enabled,
                    })
            if images:
                res_values['file_image'] = images
            if sp_attributes:
                res_values['sp_attributes'] = sp_attributes
            if sp_logistics:
                res_values['sp_logistics'] = sp_logistics
            res_values.update(res)
            res_values.pop('mp_type')
        return res_values

    #
    # Upload Manual
    #
    def upload_products(self, model_name, obj_id):
        if not model_name:
            return
        res_values = self.before_send_product(model_name, obj_id)
        is_success = (False, "Unknown error.")
        jsondata = self.mapping_field_post_one(model_name, obj_id)
        jsondata.update(res_values)
        is_success = self.post_records(model_name, jsondata, True)
        if is_success[0]:
            #### self._cr.commit()
            pass  ####
        return is_success

    def get_limit(self, day=1):
        # default last edited kemarin_dinihari
        return datetime.today() + delta(days=-day)

    def upload_to_izi(self, model_name='product.template'):
        # limit_date = self.get_limit()
        Model = self.env[model_name].sudo()
        domain = []
        if 'active' in Model._fields.keys():
            domain += [('active', 'in', [True, False])]
        Model_ids = Model.search(domain, order='write_date', limit=20)
        if model_name == 'product.template':
            for obj_id in Model_ids.ids:
                self.upload_products(model_name, obj_id)
        return True

    def upload_to_izi_one(self, model_name):
        # limit_date = self.get_limit()
        Model = self.env[model_name].sudo()
        domain = []
        if 'active' in Model._fields.keys():
            domain += [('active', 'in', [True, False])]
        Model_ids = Model.search(domain, order='write_date', limit=80)
        for obj_id in Model_ids.ids:
            data = self.mapping_field_post_one(model_name, obj_id)
            is_success = self.post_records(model_name, data, True)
            if is_success[0]:
                #### self._cr.commit()
                pass  ####
        return True

    def get_updated_izi_id(self, Model_id, data):
        flds = Model_id.fields_get([], ['name', 'type'])
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
                    #### self._cr.commit()
                elif error:
                    is_success = (False, "Pesan dari IZI : " + error)
        except Exception as e:
            _logger.warn(e)
            is_success = (False, e)
        return is_success

    def post_izi_records(self, model_name, jsondata, recheck_m2o_id=True):
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
            url = '{}/external/api/ui/update/{}/{}'.format(
                self.name, model_name, Model_id.izi_id)
            jsondata['record_was_exist'] = Model_id.izi_id
        else:
            url = '{}/external/api/ui/create/{}'.format(self.name, model_name)
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
                    #### self._cr.commit()
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
        records = self.search([], limit=1)
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
            (time.time() - start_time))
    
    def execute_action(self, model_name, model_id, method, push_self=True):
        is_success = (False, "Unknown error.")
        Model = self.env[model_name].sudo()
        if push_self:
            data = self.mapping_field_post_one(model_name, model_id)
            self.post_records(model_name, data, True)
            #### self._cr.commit()
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
                    error = response.get('error_descrip', '')
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
            webhook_server.with_context({'run_by_cron': True}).get_orders(domain_code='last_hour')

            
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
                        #### self._cr.commit()
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
                    #### self._cr.commit()
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


class WebhookServerLog(models.Model):
    _name = 'webhook.server.log'
    _order = 'id desc'

    name = fields.Char('Name')
    server_id = fields.Many2one('webhook.server', string='Server')
    model_name = fields.Char('Model Name')
    izi_id = fields.Integer('IZI ID')
    status = fields.Selection([
        ('failed', 'Failed'),
        ('success', 'Success'),
    ], default='failed')
    res_id = fields.Integer('Record ID')
    notes = fields.Char('Notes')
    error_message = fields.Text('Error Message')
    last_retry_time = fields.Datetime('Last Retry')

    def retry_get_record(self):
        for log in self:
            if log.status == 'failed':
                domain_url = "[('id', '=', %i)]" % int(log.izi_id)
                log.server_id.get_records(log.model_name, domain_url=domain_url)
