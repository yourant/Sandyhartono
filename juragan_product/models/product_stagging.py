from lxml import etree
from odoo import models, fields, api, tools, _
from odoo.addons import decimal_precision as dp
from odoo.addons.juragan_webhook import BigInteger, BigMany2one
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError
import requests

import logging

_logger = logging.getLogger(__name__)


class ProductStaging(models.Model):
    _name = 'product.staging'
    _description = 'Product Stagging'
    __marketplace_upload_for__ = {
        'Tokopedia': 'tp_export_product',
        'Shopee': 'sp_export_product',
        'Lazada': None,
    }

    @api.model
    def default_get(self, default_fields):
        res = super().default_get(default_fields)
        mp_type = False
        if res.get('mp_tokopedia_id'):
            mp_type = 'Tokopedia'
        elif res.get('mp_shopee_id'):
            mp_type = 'Shopee'
        if not res.get('mp_type'):
            res['mp_type'] = mp_type
        if not res.get('product_template_id'):
            res['product_template_id'] = self._context.get('default_tmpl_id')
        return res

    product_template_id = fields.Many2one(
        'product.template', 'Product Template')
    name = fields.Char('Name', index=True, translate=True)
    description_sale = fields.Text(
        'Sale Description', translate=True,
        help="A description of the Product that you want to communicate \
        to your customers. This description will be copied to every Sales \
        Order, Delivery Order and Customer Invoice/Credit Note")
    brand_id = fields.Many2one('product.brand', string='Merek')
    list_price = fields.Float(
        'Sales Price', default=1.0,
        digits=dp.get_precision('Product Price'),
        help="Base price to compute the customer price. \
        Sometimes called the catalog price.")
    # volume = fields.Float(
    #     'Volume',
    #     help="The volume in m3.", store=True)
    weight = fields.Float(
        'Weight', digits=dp.get_precision('Stock Weight'), store=True,
        help="The weight of the contents in Kg, not including any \
        packaging, etc.")
    length = fields.Float('Length')
    width = fields.Float('Width')
    height = fields.Float('Height')
    barcode = fields.Char('Barcode')
    default_code = fields.Char(
        'Internal Reference', store=True)
    active = fields.Boolean(
        'Active', default=True,
        help="If unchecked, it will allow you to hide the product \
        without removing it.")
    # item_ids = fields.One2many(
    #     'product.pricelist.item', 'product_tmpl_id', 'Pricelist Items')
    # product_variant_id
    product_variant_stg_ids = fields.One2many(
        'product.staging.variant', 'product_stg_id',
        'Product Variant Staging',
        domain=['|', ('active', '=', False), ('active', '=', True), ],
        context={'active_test': False})
    product_image_staging_ids = fields.One2many(
        'product.image.staging', 'product_stg_id')

    is_uploaded = fields.Boolean('Is Uploaded')
    is_active = fields.Boolean('Is Active')
    qty_available = fields.Integer('Qty Available', readonly=True, compute='_get_qty_available')
    product_uom_id = fields.Many2one('uom.uom', 'Unit of Measure')
    min_order = fields.Integer('Min Order')
    package_content = fields.Text('Isi Paket')
    latest_upload_status = fields.Selection(
        [('1', 'DONE'), ('2', 'FAILED')])

    mp_type = fields.Selection([
        ('Tokopedia', 'Tokopedia'),
        ('Shopee', 'Shopee'),
        ('Lazada', 'Lazada'),
    ], 'Marketplace', )
    mp_external_id = BigInteger()

    mp_tokopedia_id = fields.Many2one(
        'mp.tokopedia', string='Tokopedia ID',
        domain=['|', ('active', '=', False), ('active', '=', True), ],
        context={'active_test': False})
    tp_available_status = fields.Selection([
        ('1', 'EMPTY'),
        ('2', 'LIMITED'),
        ('3', 'UNLIMITED')
    ], string='Product Availability Status')
    tp_active_status = fields.Selection([
        ('-2', 'Banned'),
        ('-1', 'Pending'),
        ('0', 'Deleted'),
        ('1', 'Active'),
        ('2', 'Best (Featured Product)'),
        ('3', 'Inactive (Warehouse)')
    ], string='Product Active Status')
    tp_condition = fields.Selection([
        ('1', 'NEW'),
        ('2', 'USED')
    ], string="Condition")
    tp_weight_unit = fields.Selection([
        ('1', 'Gr'),
        ('2', 'KG')
    ], string='Weight Unit')
    tp_category_id = fields.Many2one(
        'mp.tokopedia.category', string='Product Category')
    tp_etalase_id = fields.Many2one(
        'mp.tokopedia.etalase', string='Product Etalase', )
    tp_latest_upload_id = fields.Integer('Latest Upload ID')
    tp_attribute_line_ids = fields.One2many(
        'mp.tokopedia.attribute.line', 'product_staging_id', 'Product Attributes Variations')
    tp_etalase_name = fields.Char(string='Etalase Name')

    mp_shopee_id = fields.Many2one('mp.shopee', string='Shopee ID')
    sp_condition = fields.Selection(
        [('NEW', 'NEW'), ('USED', 'USED')], 'Condition')
    sp_status = fields.Selection(
        [('NORMAL', 'NORMAL'), ('UNLIST', 'UNLIST')], 'Status Produk', compute='_set_sp_status')
    sp_is_pre_order = fields.Boolean('Pre Order')
    sp_days_to_ship = fields.Integer(default=2)


    sp_category_id = BigMany2one('mp.shopee.item.category',string='Shopee Category', domain=[('has_children', '=', False)])
    sp_category_int = BigInteger()
    sp_logistics = fields.One2many(
        'mp.shopee.item.logistic', 'item_id_staging')
    sp_attributes = fields.One2many(
        'mp.shopee.item.attribute.val', 'item_id_staging')

    sp_attribute_line_ids = fields.One2many('mp.shopee.attribute.line', 'product_staging_id', 'Product Attributes Variations')

    # attributes = fields.One2many('mp.shopee.item.wizard.item.attr', 'item_staging_id')

    # mp_lazada_product_id = fields.Many2one(
    #     'mp.lazada.product', string='Lazada Product')
    mp_lazada_id = fields.Many2one('mp.lazada', string='Lazada ID')

    product_wholesale_ids = fields.One2many(
        'product.staging.wholesale', 'product_stg_id')

    product_variant_ids = fields.Many2many('product.product')

    izi_id = fields.Integer('Izi ID')
    izi_md5 = fields.Char()

    def get_webhook_server(self):
        server = self.env['webhook.server'].search([], limit=1)
        if not server:
            raise UserError('There is no webhook server.')
        return server

    @api.onchange('sp_is_pre_order')
    def set_sp_dtp(self):
        ## Validasi Karakter pada field 'name'
        if self.sp_is_pre_order:
            self.sp_days_to_ship = 7
        else:
            self.sp_days_to_ship = 2

    def mp_upload(self):
        self.ensure_one()
        p_method = self.__marketplace_upload_for__.get(self.mp_type)
        server = self.env['webhook.server'].search(
            [('active', 'in', [False, True])],
            limit=1, order='write_date desc')
        if not server:
            raise
        # if self.product_template_id:
        #     self.product_template_id.upload_self()
        #     server.upload_products(
        #         'product.template', self.product_template_id.id)
        uploaded = server.execute_action(
            self._name, self.id, p_method, push_self=True)
        if uploaded[0]:
            msg = _("Upload to %s" % self.mp_type)
        else:
            msg = _("Fail to upload to %s : %s" % (self.mp_type, uploaded[1]))
            raise ValidationError(msg)
        self.product_template_id.message_post(
            body=uploaded[1], subject=msg)

    def action_toggle_mp(self):
        ctx = self._context
        pd_tmpl = self.product_template_id
        tp = False
        sh = False
        lz = False
        self.active = True
        mp_id = ctx.get('mp_int_id', False)
        if ctx.get('mp_tipe') == 'Tokopedia':
            tp = mp_id
            pd_tmpl.mp_tokopedia_ids = [(4, tp)]
        if ctx.get('mp_tipe') == 'Shopee':
            sh = mp_id
            pd_tmpl.mp_shopee_ids = [(4, sh)]
        if ctx.get('mp_tipe') == 'Lazada':
            lz = mp_id
            pd_tmpl.mp_lazada_ids = [(4, lz)]
        if self.list_price <= 0:
            self.list_price = ctx.get('default_list_price', 1)
        self.mp_type = ctx.get('mp_tipe')
        self.mp_tokopedia_id = tp
        self.mp_shopee_id = sh
        self.mp_lazada_id = lz
        
        # mapping pd template field to pd staging
        self.default_code = pd_tmpl.default_code
        self.barcode = pd_tmpl.barcode
        self.description_sale = pd_tmpl.description_sale
        self.list_price = pd_tmpl.list_price

        # mapping shopee logistic
        if not self.sp_logistics:
            logistic_shop = self.env['mp.shopee.shop.logistic'].search([('mp_id','=',sh),('enabled','=',True)])
            self.sp_logistics = [(5, 0, 0), *[(0, 0, {
                        'logistic_id': logistic.logistic_id.id
                    }) for logistic in logistic_shop]]
        if self.mp_type:
            msg = {
                "message": "Sukses membuat produk %s" % self.mp_type,
                "title": "Produk Staging", "sticky": False}
            self.env.user.notify_success(**msg)
            return True

    def _get_qty_available(self):
        for rec in self:
            lot_stock_id = False
            product_id = False
            if rec.mp_tokopedia_id:
                lot_stock_id = rec.mp_tokopedia_id.wh_id.lot_stock_id.id
            elif rec.mp_shopee_id:
                lot_stock_id = rec.mp_shopee_id.wh_id.lot_stock_id.id
            if rec.product_template_id and rec.product_template_id.product_variant_ids:
                product_id = rec.product_template_id.product_variant_ids[0].id
            if lot_stock_id and product_id:
                quants = self.env['stock.quant'].search(
                    [('product_id', '=', product_id),
                     ('location_id', '=', lot_stock_id)])
                rec.qty_available = sum(
                    q['quantity'] - q['reserved_quantity'] for q in quants)
                # rec.product_uom_id = quants and quants[0].product_uom_id
            else:
                rec.qty_available = 0
                # rec.product_uom_id = False

    # @api.onchange('product_template_id', 'mp_type')
    # def onchange_product_template_id(self):
    #     mp_tp = [('id', 'in', self.product_template_id and self.product_template_id.mp_tokopedia_ids.ids or []), ]
    #     mp_sh = [('id', 'in', self.product_template_id and self.product_template_id.mp_shopee_ids.ids or []), ]
    #     return {'domain': {
    #         'mp_tokopedia_id': mp_tp,
    #         'mp_shopee_id': mp_sh,
    #     }}

    @api.onchange('sp_category_id')
    def _change_category_id(self):
        if self.mp_shopee_id and self.sp_category_id:
            try:
                mp_id_by_izi_id = self.mp_shopee_id.izi_id
                category_id = self.sp_category_id.izi_id
                server = self.get_webhook_server()
                if server:
                    if not self.sp_category_id.attributes:
                        res = server.get_attribute_category(category_id,mp_id_by_izi_id)
                # self.mp_ids[0].get_item_category(category_ids=self.category_id.ids)
                self.sp_attributes = [(5, 0, 0), *[(0, 0, {
                    'attribute_id': attribute.id
                }) for attribute in self.sp_category_id.attributes]]
            except Exception as e:
                _logger.warn(e)
           
    def _set_sp_status(self):
        for rec in self:
            if rec.is_active:
                rec.sp_status = 'NORMAL'
            else:
                rec.sp_status = 'UNLIST'

    @api.model
    def fields_view_get(
            self, view_id=None, view_type='form',
            toolbar=False, submenu=False):
        def get_view_id(xid, name):
            try:
                return self.env.ref('juragan_product.' + xid)
            except ValueError:
                view = self.env['ir.ui.view'].search(
                    [('name', '=', name)], limit=1)
                if not view:
                    return False
                return view.id

        def mp_name_get(mp_id):
            mp_int_id, mp_name = mp.name_get()[0]
            if len(mp_name) > 33:
                mp_name = mp_name[:30] + '...'
            return {
                'mp_int_id': mp_int_id,
                'mp_name': mp_name,
                'mp_tipe': mp_id._name.replace('mp.', '').title()}

        res = super(ProductStaging, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar,
            submenu=submenu)
        context = self._context
        mdl = context.get('active_model', 'product.staging')
        tmpl_id = context.get('default_tmpl_id', 0)
        if (mdl == 'product.staging') and (view_type == 'form'):
            doc = etree.fromstring(res['arch'])
            divbox = doc.xpath("//group[@name='mp_button_box']")
            if not divbox:
                return res
            if not tmpl_id:
                divbox[0].append(etree.fromstring(
                    "<p><strong>Please save this product to create marketplace product.<br/>Press button 'discard' bellow...</strong></p>"))
                res['arch'] = etree.tostring(doc, encoding='unicode')
                return res
            mp_button_xml = """<button type="object" name="action_toggle_mp" class="btn-bg btn-info" context="{'mp_int_id': %(mp_int_id)d,'mp_tipe': '%(mp_tipe)s'}"><strong>%(mp_tipe)s</strong><p>%(mp_name)s</p></button>"""
            mp_list = []
            mp_tokopedia_ids = self.env['mp.tokopedia'].with_context(
                active_test=True).search([])
            mp_shopee_ids = self.env['mp.shopee'].with_context(
                active_test=True).search([])
            mp_lazada_ids = self.env['mp.lazada'].with_context(
                active_test=True).search([])
            for mp in mp_tokopedia_ids:
                mp_list.append(mp_name_get(mp))
            for mp in mp_shopee_ids:
                mp_list.append(mp_name_get(mp))
            for mp in mp_lazada_ids:
                mp_list.append(mp_name_get(mp))
            for mpl in mp_list:
                btn_xml = mp_button_xml % mpl
                xb = etree.fromstring(btn_xml)
                divbox[0].append(xb)
            res['arch'] = etree.tostring(doc, encoding='unicode')
        return res

    def _do_upload_product_stg_izi(self, generate_variant=False, do_export=False):
        response_fields_from_izi = [
            'product_image_staging_ids', 'product_wholesale_ids', 'product_variant_ids', 'tp_attribute_line_ids', 'product_variant_stg_ids']
        for product_stg_id in self:
            server = self.env['webhook.server'].search(
                [('active', 'in', [False, True])],
                limit=1, order='write_date desc')
            if not server:
                raise UserError('Buatkan minimal 1 webhook server!')
            if product_stg_id.product_template_id.izi_id == 0 or not product_stg_id.product_template_id.izi_id or product_stg_id.product_template_id.izi_id == None:
                product_stg_id.product_template_id.upload_product_tmpl_izi()
            json_data = {
                "id": product_stg_id.id,
                'product_template_id': product_stg_id.product_template_id.izi_id,
                "name": product_stg_id.name,
                "description_sale": product_stg_id.description_sale,
                "default_code": product_stg_id.default_code,
                "barcode": product_stg_id.barcode,
                "min_order": product_stg_id.min_order,
                "list_price": product_stg_id.list_price,
                "weight": product_stg_id.weight,
                "length": product_stg_id.length,
                "height": product_stg_id.height,
                "width": product_stg_id.width,
                "package_content": product_stg_id.package_content,
                "qty_available": product_stg_id.qty_available,
                "mp_external_id": product_stg_id.mp_external_id,
                "is_active": product_stg_id.is_active,

                # tokopedia
                "mp_tokopedia_id": product_stg_id.mp_tokopedia_id.izi_id,
                "tp_category_id": product_stg_id.tp_category_id.izi_id,
                "tp_etalase_name": product_stg_id.tp_etalase_name,
                "tp_etalase_id": product_stg_id.tp_etalase_id.izi_id,
                "tp_condition": product_stg_id.tp_condition,
                "tp_available_status": product_stg_id.tp_available_status,
                "tp_weight_unit": product_stg_id.tp_weight_unit,

                # shopee
                "mp_shopee_id": product_stg_id.mp_shopee_id.izi_id,
                "sp_is_pre_order": product_stg_id.sp_is_pre_order,
                "sp_category_int": product_stg_id.sp_category_id.izi_id,
                "sp_days_to_ship": product_stg_id.sp_days_to_ship,
                "sp_condition": product_stg_id.sp_condition,
                "sp_status": product_stg_id.sp_status
            }

            images = []
            for image in product_stg_id.product_image_staging_ids:
                images.append({
                    'src': 'data:image;base64,' + image.image.decode('utf-8') if image.image else image.url,
                    'name': image.name,
                    'url_external': image.url_external,
                    'id': image.izi_id
                })
            json_data.update({
                'file_image': images
            })

            wholesales = []
            for wholesale in product_stg_id.product_wholesale_ids:
                wholesales.append({
                    'id': wholesale.izi_id,
                    'min_qty': wholesale.min_qty,
                    'max_qty': wholesale.max_qty,
                    'price_wholesale': wholesale.price_wholesale,
                })
            json_data.update({
                'wholesale': wholesales
            })

            variant_table = False
            attribute_lines = False
            if generate_variant:
                if product_stg_id.tp_attribute_line_ids and product_stg_id.mp_tokopedia_id:
                    variant_table = {}
                    attribute_lines = []
                    for tp_attribute_line in product_stg_id.tp_attribute_line_ids:
                        attribute_data = {
                            'id': tp_attribute_line.izi_id,
                            'product_staging_id': tp_attribute_line.product_staging_id.izi_id,
                            'tp_variant_id': tp_attribute_line.tp_variant_id.izi_id,
                            'tp_variant_unit_id': tp_attribute_line.tp_variant_unit_id.izi_id,
                        }
                        values = []
                        for tp_value in tp_attribute_line.tp_variant_value_ids:
                            values.append(tp_value.izi_id)
                        attribute_data.update({
                            'tp_variant_value_ids': values
                        })
                        attribute_lines.append(attribute_data)
                    variant_table.update({
                        'tp_attribute_line_ids': attribute_lines
                    })

                elif product_stg_id.sp_attribute_line_ids and product_stg_id.mp_shopee_id:
                    variant_table = {}
                    attribute_lines = []
                    for sp_attribute_line in product_stg_id.sp_attribute_line_ids:
                        if sp_attribute_line.izi_id != 0 and sp_attribute_line.attribute_id.izi_id != 0:
                            attribute_data = {
                                'id': sp_attribute_line.izi_id,
                                'product_staging_id': sp_attribute_line.product_staging_id.izi_id,
                                'attribute_id': sp_attribute_line.attribute_id.izi_id,
                            }
                            values = []
                            for sp_value in sp_attribute_line.value_ids:
                                values.append(sp_value.izi_id)
                            attribute_data.update({
                                'value_ids': values
                            })
                            attribute_lines.append(attribute_data)
                    variant_table.update({
                        'sp_attribute_line_ids': attribute_lines
                    })

            if variant_table and attribute_lines and product_stg_id.product_variant_stg_ids:
                if not variant_table:
                    variant_table = {}
                variant_ids = []
                for variant_staging in product_stg_id.product_variant_stg_ids:
                    variant_data = {
                        'id': variant_staging.izi_id,
                        'barcode': variant_staging.barcode,
                        'default_code': variant_staging.default_code,
                        'image': variant_staging.image.decode('utf-8') if variant_staging.image else False,
                        'image_url': variant_staging.image_url,
                        'image_url_external': variant_staging.image_url_external,
                        'is_active': variant_staging.is_active,
                        'is_uploaded': variant_staging.is_uploaded,
                        'name': variant_staging.name,
                        'price_custom': variant_staging.price_custom,
                        'mp_external_id': variant_staging.mp_external_id,
                        'product_id': variant_staging.product_id.izi_id,
                        'product_stg_id': variant_staging.product_stg_id.izi_id,
                        'qty_available': variant_staging.qty_available,
                        'sp_update_time_unix': variant_staging.qty_available,
                        'sp_variant_id': variant_staging.sp_variant_id,
                        'sp_variant_name': variant_staging.sp_variant_name,
                        'sp_variant_status': variant_staging.sp_variant_status,
                    }
                    tp_values = []
                    for tp_value in variant_staging.tp_variant_value_ids:
                        tp_values.append(tp_value.izi_id)
                    variant_data.update({
                        'tp_variant_value_ids': tp_values
                    })
                    sp_values = []
                    for sp_value in variant_staging.sp_attribute_value_ids:
                        sp_values.append(sp_value.izi_id)
                    variant_data.update({
                        'sp_attribute_value_ids': sp_values
                    })
                    variant_ids.append(variant_data)
                variant_table.update({
                    'varian_list': variant_ids
                })

            json_data.update({
                'varian_table': variant_table
            })

            sp_attributes = []
            for attr in product_stg_id.sp_attributes:
                attr_value = False
                if attr.attribute_id.input_type == 'TEXT_FILED':
                    attr_value = attr.attribute_value
                else:
                    attr_value = self.env['mp.shopee.item.attribute.option'].search(
                        [('name', '=', attr.attribute_value)], limit=1).izi_id
                sp_attributes.append({
                    'attr_id': attr.attribute_id.izi_id,
                    'attr_value': attr_value,
                })
            json_data.update({
                'sp_attributes': sp_attributes
            })

            sp_logistics = []
            for line in product_stg_id.sp_logistics:
                sp_logistics.append({
                    "logistic_name": line.logistic_id and line.logistic_id.izi_id,
                    "estimated_shipping_fee": line.estimated_shipping_fee,
                    "is_free": line.is_free,
                    "is_active": line.enabled,
                })
            json_data.update({
                'sp_logistics': sp_logistics
            })

            jsondata = server.get_updated_izi_id(product_stg_id, json_data)

            if product_stg_id.izi_id:
                url = '{}/external/api/ui/update/product.staging/{}'.format(
                    server.name, product_stg_id.izi_id)
                jsondata['record_was_exist'] = product_stg_id.izi_id
            else:
                url = '{}/external/api/ui/create/product.staging'.format(
                    server.name)
            try:
                req = requests.post(
                    url,
                    headers={'X-Openerp-Session-Id': server.session_id},
                    json=json_data)
                if req.status_code == 200:
                    response = req.json()
                    if response.get('code') == 200:

                        def process_response_data(product_stg_id, response_data, response_key, server):
                            existing_data_ids = product_stg_id[response_key]
                            response_data_ids = response_data.get(response_key)
                            if len(response_data.get(response_key)) > 0:
                                domain_url = "[('id', 'in', %s)]" % str(
                                    response_data.get(response_key))
                                server.get_records(
                                    product_stg_id[response_key]._name, domain_url=domain_url, force_update=True)
                            for model_data_response in existing_data_ids:
                                if model_data_response.izi_id not in response_data_ids:
                                    if model_data_response._fields.get('active') != None:
                                        if not model_data_response._fields.get('active').related:
                                            model_data_response.active = False
                                        else:
                                            model_data_response.unlink()
                                    else:
                                        model_data_response.unlink()
                            self.env.cr.commit()

                        response_data = response.get('data')
                        product_stg_id.izi_id = response_data.get('id')

                        for response_field in response_fields_from_izi:
                            if response_field in response_data:
                                process_response_data(product_stg_id=product_stg_id, response_data=response_data, response_key=response_field, server=server)
                        
                        if generate_variant:
                            for product_variant in product_stg_id.product_template_id.product_variant_ids:
                                if product_variant.id != product_stg_id.product_template_id.product_variant_id.id and product_variant.izi_id not in response_data.get('product_variant_ids') and not product_variant.product_variant_stg_ids and product_variant.product_tmpl_id.id == product_stg_id.product_template_id.id:
                                    product_variant.active = False

                        if do_export:
                            izi_id = product_stg_id.izi_id
                            if izi_id != 0:
                                url = '{}/ui/products/export'.format(
                                    server.name)
                                req = requests.post(
                                    url,
                                    headers={
                                        'X-Openerp-Session-Id': server.session_id},
                                    json={'product_staging_id': izi_id})

                                if req.status_code == 200:
                                    response = req.json().get('result')
                                    if response.get('code') == 200:
                                        data = response.get('data')
                                        product_stg_id.mp_external_id = data['external_id']['staging_external_id']
                                        if data['external_id']['variant_external_ids']:
                                            variant_exid = data['external_id']['variant_external_ids']
                                            for var_stg in product_stg_id.product_variant_stg_ids:
                                                var_stg.mp_external_id = variant_exid[var_stg.izi_id]
                                    else:
                                        if response.get('data').get('error_descrip'):
                                            raise UserError(response.get(
                                                'data').get('error_descrip'))

                                else:
                                    if response.get('data').get('error_descrip'):
                                        raise UserError(response.get(
                                            'data').get('error_descrip'))
                    else:
                        if response.get('data').get('error_descrip') != None:
                            raise UserError(response.get(
                                'data').get('error_descrip'))
                        else:
                            raise UserError(
                                "Error from IZI. Failed Upload to IZI")
            except Exception as e:
                raise UserError(str(e))
        return True
    
    def upload_product_stg_izi(self):
        for product_staging in self:
            product_staging._do_upload_product_stg_izi(generate_variant=True, do_export=True)

    def generate_staging_variant(self):
        for product_staging in self:
            if product_staging.mp_tokopedia_id:
                product_staging._do_upload_product_stg_izi(generate_variant=True)
            elif product_staging.mp_shopee_id:
                product_staging.generate_shopee_variant()
                
    
    @api.onchange('tp_category_id')
    def _change_tp_category_id(self):
        if self.mp_tokopedia_id and self.tp_category_id:
            server = self.env['webhook.server'].search(
                [('active', 'in', [False, True])],
                limit=1, order='write_date desc')
            if not server:
                raise UserError('Buatkan minimal 1 webhook server!')
            url = '{}/ui/products/change_category/tokopedia'.format(
                server.name)
            req = requests.post(
                url,
                headers={'X-Openerp-Session-Id': server.session_id},
                json={'tp_category_id': self.tp_category_id.izi_id, 'mp_tokopedia_id': self.mp_tokopedia_id.izi_id})
            if req.status_code == 200:
                response = req.json().get('result')
                if response.get('code') == 200:
                    response_data = response.get('data')
                    if response_data.get('tp_variant_ids'):
                        domain_url = "[('id', 'in', %s)]" % str(
                            response_data.get('tp_variant_ids'))
                        server.get_records(
                            'mp.tokopedia.category.variant', domain_url=domain_url, force_update=True)
                    if response_data.get('tp_unit_ids'):
                        domain_url = "[('id', 'in', %s)]" % str(
                            response_data.get('tp_unit_ids'))
                        server.get_records(
                            'mp.tokopedia.category.unit', domain_url=domain_url, force_update=True)
                    if response_data.get('tp_value_ids'):
                        domain_url = "[('id', 'in', %s)]" % str(
                            response_data.get('tp_value_ids'))
                        server.get_records(
                            'mp.tokopedia.category.value', domain_url=domain_url, force_update=True)

    def generate_shopee_variant(self):
        server = self.env['webhook.server'].search(
            [('active', 'in', [False, True])], limit=1, order='write_date desc')
        if not server:
            raise UserError('Create at least 1 webhook server')

        # validated must be upload to izi master product
        if self.product_template_id.izi_id == 0 or not self.product_template_id.izi_id or self.product_template_id.izi_id == None:
            self.product_template_id.upload_product_tmpl_izi()

        # validated must be upload to izi staging product
        if self.izi_id == 0 or not self.izi_id or self.izi_id == None:
            self._do_upload_product_stg_izi()

        # make sure the product have a izi_id
        if self.izi_id and self.izi_id != 0 and self.izi_id != None:
            body = {
                'product_staging': self.izi_id
            }
            tier_variation = False
            if self.sp_attribute_line_ids and self.mp_shopee_id:
                tier_variation = []

                for attribute in self.sp_attribute_line_ids:
                    name = attribute.attribute_id.name
                    options = []
                    for value in attribute.value_ids:
                        options.append(value.name)

                    vals = {
                        'name': name,
                        'options': options
                    }
                    tier_variation.append(vals)

                if tier_variation:
                    body.update({
                        'tier_variation': tier_variation
                    })

                    try:
                        url = '{}/ui/products/sp/generate/variant'.format(
                            server.name)
                        req = requests.post(
                            url,
                            headers={
                                'X-Openerp-Session-Id': server.session_id},
                            json=body)

                        if req.status_code == 200:
                            response = req.json().get('result')
                            if response.get('code') == 200:
                                data = response.get('data')

                                # unlink attribute line not have izi idi
                                for attr in self.sp_attribute_line_ids:
                                    if attr.izi_id == 0 or not attr.izi_id:
                                        attr.sudo().unlink()

                                attr_value = self.env['mp.shopee.item.var.attribute.value'].search(
                                    ['|', ("izi_id", '=', 0), ("izi_id", "=", False)])
                                for val in attr_value:
                                    val.sudo().unlink()

                                attr_ids = self.env['mp.shopee.item.var.attribute'].search(
                                    ['|', ("izi_id", '=', 0), ("izi_id", "=", False)])
                                for attr in attr_ids:
                                    attr.sudo().unlink()

                                # unlink not useless product variant stg
                                product_var_stg_ids = self.product_variant_stg_ids
                                for var_stg in product_var_stg_ids:
                                    # if var_stg.izi_id not in data['product_variant_stg_ids']:
                                    #     var_stg.sudo().unlink()
                                    if var_stg.product_id.izi_id not in data['product_ids']:
                                        var_stg.product_id.sudo().unlink()

                                server.get_records('product.product', force_update=True, domain_url="[('id', 'in', %s)]" % str(
                                    data.get("product_ids")))
                                server.get_records('mp.shopee.item.var.attribute', domain_url="[('id', 'in', %s)]" % str(
                                    data.get("attribute_ids")))
                                server.get_records('mp.shopee.item.var.attribute.value', domain_url="[('id', 'in', %s)]" % str(
                                    data.get("attribute_value_ids")))
                                server.get_staging_attribute_line_and_staging_variant(
                                    domain_url_attr="[('id', 'in', %s)]" % str(
                                    data.get("attribute_line_ids")), 
                                    domain_url_var="[('id', 'in', %s)]" % str(
                                    data.get("product_variant_stg_ids")))

                            else:
                                if response.get('data').get('error_descrip'):
                                    raise UserError(response.get(
                                        'data').get('error_descrip'))
                        else:
                            is_success = (False, "Upload Failed")

                    except Exception as e:
                        raise UserError(str(e))
            else:
                raise UserError(
                    'Variant is not set, Set variant attribute line first')
