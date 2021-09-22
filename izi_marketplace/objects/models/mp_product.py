# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models, tools

from odoo.addons import decimal_precision as dp


class MarketplaceProduct(models.Model):
    _name = 'mp.product'
    _inherit = 'mp.base'
    _description = 'Marketplace Product'
    _rec_mp_external_id = {}

    name = fields.Char(string="Name", index=True, required=True)
    active = fields.Boolean(default=True)
    currency_id = fields.Many2one(related="mp_account_id.currency_id")
    company_id = fields.Many2one(related="mp_account_id.company_id")
    description_sale = fields.Text(string="Sale Description",
                                   help="A description of the Product that you want to communicate to your customers. "
                                        "This description will be copied to every Sales Order, Delivery Order and "
                                        "Customer Invoice/Credit Note")
    default_code = fields.Char(string="Internal Reference")
    list_price = fields.Float(string="Sales Price", default=1.0, digits=dp.get_precision('Product Price'),
                              help="Base price to compute the customer price. Sometimes called the catalog price.")
    weight = fields.Float(string="Weight", digits=dp.get_precision('Stock Weight'),
                          help="The weight of the contents in Kg, not including any packaging, etc.")
    volume = fields.Float("Volume", help="The volume in m3.")
    length = fields.Float(string="Length", required=False)
    width = fields.Float(string="Width", required=False)
    height = fields.Float(string="Height", required=False)
    image = fields.Binary(string="Image", attachment=True,
                          help="This field holds the image used as image for the product, limited to 1024x1024px.")
    image_medium = fields.Binary(string="Medium-sized image", attachment=True,
                                 help="Medium-sized image of the product. It is automatically "
                                      "resized as a 128x128px image, with aspect ratio preserved, "
                                      "only when the image exceeds one of those sizes. Use this field in form views "
                                      "or some kanban views.")
    image_small = fields.Binary(string="Small-sized image", attachment=True,
                                help="Small-sized image of the product. It is automatically "
                                     "resized as a 64x64px image, with aspect ratio preserved. "
                                     "Use this field anywhere a small image is required.")
    mp_product_image_ids = fields.One2many(comodel_name="mp.product.image", inverse_name="mp_product_id",
                                           string="Marketplace Product Images")
    mp_product_variant_ids = fields.One2many(comodel_name="mp.product.variant", inverse_name="mp_product_id",
                                             string="Marketplace Product Variant")

    @api.model
    def create(self, values):
        tools.image_resize_images(values)
        mp_product = super(MarketplaceProduct, self).create(values)
        if mp_product.mp_product_image_ids:
            mp_product_image = mp_product.get_main_image()
            mp_product.write({'image': mp_product_image.image})
        return mp_product

    @api.multi
    def write(self, values):
        tools.image_resize_images(values)
        res = super(MarketplaceProduct, self).write(values)
        for mp_product in self:
            if mp_product.mp_product_image_ids:
                mp_product_image = mp_product.get_main_image()
                if mp_product_image.id != self._context.get('latest_mp_product_image_id'):
                    mp_product.with_context({'latest_mp_product_image_id': mp_product_image.id}).write(
                        {'image': mp_product_image.image})
            else:
                if not self._context.get('mp_product_image_id_cleaned'):
                    mp_product.with_context({'mp_product_image_id_cleaned': True}).write({'image': False})
        return res

    @api.onchange('mp_product_image_ids')
    def onchange_mp_product_image_ids(self):
        if self.mp_product_image_ids:
            mp_product_image = self.mp_product_image_ids.filtered(lambda s: not isinstance(s.id, int))
            if mp_product_image.exists():
                mp_product_image.sequence -= len(self.mp_product_image_ids)

    @api.multi
    def get_main_image(self):
        self.ensure_one()
        return self.mp_product_image_ids.sorted('sequence')[0]
