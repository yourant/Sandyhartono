from odoo import models, fields, api
from odoo.addons import decimal_precision as dp
from odoo.addons.juragan_webhook import BigInteger
from odoo.exceptions import UserError
import requests

class ProductVariantStaging(models.Model):
    _name = 'product.staging.variant'
    _description = 'Product Stagging Variant'

    name = fields.Char(string='Variant Name')
    barcode = fields.Char('Barcode')
    default_code = fields.Char(
        'Internal Reference')
    qty_available = fields.Integer(
        'Qty Available', readonly=True, compute='_get_qty_available')
    active = fields.Boolean(
        string='Active Variant', related='product_id.active')
    is_active = fields.Boolean(string='Active', default=False)
    is_uploaded = fields.Boolean(string='Is Uploaded')
    product_stg_id = fields.Many2one(
        'product.staging', 'Product Staging',
        ondelete="cascade", )
    product_id = fields.Many2one(
        'product.product', 'Product Product',
        index=True, ondelete="cascade", )
    attribute_value_ids = fields.Many2many(
        related='product_id.attribute_value_ids', readonly=True,
        string='Attributes', )
    image = fields.Binary("Image", attachment=True)
    mp_external_id = BigInteger()
    price_custom = fields.Float('Sales Price')
    sp_variant_name = fields.Char(string='Shopee Variant Name')
    sp_variant_id = BigInteger()
    sp_variant_status = fields.Char()
    sp_update_time_unix = fields.Float('Last Update Time')
    sp_attribute_value_ids = fields.Many2many('mp.shopee.item.var.attribute.value', string='Shopee Variation Attributes', ondelete='restrict')
    tp_variant_value_ids = fields.Many2many('mp.tokopedia.variant.value')
    lz_variant_value_ids = fields.Many2many('mp.lazada.variant.value')
    bli_variant_value_ids = fields.Many2many('mp.blibli.variant.value')
    bli_itemsku = fields.Char()
    
    image_url = fields.Char('Image URL', compute='_get_image_url')
    image_url_external = fields.Char('Image URL External')

    izi_id = fields.Integer('Izi ID')
    izi_md5 = fields.Char()



    @api.onchange('price_custom')
    def validasi_form(self):
        if self.price_custom < 0:
            return {
                'warning': {
                    'title': 'Warning Validation',
                    'message': 'Please input Price must higher than 0',
                }
            }
        elif self.price_custom < 99 and self.price_custom != 0:
            return {
                'warning': {
                    'title': 'Warning Validation',
                    'message': 'Please input Price must higher than 99',
                }
            }
    

    def _get_image_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for rec in self:
            if rec.image:
                rec.image_url = '%s/jpg/product.staging.variant/image/%s.jpg' % (
                    base_url, str(rec.id))
            elif rec.image_url_external:
                rec.image_url = rec.image_url_external
            else:
                rec.image_url = False
    
    def _get_qty_available(self):
        for rec in self:
            lot_stock_id = False
            product_id = False
            if rec.product_stg_id.mp_tokopedia_id:
                lot_stock_id = rec.product_stg_id.mp_tokopedia_id.wh_id.lot_stock_id.id
            elif rec.product_stg_id.mp_shopee_id:
                lot_stock_id = rec.product_stg_id.mp_shopee_id.wh_id.lot_stock_id.id
            elif rec.product_stg_id.mp_lazada_id:
                lot_stock_id = rec.product_stg_id.mp_lazada_id.wh_id.lot_stock_id.id
            elif rec.product_stg_id.mp_blibli_id:
                lot_stock_id = rec.product_stg_id.mp_blibli_id.wh_id.lot_stock_id.id
            if rec.product_id.id:
                product_id = rec.product_id.id
            if lot_stock_id and product_id:
                quants = self.env['stock.quant'].search(
                    [('product_id', '=', product_id), ('location_id', '=', lot_stock_id)])
                rec.qty_available = sum(
                    q['quantity'] - q['reserved_quantity'] for q in quants)

            # # check last stock quantity for tokopedia product
            # if rec.product_stg_id.mp_tokopedia_id:
            #     if rec.qty_available <= 0:
            #         rec.write({
            #             'is_active': False,
            #         })
            #     elif rec.qty_available > 0:
            #         rec.write({
            #             'is_active': True,
            #         })
                
            #     inactive_staging_variants = 0
            #     for staging_variant in rec.product_stg_id.product_variant_stg_ids:
            #         if not staging_variant.is_active:
            #             inactive_staging_variants += 1
            #     if inactive_staging_variants >= len(rec.product_stg_id.product_variant_stg_ids):
            #         rec.product_stg_id.write({
            #             'is_active': False,
            #             'tp_available_status': 1,
            #             'tp_active_status': 3,
            #         })
            #     elif inactive_staging_variants < len(rec.product_stg_id.product_variant_stg_ids):
            #         rec.product_stg_id.write({
            #             'is_active': True,
            #             'tp_available_status': 2,
            #             'tp_active_status': 1,
            #         })

    def update_staging_variant_stock(self):
        form_view = self.env.ref('juragan_product.update_staging_variant_stock_form')
        return {
            'name': 'Update Qty Available',
            'view_mode': 'form',
            'res_model': 'staging.variant.stock.wizard',
            'view_id': form_view.id,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {
                'product_staging_variant_id': self.id,
                'default_qty_available': self.qty_available,
            },
        }
    
    @api.onchange('is_active')
    def _change_is_active(self):
        for rec in self:      
            if rec.izi_id != 0 and rec.izi_id != False and rec.izi_id != None:
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
                    json={'product_staging_variant_id': rec.izi_id, 'product_staging_id': rec.product_stg_id.izi_id, 'set_active': rec.is_active})
                if req.status_code == 200:
                    response = req.json().get('result')
                    if response.get('code') == 200:
                        domain_url = "[('id', 'in', [%s])]" % str(rec.izi_id)
                        server.get_records(
                            'product.staging.variant', domain_url=domain_url, force_update=True, loop_commit=False)
                        #### self.env.cr.commit()

class MPTokopediaAttributeLine(models.Model):
    _name = 'mp.tokopedia.attribute.line'

    izi_id = fields.Integer('Izi ID')
    product_staging_id = fields.Many2one('product.staging')
    tp_variant_id = fields.Many2one('mp.tokopedia.category.variant', string='Variant')
    tp_variant_unit_id = fields.Many2one('mp.tokopedia.category.unit', string='Unit')
    tp_variant_value_ids = fields.Many2many('mp.tokopedia.variant.value', string='Value')

    @api.onchange('tp_variant_id')
    def _change_tp_variant_id(self):
        self.tp_variant_unit_id = False
        self.tp_variant_value_ids = False

    @api.onchange('tp_variant_unit_id')
    def _change_tp_unit_id(self):
        self.tp_variant_value_ids = False    

class MPTokopediaVariantValue(models.Model):
    _name = 'mp.tokopedia.variant.value'

    izi_id = fields.Integer('Izi ID')
    name = fields.Char('Value')
    units = fields.Many2many('mp.tokopedia.category.unit')
    tp_value_id = fields.Many2one('mp.tokopedia.category.value')
    tp_value_external_id = BigInteger()
    product_staging_variant_ids = fields.Many2many('product.staging.variant')
    tp_attribute_line_ids = fields.Many2many('mp.tokopedia.attribute.line')
