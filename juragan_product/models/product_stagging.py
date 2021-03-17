from odoo import models, fields, api, tools, _
from odoo.addons import decimal_precision as dp
from odoo.addons.juragan_webhook import BigInteger, BigMany2one
from odoo.exceptions import ValidationError


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
    product_variant_stg_id = fields.One2many(
        'product.staging.variant', 'product_stg_id',
        'Product Variant Staging',
        domain=['|', ('active', '=', False), ('active', '=', True), ],
        context={'active_test': False})
    product_image_staging_ids = fields.One2many(
        'product.image.staging', 'product_stg_id')

    is_uploaded = fields.Boolean('Is Uploaded')
    is_active = fields.Boolean('Is Active')
    qty_available = fields.Integer('Qty Available', compute='_get_qty_available')
    product_uom_id = fields.Many2one(
        'uom.uom', 'Unit of Measure',
        readonly=True, compute='_get_qty_available')
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

    mp_tokopedia_product_id = BigMany2one(
        'mp.tokopedia.product', string='Tokopedia Product')
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

    mp_shopee_id = fields.Many2one('mp.shopee', string='Shopee ID')
    sp_condition = fields.Selection(
        [('NEW', 'NEW'), ('USED', 'USED')], 'Condition')
    sp_status = fields.Selection(
        [('NORMAL', 'NORMAL'), ('UNLIST', 'UNLIST')], 'Status Produk', compute='_set_sp_status')
    sp_is_pre_order = fields.Boolean('Pre Order')
    sp_days_to_ship = fields.Integer()
    sp_condition = fields.Selection(
        [('NEW', 'NEW'), ('USED', 'USED')])

    sp_category_int = BigInteger()
    sp_category_id = BigMany2one(
        'mp.shopee.item.category', compute='_get_category_id', inverse='_set_category_id')
    sp_logistics = fields.One2many(
        'mp.shopee.item.logistic', 'item_id_staging')
    sp_attributes = fields.One2many(
        'mp.shopee.item.attribute.val', 'item_id_staging')

    # mp_lazada_product_id = fields.Many2one(
    #     'mp.lazada.product', string='Lazada Product')
    # mp_lazada_id = fields.Many2one('mp.lazada', string='Lazada ID')

    product_wholesale_ids = fields.One2many(
        'product.staging.wholesale', 'product_stg_id')

    izi_id = fields.Integer('Izi ID')
    izi_md5 = fields.Char()

    def mp_upload(self):
        self.ensure_one()
        p_method = self.__marketplace_upload_for__.get(self.mp_type)
        server = self.env['webhook.server'].search(
            [('active', 'in', [False, True])],
            limit=1, order='write_date desc')
        if not server:
            raise
        uploaded = server.execute_action(self._name, self.id, p_method)
        if uploaded[0]:
            msg = _("Upload to %s" % self.mp_type)
        else:
            msg = _("Fail to upload to %s : %s" % (self.mp_type, uploaded[1]))
            raise ValidationError(msg)
        self.product_template_id.message_post(
            body=uploaded[1], subject=msg)

    def _get_qty_available(self):
        for rec in self:
            lot_stock_id = False
            product_id = False
            if rec.mp_tokopedia_id:
                lot_stock_id = rec.mp_tokopedia_id.wh_id.lot_stock_id.id
            if rec.product_template_id and rec.product_template_id.product_variant_ids:
                product_id = rec.product_template_id.product_variant_ids[0].id
            if lot_stock_id and product_id:
                # self.env['stock.quant']._merge_quants()
                # self.env['stock.quant']._unlink_zero_quants()
                quants = self.env['stock.quant'].search(
                    [('product_id', '=', product_id),
                     ('location_id', '=', lot_stock_id)])
                rec.qty_available = sum(
                    q['quantity'] - q['reserved_quantity'] for q in quants)
                # rec.product_uom_id = quants and quants[0].product_uom_id
            else:
                rec.qty_available = 0
                # rec.product_uom_id = False

    @api.onchange('product_template_id', 'mp_type')
    def onchange_product_template_id(self):
        mp_tp = [('id', 'in', self.product_template_id and self.product_template_id.mp_tokopedia_ids.ids or []), ]
        mp_sh = [('id', 'in', self.product_template_id and self.product_template_id.mp_shopee_ids.ids or []), ]
        return {'domain': {
            'mp_tokopedia_id': mp_tp,
            'mp_shopee_id': mp_sh,
        }}
    
    def _set_category_id(self):
        self.sp_category_int = self.sp_category_id.id

    def _set_sp_status(self):
        for rec in self:
            if rec.is_active:
                rec.sp_status = 'NORMAL'
            else:
                rec.sp_status = 'UNLIST'
