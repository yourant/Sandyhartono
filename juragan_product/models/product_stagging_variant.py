from odoo import models, fields, api
from odoo.addons import decimal_precision as dp
from odoo.addons.juragan_webhook import BigInteger


class ProductVariantStaging(models.Model):
    _name = 'product.staging.variant'
    _description = 'Product Stagging Variant'

    name = fields.Char(string='Variant Name')
    barcode = fields.Char('Barcode')
    default_code = fields.Char(
        'Internal Reference')
    qty_available = fields.Integer('Qty Available')
    active = fields.Boolean(
        string='Active Variant', related='product_id.active')
    is_active = fields.Boolean(string='Is Active Variant')
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
    price_custom = fields.Float('Price Custom')
    sp_variant_name = fields.Char(string='Shopee Variant Name')
    sp_variant_id = BigInteger()
    sp_variant_status = fields.Char()
    sp_update_time_unix = fields.Float('Last Update Time')
    sp_attribute_value_ids = fields.Many2many('mp.shopee.item.var.attribute.value', string='Shopee Variation Attributes', ondelete='restrict')
    tp_variant_value_ids = fields.Many2many('mp.tokopedia.variant.value')


    image_url = fields.Char('Image URL', compute='_get_image_url')
    image_url_external = fields.Char('Image URL External')

    izi_id = fields.Integer('Izi ID')
    izi_md5 = fields.Char()

    def _get_image_url(self):
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        for rec in self:
            if rec.image:
                rec.image_url = '%s/jpg/product.staging.variant/image/%s.jpg' % (
                    base_url, str(rec.id))
            elif rec.image_url_external:
                rec.image_url = rec.image_url_external


class MPTokopediaAttributeLine(models.Model):
    _name = 'mp.tokopedia.attribute.line'

    izi_id = fields.Integer('Izi ID')
    product_staging_id = fields.Many2one('product.staging')
    tp_variant_id = fields.Many2one('mp.tokopedia.category.variant')
    tp_variant_unit_id = fields.Many2one('mp.tokopedia.category.unit')
    tp_variant_value_ids = fields.Many2many('mp.tokopedia.variant.value')


class MPTokopediaVariantValue(models.Model):
    _name = 'mp.tokopedia.variant.value'

    izi_id = fields.Integer('Izi ID')
    name = fields.Char('Value')
    units = fields.Many2many('mp.tokopedia.category.unit')
    tp_value_id = fields.Many2one('mp.tokopedia.category.value')
    tp_value_external_id = BigInteger()
    product_staging_variant_ids = fields.Many2many('product.staging.variant')
    tp_attribute_line_ids = fields.Many2many('mp.tokopedia.attribute.line')
