from odoo import models, fields
from odoo.addons import decimal_precision as dp
from odoo.addons.juragan_webhook import BigInteger


class ProductVariantStaging(models.Model):
    _name = 'product.staging.variant'
    _description = 'Product Stagging Variant'

    name = fields.Char(string='Variant Name')
    default_code = fields.Char(
        'Internal Reference')
    qty_available = fields.Integer('Qty Available')
    active = fields.Boolean(string='Active Variant')
    price_custom = fields.Float('Price Custom')
    product_stg_id = fields.Many2one(
        'product.staging', 'Product Staging',
        ondelete="cascade", )
    prdp_ids = fields.Many2one(
        'product.product', 'Product Product',
        auto_join=True, index=True, ondelete="cascade", )
    attribute_value_ids = fields.Many2many(
        related='prdp_ids.product_template_attribute_value_ids', readonly=True,
        string='Attributes', )
    # image_variant = fields.Binary(
    #     "Variant Image", attachment=True,
    #     help="This field holds the image used as image for the product \
    #     variant, limited to 1024x1024px.")
    image = fields.Binary("Image", attachment=True)
    mp_external_id = BigInteger()
    tp_update_time_unix = fields.Float('Last Update Time')
    volume = fields.Float(
        'Volume',
        help="The volume in m3.", store=True)
    weight = fields.Float(
        'Weight', digits=dp.get_precision('Stock Weight'), store=True,
        help="The weight of the contents in Kg, \
        not including any packaging, etc.")
    price = fields.Float(
        'Price',
        digits=dp.get_precision('Product Price'))
    lst_price = fields.Float(
        'Sale Price',
        digits=dp.get_precision('Product Price'))
    price_extra = fields.Float(
        'Variant Price Extra',
        digits=dp.get_precision('Product Price'))
    list_price = fields.Float('Price Master')
    price_custom = fields.Float('Price Custom')
    sp_variant_name = fields.Char(string='Shopee Variant Name')
    sp_variant_id = BigInteger()
    sp_variant_status = fields.Char()
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
