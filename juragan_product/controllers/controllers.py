# -*- coding: utf-8 -*-
from odoo import http

# class JuraganProduct(http.Controller):
#     @http.route('/juragan_product/juragan_product/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/juragan_product/juragan_product/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('juragan_product.listing', {
#             'root': '/juragan_product/juragan_product',
#             'objects': http.request.env['juragan_product.juragan_product'].search([]),
#         })

#     @http.route('/juragan_product/juragan_product/objects/<model("juragan_product.juragan_product"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('juragan_product.object', {
#             'object': obj
#         })