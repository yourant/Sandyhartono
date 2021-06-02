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
    'mp.shopee.item.attribute.option': 'izi-shopee-item-attribute-option',
    'mp.shopee.item.attribute.val': 'izi-shopee-item-attribute-val',
    'mp.shopee.logistic': 'izi-shopee-logistic',
    'mp.shopee.logistic.size': 'izi-shopee-logistic-size',
    'mp.shopee.shop.logistic': 'izi-shopee-shop-logistic',
    'mp.shopee.item.logistic': 'izi-shopee-item-logistic',

    'mp.shopee.item.var.attribute': 'izi-shopee-item-var-attribute',
    'mp.shopee.item.var.attribute.value': 'izi-shopee-item-var-attribute-value',
    'mp.shopee.attribute.line' : 'izi-shopee-item-attribute-line',

    'mp.lazada': 'izi-lazada',
    'mp.lazada.brand': 'izi-lazada-brand',
    'mp.lazada.category': 'izi-lazada-category',
    'mp.lazada.category.attr': 'izi-lazada-category-attr',
    'mp.lazada.category.attr.opt': 'izi-lazada-category-attr-opt',
    'mp.lazada.product.attr': 'izi-lazada-product-attr',

    'mp.lazada.variant.value': 'izi-lazada-variant-value',
    'mp.lazada.attribute.line': 'izi-lazada-attribute-line',

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
    'stock.warehouse': ['code'],
    'res.company': ['name'],
    'res.users': ['name'],
    'mp.shopee.item.attribute.option': ['name'],
    'mp.lazada.category.attr.opt': ['name'],
}

removed_fields = {
    'product.product': ['uom_id', 'company_id', 'barcode'],
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
        'id','attribute_int','attribute_id','attribute_value','item_id_staging'
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
                    if not isinstance(v, str):
                        vals2[k] = '%s' % (v)
        else:
            vals2 = vals
        res = super(Base, self).create(vals2)
        if vals2 and self._context.get('webhook', True):
            res.create_webhook(fields=list(vals2.keys()))
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
    is_sync = fields.Boolean(default=True)
    is_skip_check = fields.Boolean(default=False)

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
        try:
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
        except Exception as e:
            _logger.error(str(e))
            return False

    def retry_login(self, count_retry):
        for i in range(count_retry):
            session_id = self.auth_login()
            if session_id:
                return session_id
            else:
                time.sleep(1)
        raise UserError('Please Login Manually.')
        return False
    
    def _get_session(self):
        for server in self:
            session_id = False
            for i in range(10):
                session_id = server.auth_login()
                if session_id:
                    break
                else:
                    time.sleep(1)
            if not session_id:
                raise UserError(
                    'Cannot access IZI server, please try again later')

    
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
        self.env.cr.execute('DELETE FROM mp_tokopedia;DELETE FROM mp_shopee;DELETE FROM product_mapping;DELETE FROM stock_change_product_qty;')
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
        self.get_warehouses()
        self.get_records('res.partner')
        self.get_records('mp.tokopedia', domain_code='all_active')
        self.get_records('mp.shopee', domain_code='all_active')
        self.get_records('mp.lazada', domain_code='all_active')

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
        
    def remote_rsa(self):
        if self.ensure_one():
            try:
                from Cryptodome.Cipher import PKCS1_OAEP
                from Cryptodome.PublicKey import RSA as rsa_key
                from base64 import urlsafe_b64encode
                
                r = requests.get('%s/rsa/pem/public' % (self.name))
                if r.status_code == 200:
                    message = '%s:%s' % (self.username, self.password)
                    rsa_public_key = rsa_key.import_key(r.text)
                    cipher = PKCS1_OAEP.new(key=rsa_public_key)
                    access_token = urlsafe_b64encode(cipher.encrypt(message.encode())).decode('utf-8')
                    return {                   
                        'name': 'Go to website',
                        'res_model': 'ir.actions.act_url',
                        'type': 'ir.actions.act_url',
                        'target': 'new',
                        'url': '%s/web/login/rsa/%s?db=%s' % (self.name, access_token, self.name.split('//')[1]),
                    }
                else:
                    raise UserError('Cannot get public key.')
            except ImportError:
                raise UserError('Cannot import Cryptodome.')
        
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
        self.get_orders(domain_code='last_hour')

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
        self.get_records('mp.shop.address')
        self.get_records('sale.order.cancel.reason')
    
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
        self.trigger_import_stock_izi()
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
                    raise UserError('Product with izi_id %s not found.' % str(prod_id))
                if products_by_izi_id[prod_id].type != 'product':
                    continue
                for prod_wh_code in data['res_warehouse_codes']:
                    if prod_wh_code not in warehouses_by_code:
                        raise UserError('Warehouse with code %s not found.' % str(prod_wh_code))
                    line_vals.append(
                        (0, 0, {
                            'product_id': products_by_izi_id[prod_id].id,
                            'location_id': warehouses_by_code[prod_wh_code].lot_stock_id.id,
                            'product_qty': prod[prod_wh_code]['qty_total'] + prod[prod_wh_code]['qty_draft'],
                        })
                    )
            res = self.env['stock.inventory'].sudo().create({
                'name': 'Import Stock Data From IZI',
                # 'location_id': lot_stock_id,
                # 'filter': 'none',
                'line_ids': line_vals,
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

    #
    # Method Generic for API
    #
    def get_records(self, model_name, force_update=False, offset=0, limit=100, order_field='id', sort='asc', retry_login=True, retry_login_count=3, domain_code=False, domain_url=False):
        i = 0
        while True:
            code = code_by_model_name[model_name] if model_name in code_by_model_name else model_name
            url = self.name + '/api/ui/read/list-detail/%s?offset=%s&limit=%s&order=%s&sort=%s&domain_code=%s' % (
                code, str(offset), str(limit), order_field, sort, domain_code)
            if domain_url:
                url = self.name + '/api/ui/read/list-detail/%s/%s?offset=%s&limit=%s&order=%s&sort=%s&domain_code=%s' % (
                    code, domain_url, str(offset), str(limit), order_field, sort, domain_code)
            r = requests.get(url, headers={'X-Openerp-Session-Id': self.session_id})
            res = r.json() if r.status_code == 200 else {}
            if res.get('code') == 200:
                get_number = offset if res['meta']['total_item'] > offset else res['meta']['total_item']
                if get_number:
                    self.env.user.notify_info('Get Records from IZI App and Marketplace: %s (%s)' % (
                        model_name.replace('.', ' ').title(), get_number))
                if len(res.get('data')) == 0:
                    break
                else:
                    offset += limit
                for res_values in res.get('data'):
                    i += 1
                    _logger.info('(%s) Get record %s ID %s' % (i, model_name, res_values.get('id')))
                    record = self.get_existing_record(
                        model_name, res_values)
                    if record:
                        if 'izi_md5' in self.env[model_name]._fields:
                            is_update = False
                            izi_md5 = hashlib.md5(json.dumps(
                                res_values).encode('utf-8')).hexdigest()
                            if force_update:
                                is_update = True
                            else:
                                if record.izi_md5 != izi_md5:
                                    is_update = True
                            if is_update:
                                values = self.mapping_field(
                                    model_name, res_values, update=True)
                                values.update({
                                    'izi_md5': izi_md5
                                })
                                values = self.custom_before_write(
                                    model_name, values)
                                record.write(values)
                                self.custom_after_write(model_name, record, values)
                        else:
                            values = self.mapping_field(
                                model_name, res_values, update=True)
                            values = self.custom_before_write(
                                model_name, values)
                            record.write(values)
                            self.custom_after_write(model_name, record, values)
                    else:
                        values = self.mapping_field(
                            model_name, res_values, update=False)
                        values = self.custom_before_create(model_name, values)
                        record = self.env[model_name].create(values)
                        self.custom_after_create(model_name, record, values)
                    self.env.cr.commit()
            elif res.get('code') == 401:
                if retry_login:
                    self.retry_login(retry_login_count)
                    self.get_records(model_name, offset, limit,
                                     order_field, sort, retry_login=False)
                else:
                    break
            else:
                break

    def custom_after_write(self, model_name, record, values):
        if model_name == 'sale.order':
            # Action
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

    def custom_before_write(self, model_name, values):
        res = values.copy()
        if model_name == 'sale.order':
            # Sale Order only update order_status and resi
            res = {
                'order_status': res['order_status'],
                'order_status_notes': res['order_status_notes'],
                'mp_awb_number': res['mp_awb_number'],
                'mp_delivery_carrier_name': res['mp_delivery_carrier_name'],               
                'mp_awb_url': res['mp_awb_url'],               
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

        elif model_name == 'product.template':
            if 'name' in res:
                del res['name']
            if 'default_code' in res:
                del res['default_code']
            res['invoice_policy'] = 'order'
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
            # Replace Values
            res['partner_id'] = partner.id
            res['partner_shipping_id'] = shipping_address.id
        elif model_name == 'product.template':
            res['invoice_policy'] = 'order'
        return res

    def custom_after_create(self, model_name, record, values):
        if model_name == 'sale.order':
            # Action
            record.with_context(no_push=True).action_by_order_status()
            # Notify
            if self.env.user:
                self.env.user.notify_info('New Order from Marketplace %s, with total amount %s. Delivery to %s.' % (record.mp_invoice_number, record.amount_total, record.mp_recipient_address_city))

    def get_existing_record_from_mapping(self, record, model_name, values):
        res = record
        if model_name == 'product.template':
            mapping = self.env['product.mapping'].sudo().search([('product_template_izi_id', '=', values['id'])], limit=1)
            if mapping and mapping.product_id and mapping.product_id.product_tmpl_id:
                res = mapping.product_id.product_tmpl_id
                res.izi_id = values['id']
                print('Product Template Mapping %s' % mapping.product_id.product_tmpl_id.name)
        if model_name == 'product.product':
            mapping = self.env['product.mapping'].sudo().search([('product_product_izi_id', '=', values['id'])], limit=1)
            if mapping and mapping.product_id:
                res = mapping.product_id
                res.izi_id = values['id']
                print('Product Variant Mapping %s' % mapping.product_id.name)
        if model_name == 'stock.warehouse':
            mapping = self.env['warehouse.mapping'].sudo().search([('warehouse_izi_id', '=', values['id'])], limit=1)
            if mapping and mapping.warehouse_id:
                res = mapping.warehouse_id
                res.izi_id = values['id']
                print('Warehouse Mapping %s' % mapping.warehouse_id.name)
        if model_name == 'stock.location':
            mapping = self.env['location.mapping'].sudo().search([('location_izi_id', '=', values['id'])], limit=1)
            if mapping and mapping.location_id:
                res = mapping.location_id
                res.izi_id = values['id']
                print('Location Mapping %s' % mapping.location_id.display_name)
        return res

    def get_existing_record(self, model_name, values, mandatory=False):
        if 'id' not in values:
            raise UserError('Field id not found in the values.')
        Model = self.env[model_name].sudo()

        if 'active' in Model._fields:
            domain = [('izi_id', '=', values['id']), '|', ('active', '=', True), ('active', '=', False)]
        else:
            domain = [('izi_id', '=', values['id'])]
        if model_name in existing_fields_by_model_name and existing_fields_by_model_name[model_name]:
            for field_name in existing_fields_by_model_name[model_name]:
                if field_name in values and values[field_name]:
                    domain = ['|'] + domain + [(field_name, '=', values[field_name])]

        record = Model.search(domain, limit=1)
        # Mapping
        record = self.get_existing_record_from_mapping(record, model_name, values)

        if not record:
            if mandatory and not self.is_skip_check:
                raise UserError('Record not found model_name: %s, izi_id: %s. Import First.' % (model_name, values['id']))
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
                elif isinstance(Model._fields[key], fields.Many2one) and values[key] and 'id' in values[key]:
                    comodel_name = Model._fields[key].comodel_name
                    if comodel_name == model_name:
                        # If it has relation to itself, skipped, handle manually in custom_mapping_field
                        if model_name not in processed_model_with_many2one_itself:
                            continue
                    record = self.get_existing_record(comodel_name, values[key], mandatory=True)
                    if record:
                        res_values[key] = record.id
                elif isinstance(Model._fields[key], fields.Binary):
                    img = False
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
                        if key == 'image':
                            if model_name in ['product.template', 'product.staging', 'product.product', 'product.staging.variant']:
                                if values.get('image_url_external') and isinstance(values.get('image_url_external'), str) and ('http://' in values.get('image_url_external') or 'https://' in values.get('image_url_external')) and values.get('image_url_external') != None and values.get('image_url_external') != False:
                                    img = b64encode(requests.get(
                                        values.get('image_url_external')).content)
                            elif model_name in ['product.image', 'product.image.staging']:
                                if values.get('url_external') and isinstance(values.get('url_external'), str) and ('http://' in values.get('url_external') or 'https://' in values.get('url_external')) and values.get('url_external') != None and values.get('url_external') != False:
                                    img = b64encode(requests.get(
                                        values.get('url_external')).content)
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
        elif model_name == 'mp.tokopedia':
            res_values['active'] = True
            res_values['server_id'] = self.id
        elif model_name == 'mp.shopee':
            res_values['active'] = True
            res_values['server_id'] = self.id
        elif model_name == 'mp.lazada':
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

    def get_warehouses(self):
        url = self.name + '/api/ui/read/list-detail/%s?offset=%s&limit=%s&order=%s&sort=%s&domain_code=%s' % (
            'stock.warehouse', 0, 1000, 'id', 'asc', 'marketplace')
        r = requests.get(url, headers={'X-Openerp-Session-Id': self.session_id})
        res = r.json() if r.status_code == 200 else {}
        if res.get('code') == 200:
            for res_values in res.get('data'):
                wh = self.get_existing_record('stock.warehouse', res_values)
                if not wh:
                    wh = self.env['stock.warehouse'].sudo().create({
                        'name': res_values.get('name'),
                        'code': res_values.get('code'),
                        'izi_id': res_values.get('id')
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
            self._cr.commit()
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
                self._cr.commit()
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
                    self._cr.commit()
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
            ('active', 'in', [False, True]), ],
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
            (time.time() - start_time))
    
    def execute_action(self, model_name, model_id, method, push_self=True):
        is_success = (False, "Unknown error.")
        Model = self.env[model_name].sudo()
        if push_self:
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
