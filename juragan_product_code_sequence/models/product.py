# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def create(self, values):
        company = self.env.user.company_id
        if not values.get('default_code'):
            if company.sequence_product_default_code:
                sequence_code = company.sequence_product_default_code.code
                values['default_code'] = self.env['ir.sequence'].sudo().next_by_code(sequence_code)
        return super(ProductTemplate, self).create(values)

    def write(self, values):
        company = self.env.user.company_id
        for product_tmpl in self:
            if not values.get('default_code'):
                if not product_tmpl.default_code:
                    if company.sequence_product_default_code:
                        sequence_code = company.sequence_product_default_code.code
                        values['default_code'] = self.env['ir.sequence'].sudo().next_by_code(sequence_code)
                else:
                    values['default_code'] = product_tmpl.default_code
        return super(ProductTemplate, self).write(values)
