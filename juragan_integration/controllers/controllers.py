# -*- coding: utf-8 -*-
from odoo import http

# class JuraganIntegration(http.Controller):
#     @http.route('/juragan_integration/juragan_integration/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/juragan_integration/juragan_integration/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('juragan_integration.listing', {
#             'root': '/juragan_integration/juragan_integration',
#             'objects': http.request.env['juragan_integration.juragan_integration'].search([]),
#         })

#     @http.route('/juragan_integration/juragan_integration/objects/<model("juragan_integration.juragan_integration"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('juragan_integration.object', {
#             'object': obj
#         })