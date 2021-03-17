from odoo import models, fields


class ProductBrand(models.Model):
    _name = 'product.brand'
    _description = 'Product Brand'

    name = fields.Char()
    active = fields.Boolean(default=True)
    name_en = fields.Char()
    global_identifier = fields.Char()

    izi_id = fields.Integer('Izi ID')
    izi_md5 = fields.Char()
