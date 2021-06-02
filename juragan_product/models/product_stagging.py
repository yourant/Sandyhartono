from lxml import etree
from odoo import models, fields, api, tools, _
from odoo.addons import decimal_precision as dp
from odoo.addons.juragan_webhook import BigInteger, BigMany2one
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError
import requests
import time

import logging

_logger = logging.getLogger(__name__)


class ProductStaging(models.Model):
    _name = 'product.staging'
    _description = 'Product Stagging'
    __marketplace_upload_for__ = {
        'Tokopedia': 'tp_export_product',
        'Shopee': 'sp_export_product',
        'Lazada': 'lz_export_product',
    }

    @api.model
    def default_get(self, default_fields):
        res = super().default_get(default_fields)
        mp_type = False
        if res.get('mp_tokopedia_id'):
            mp_type = 'Tokopedia'
        elif res.get('mp_shopee_id'):
            mp_type = 'Shopee'
        elif res.get('mp_lazada_id'):
            mp_type = 'Lazada'
        if not res.get('mp_type'):
            res['mp_type'] = mp_type
        if not res.get('product_template_id'):
            res['product_template_id'] = self._context.get('default_tmpl_id')
        return res

    product_template_id = fields.Many2one(
        'product.template', 'Product Template')
    name = fields.Char('Name', index=True, translate=True)
    description_sale = fields.Text('Description')
    brand_id = fields.Many2one('product.brand', string='Brand')
    list_price = fields.Float(
        'Sales Price', digits=dp.get_precision('Product Price'))
    weight = fields.Float(
        'Weight', digits=dp.get_precision('Stock Weight'), store=True)
    length = fields.Float('Length')
    width = fields.Float('Width')
    height = fields.Float('Height')
    barcode = fields.Char('Barcode')
    default_code = fields.Char(
        'Internal Reference', store=True)
    active = fields.Boolean('Active', default=True)
    product_variant_stg_ids = fields.One2many('product.staging.variant', 'product_stg_id', 'Variant', domain=[
                                              '|', ('active', '=', False), ('active', '=', True), ], context={'active_test': False})
    product_image_staging_ids = fields.One2many(
        'product.image.staging', 'product_stg_id')

    is_uploaded = fields.Boolean('Uploaded')
    is_active = fields.Boolean('Active')
    qty_available = fields.Integer(
        'Qty Available', readonly=True, compute='_get_qty_available')
    product_uom_id = fields.Many2one('uom.uom', 'Unit of Measure')
    min_order = fields.Integer('Min Order')
    package_content = fields.Text('Package Content')
    latest_upload_status = fields.Selection([('1', 'DONE'), ('2', 'FAILED')])

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
    ], string='Availability', default=2)
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
    tp_category_id = fields.Many2one(
        'mp.tokopedia.category', string='Category')
    tp_etalase_id = fields.Many2one(
        'mp.tokopedia.etalase', string='Etalase', )
    tp_latest_upload_id = fields.Integer('Latest Upload ID')
    tp_attribute_line_ids = fields.One2many(
        'mp.tokopedia.attribute.line', 'product_staging_id', 'Product Attributes Variations')
    tp_etalase_name = fields.Char(string='Etalase Name')
    tp_is_must_insurance = fields.Boolean('Must Insurance', default=False)
    tp_is_free_return = fields.Boolean('Free Return Cost', default=False)
    tp_preorder = fields.Boolean('Pre-Order', default=False)
    tp_preorder_duration = fields.Integer('Pre-Order Duration')
    tp_preorder_time_unit = fields.Selection([
        ('1', 'DAY'),
        ('2', 'WEEK'),
    ], string='Pre-Order Time Unit')

    mp_shopee_id = fields.Many2one('mp.shopee', string='Shopee ID',
        domain=['|', ('active', '=', False), ('active', '=', True), ],
        context={'active_test': False})
    sp_condition = fields.Selection(
        [('NEW', 'NEW'), ('USED', 'USED')], 'Condition')
    sp_status = fields.Selection(
        [('NORMAL', 'NORMAL'), ('UNLIST', 'UNLIST')], 'Status Produk', compute='_set_sp_status')
    sp_is_pre_order = fields.Boolean('Pre Order')
    sp_days_to_ship = fields.Integer(default=2)


    sp_category_id = BigMany2one('mp.shopee.item.category',string='Shopee Category')
    sp_category_int = BigInteger()
    sp_logistics = fields.One2many(
        'mp.shopee.item.logistic', 'item_id_staging')
    sp_attributes = fields.One2many(
        'mp.shopee.item.attribute.val', 'item_id_staging')

    sp_attribute_line_ids = fields.One2many('mp.shopee.attribute.line', 'product_staging_id', 'Product Attributes Variations')

    mp_lazada_id = fields.Many2one('mp.lazada', string='Lazada ID',
        domain=['|', ('active', '=', False), ('active', '=', True), ],
        context={'active_test': False})
    lz_category_id =  fields.Many2one('mp.lazada.category', string='Product Category')
    lz_attribute_line_ids = fields.One2many('mp.lazada.attribute.line', 'product_staging_id', string='Attributes Line')
    lz_brand_id =  fields.Many2one('mp.lazada.brand', string='Product Brand')
    lz_attributes = fields.One2many('mp.lazada.product.attr', 'item_id_staging', string='Attributes Category')
    lz_status = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('deleted', 'Deleted')
    ])
    lz_sku_id = fields.Char()

    product_wholesale_ids = fields.One2many(
        'product.staging.wholesale', 'product_stg_id')

    product_variant_ids = fields.Many2many('product.product')

    image = fields.Binary("Image", attachment=True)
    image_url = fields.Char('Image URL', compute='_get_image_url')
    image_url_external = fields.Char('Image URL External')

    izi_id = fields.Integer('Izi ID')
    izi_md5 = fields.Char()

    def _get_image_url(self):
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        for rec in self:
            if rec.image:
                rec.image_url = '%s/jpg/product.staging/image/%s.jpg' % (
                    base_url, str(rec.id))
            elif rec.image_url_external:
                rec.image_url = rec.image_url_external

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
        self.mp_type = ctx.get('mp_tipe')
        mp_id = ctx.get('mp_int_id', False)

        if ctx.get('mp_tipe') == 'Tokopedia':
            tp = mp_id
            pd_tmpl.mp_tokopedia_ids = [(4, tp)]

            self.mp_tokopedia_id = tp
        if ctx.get('mp_tipe') == 'Shopee':
            sh = mp_id
            pd_tmpl.mp_shopee_ids = [(4, sh)]

            self.mp_shopee_id = sh
        if ctx.get('mp_tipe') == 'Lazada':
            lz = mp_id
            pd_tmpl.mp_lazada_ids = [(4, lz)]

            self.mp_lazada_id = lz
        
        # mapping pd template field to pd staging
        self.default_code = pd_tmpl.default_code
        self.barcode = pd_tmpl.barcode
        self.description_sale = pd_tmpl.description_sale
        self.list_price = pd_tmpl.list_price
        self.image = pd_tmpl.image
        self.image_url_external = pd_tmpl.image_url_external
        self.min_order = 1
        self.tp_active_status = 3
        self.tp_available_status = 2
        self.tp_condition = 1
        self.tp_weight_unit = 1

        images = []
        for image in pd_tmpl.product_image_ids:
            images.append((0, 0, {
                'name': 'product.staging_%s' % str(time.time()),
                'image': image.image.decode('utf-8') if image.image else None,
                'url_external': image.url_external
            }))
        if len(images) > 0:
            self.write({
                'product_image_staging_ids': images
            })
        
        wholesales = []
        for wholesale in pd_tmpl.product_wholesale_ids:
            wholesales.append((0, 0, {
                'min_qty': wholesale.min_qty,
                'max_qty': wholesale.max_qty,
                'price_wholesale': wholesale.price_wholesale
            }))
        if len(wholesales) > 0:
            self.write({
                'product_wholesale_ids': wholesales
            })

        # mapping shopee logistic
        if not self.sp_logistics:
            logistic_shop = self.env['mp.shopee.shop.logistic'].search([('mp_id','=',sh),('enabled','=',True),('is_parent','=',True)])
            self.sp_logistics = [(5, 0, 0), *[(0, 0, {
                        'logistic_id': logistic.logistic_id.id
                    }) for logistic in logistic_shop]]
        if self.mp_type:
            msg = {
                "message": "Sukses membuat produk %s" % self.mp_type,
                "title": "Produk Staging", "sticky": False}
            self.env.user.fcm_notify_success(**msg)
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }

    def _get_qty_available(self):
        for rec in self:
            lot_stock_id = False
            product_id = []
            if rec.mp_tokopedia_id:
                lot_stock_id = rec.mp_tokopedia_id.wh_id.lot_stock_id.id
            elif rec.mp_shopee_id:
                lot_stock_id = rec.mp_shopee_id.wh_id.lot_stock_id.id
            elif rec.mp_lazada_id:
                lot_stock_id = rec.mp_lazada_id.wh_id.lot_stock_id.id
            if rec.product_template_id and rec.product_template_id.product_variant_ids:
                for variant in rec.product_template_id.product_variant_ids:
                    if variant.active:
                        product_id.append(variant.id)
            if lot_stock_id and product_id:
                quants = self.env['stock.quant'].search(
                    [('product_id', 'in', product_id),
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
    def _sp_change_category_id(self):
        if self.mp_shopee_id and self.sp_category_id:
            try:
                mp_id_by_izi_id = self.mp_shopee_id.izi_id
                category_id = self.sp_category_id.izi_id
                server = self.get_webhook_server()
                if server:
                    if not self.sp_category_id.attributes:
                        res = server.sp_get_attribute_category(category_id,mp_id_by_izi_id)
                # self.mp_ids[0].get_item_category(category_ids=self.category_id.ids)
                self.sp_attributes = [(5, 0, 0), *[(0, 0, {
                    'attribute_id': attribute.id
                }) for attribute in self.sp_category_id.attributes]]
            except Exception as e:
                _logger.warn(e)

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
        product_template_id = self.env['product.template'].search(
            [('id', '=', tmpl_id)])
        exist_mp_tokopedia_ids = []
        exist_mp_shopee_ids = []
        exist_mp_lazada_ids = []
        if product_template_id:
            for product_staging in product_template_id.product_staging_ids:
                if product_staging.mp_tokopedia_id:
                    exist_mp_tokopedia_ids.append(product_staging.mp_tokopedia_id.id)
                elif product_staging.mp_shopee_id:
                    exist_mp_shopee_ids.append(product_staging.mp_shopee_id.id)
                elif product_staging.mp_lazada_id:
                    exist_mp_lazada_ids.append(product_staging.mp_lazada_id.id)

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
                if mp.id not in exist_mp_tokopedia_ids:
                    mp_list.append(mp_name_get(mp))
            for mp in mp_shopee_ids:
                if mp.id not in exist_mp_shopee_ids:
                    mp_list.append(mp_name_get(mp))
            for mp in mp_lazada_ids:
                if mp.id not in exist_mp_lazada_ids:
                    mp_list.append(mp_name_get(mp))
            for mpl in mp_list:
                btn_xml = mp_button_xml % mpl
                xb = etree.fromstring(btn_xml)
                divbox[0].append(xb)
            res['arch'] = etree.tostring(doc, encoding='unicode')
        return res

    def _do_upload_product_stg_izi(self, generate_variant=False, do_export=False):
        response_fields_from_izi = [
            'product_image_staging_ids', 'product_wholesale_ids', 'product_variant_ids', 'tp_attribute_line_ids', 'product_variant_stg_ids','sp_attributes','sp_logistics','lz_attributes']
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
                "tp_etalase_id": product_stg_id.tp_etalase_id.izi_id,
                "tp_condition": product_stg_id.tp_condition,
                "tp_available_status": product_stg_id.tp_available_status,
                "tp_weight_unit": product_stg_id.tp_weight_unit,
                "tp_active_status": product_stg_id.tp_active_status,
                "tp_is_must_insurance": product_stg_id.tp_is_must_insurance,
                "tp_is_free_return": product_stg_id.tp_is_free_return,
                "tp_preorder": product_stg_id.tp_preorder,
                "tp_preorder_duration": product_stg_id.tp_preorder_duration,
                "tp_preorder_time_unit": product_stg_id.tp_preorder_time_unit,
            
                # shopee
                "mp_shopee_id": product_stg_id.mp_shopee_id.izi_id,
                "sp_is_pre_order": product_stg_id.sp_is_pre_order,
                "sp_category_int": product_stg_id.sp_category_id.izi_id,
                "sp_days_to_ship": product_stg_id.sp_days_to_ship,
                "sp_condition": product_stg_id.sp_condition,
                "sp_status": product_stg_id.sp_status,

                # lazada
                "mp_lazada_id": product_stg_id.mp_lazada_id.izi_id,
                "lz_sku_id": product_stg_id.lz_sku_id,
                "lz_category_id": product_stg_id.lz_category_id.izi_id,
                "lz_brand_id": product_stg_id.lz_brand_id.izi_id,
            }

            # check tokopedia etalse
            if not product_stg_id.tp_etalase_id.izi_id or product_stg_id.tp_etalase_id.izi_id == 0:
                json_data.update({
                    'tp_etalase_id': False,
                    'tp_etalase_name': product_stg_id.tp_etalase_id.etalase_name
                })

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

            # if variant_table and attribute_lines and product_stg_id.product_variant_stg_ids:
            if product_stg_id.product_variant_stg_ids:
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
                    lz_values = []
                    for lz_value in variant_staging.lz_variant_value_ids:
                        lz_values.append(lz_value.izi_id)
                    variant_data.update({
                        'lz_variant_value_ids': lz_values
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
                if line.enabled:
                    sp_logistics.append({
                        "logistic_name": line.logistic_id and line.logistic_id.izi_id,
                        "estimated_shipping_fee": line.estimated_shipping_fee,
                        "is_free": line.is_free,
                        "is_active": line.enabled,
                    })
            json_data.update({
                'sp_logistics': sp_logistics
            })

            lz_attributes = []
            for attr in product_stg_id.lz_attributes:
                attr_value = False
                if attr.attribute_id.input_type == 'text':
                    attr_value = attr.value
                else:
                    attr_value = attr.option_id.izi_id
                lz_attributes.append({
                    'attr_id': attr.attribute_id.izi_id,
                    'attr_value': attr_value,
                })
            json_data.update({
                'lz_attributes': lz_attributes
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
                                if response_key == 'lz_attributes':
                                    server.with_context(create_product_attr=True).get_records(
                                        product_stg_id[response_key]._name, domain_url=domain_url, force_update=True)
                                else:
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

                        # get product staging by izi_id
                        domain_url = "[('id', 'in', [%s])]" % str(
                            response_data.get('id'))
                        server.get_records(
                            'product.staging', domain_url=domain_url, force_update=True)

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
                                                var_stg.mp_external_id = variant_exid[str(var_stg.izi_id)]
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

            server = self.env['webhook.server'].search(
                [('active', 'in', [False, True])],
                limit=1, order='write_date desc')
            if not server:
                raise UserError('Buatkan minimal 1 webhook server!')
            # custom get records tokopedia product
            if product_staging.mp_tokopedia_id and product_staging.mp_external_id:
                if not product_staging.tp_etalase_id:
                    server.get_records('mp.tokopedia.etalase',domain_code='all_active')
                    # get product staging by izi_id
                    domain_url = "[('id', 'in', [%s])]" % str(product_staging.izi_id)
                    server.get_records('product.staging', domain_url=domain_url, force_update=True)
                    etalase_ids = product_staging.env['mp.tokopedia.etalase'].search(
                        [('izi_id', '=', False)])
                    for etalase_id in etalase_ids:
                        etalase_id.active = False
                        etalase_id.unlink()

            # custom get records shopee product
            elif product_staging.mp_shopee_id and product_staging.mp_external_id:
                product_izi_id = product_staging.izi_id
                
            
                # unlink before get
                if product_staging.sp_logistics:
                    for logistic in product_staging.sp_logistics:
                        logistic.sudo().unlink()

                    # Get Logistic Shopee
                    server.get_records('mp.shopee.item.logistic', domain_url="[('item_id_staging', '=', %i)]" % product_izi_id)

                if product_staging.product_image_staging_ids:
                    for image in product_staging.product_image_staging_ids:
                        image.sudo().unlink()

                    # get Image Shopee
                    server.get_records('product.image.staging', domain_url="[('product_stg_id', '=', %i)]" % product_izi_id)
            
            # custom get records lazada product
            elif product_staging.mp_lazada_id and product_staging.mp_external_id:
                product_izi_id = product_staging.izi_id
                if product_staging.product_image_staging_ids:
                    for image in product_staging.product_image_staging_ids:
                        image.sudo().unlink()

                    # get Image Shopee
                    server.get_records('product.image.staging', domain_url="[('product_stg_id', '=', %i)]" % product_izi_id)
               
                

    def generate_staging_variant(self):
        for product_staging in self:
            if product_staging.mp_tokopedia_id:
                product_staging._do_upload_product_stg_izi(generate_variant=True)
            elif product_staging.mp_shopee_id:
                product_staging.generate_shopee_variant()
            elif product_staging.mp_lazada_id:
                product_staging.generate_lazada_variant()
                
    
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
    
    @api.onchange('is_active')
    def _change_is_active(self):
        if self.mp_tokopedia_id:
            if self.is_active:
                self.tp_active_status = 1
            else:
                self.tp_active_status = 3
        if self.izi_id != 0 and self.izi_id != False and self.izi_id != None:
            server = self.env['webhook.server'].search(
                [('active', 'in', [False, True])],
                limit=1, order='write_date desc')
            if not server:
                raise UserError('Buatkan minimal 1 webhook server!')
            url = '{}/ui/products/set_active'.format(
                server.name)
            req = requests.post(
                url,
                headers={'X-Openerp-Session-Id': server.session_id},
                json={'product_staging_id': self.izi_id, 'set_active': self.is_active})
            if req.status_code == 200:
                response = req.json().get('result')
                if response.get('code') == 200:
                    domain_url = "[('id', 'in', [%s])]" % str(self.izi_id)
                    server.get_records(
                        'product.staging', domain_url=domain_url, force_update=True)


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
                                exist_product_by_izi_id = {}
                                product_var_stg_ids = self.product_variant_stg_ids
                                for var_stg in product_var_stg_ids:
                                    if var_stg.izi_id not in data['product_variant_stg_ids']:
                                        exist_product_by_izi_id[var_stg.product_id.izi_id] = var_stg.product_id
                                        var_stg.sudo().unlink()

                                    # if var_stg.product_id.izi_id not in data['product_ids']:
                                    #     var_stg.product_id.sudo().unlink()

                                # check product product and set False if not useless
                                product_by_izi_id = {}
                                product_products = self.env['product.product'].search([])
                                for prod in product_products:
                                    product_by_izi_id[prod.izi_id] = prod

                                for product_id in exist_product_by_izi_id:
                                    if product_id in product_by_izi_id:
                                        product_obj = product_by_izi_id[product_id]
                                        if not product_obj.product_variant_stg_ids:
                                            product_obj.active = False


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
                                    data.get("product_variant_stg_ids")), limit=500,mp_type="sp")

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


    def generate_lazada_variant(self):
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
            if self.lz_attribute_line_ids and self.mp_lazada_id:
                tier_variation = []

                for attribute in self.lz_attribute_line_ids:
                    name = attribute.attribute_id.name
                    options = []
                    for value in attribute.lz_variant_value_ids:
                        options.append(value.name)

                    if options:
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
                        url = '{}/ui/products/lz/generate/variant'.format(
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
                                for attr in self.lz_attribute_line_ids:
                                    if attr.izi_id == 0 or not attr.izi_id:
                                        attr.sudo().unlink()

                                attr_value = self.env['mp.lazada.variant.value'].search(
                                    ['|', ("izi_id", '=', 0), ("izi_id", "=", False)])
                                for val in attr_value:
                                    val.sudo().unlink()


                                # unlink not useless product variant stg
                                exist_product_by_izi_id = {}
                                product_var_stg_ids = self.product_variant_stg_ids
                                for var_stg in product_var_stg_ids:
                                    if var_stg.izi_id not in data['product_variant_stg_ids']:
                                        exist_product_by_izi_id[var_stg.product_id.izi_id] = var_stg.product_id
                                        var_stg.sudo().unlink()

                                    # if var_stg.product_id.izi_id not in data['product_ids']:
                                    #     var_stg.product_id.sudo().unlink()

                                # check product product and set False if not useless
                                product_by_izi_id = {}
                                product_products = self.env['product.product'].search([])
                                for prod in product_products:
                                    product_by_izi_id[prod.izi_id] = prod

                                for product_id in exist_product_by_izi_id:
                                    if product_id in product_by_izi_id:
                                        product_obj = product_by_izi_id[product_id]
                                        if not product_obj.product_variant_stg_ids:
                                            product_obj.active = False


                                server.get_records('product.product', force_update=True, domain_url="[('id', 'in', %s)]" % str(
                                    data.get("product_ids")))
                                server.get_records('mp.lazada.variant.value', domain_url="[('id', 'in', %s)]" % str(
                                    data.get("attribute_value_ids")))
                                server.get_staging_attribute_line_and_staging_variant(
                                    domain_url_attr="[('id', 'in', %s)]" % str(
                                    data.get("attribute_line_ids")), 
                                    domain_url_var="[('id', 'in', %s)]" % str(
                                    data.get("product_variant_stg_ids")), limit=500,mp_type="lz")

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

    def update_staging_stock(self):
        form_view = self.env.ref('juragan_product.update_staging_stock_form')
        return {
            'name': 'Update Qty Available',
            'view_mode': 'form',
            'res_model': 'staging.stock.wizard',
            'view_id': form_view.id,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {
                'product_staging_id': self.id,
                'default_qty_available': self.qty_available,
            },
        }
