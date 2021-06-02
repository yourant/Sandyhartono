# -*- coding: utf-8 -*-
from odoo import http

# class JuraganProductCodeSequence(http.Controller):
#     @http.route('/juragan_product_code_sequence/juragan_product_code_sequence/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/juragan_product_code_sequence/juragan_product_code_sequence/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('juragan_product_code_sequence.listing', {
#             'root': '/juragan_product_code_sequence/juragan_product_code_sequence',
#             'objects': http.request.env['juragan_product_code_sequence.juragan_product_code_sequence'].search([]),
#         })

#     @http.route('/juragan_product_code_sequence/juragan_product_code_sequence/objects/<model("juragan_product_code_sequence.juragan_product_code_sequence"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('juragan_product_code_sequence.object', {
#             'object': obj
#         })