# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models

from odoo.addons import decimal_precision as dp


class MarketplaceProduct(models.Model):
    _name = 'mp.product'
    _inherit = 'mp.base'
    _description = 'Marketplace Product Representation'
    _rec_mp_external_id = {}

    name = fields.Char(string="Name", index=True, required=True)
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
