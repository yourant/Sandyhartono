# -*- coding: utf-8 -*-
# from odoo import http


# class JuraganFastprint(http.Controller):
#     @http.route('/juragan_fastprint/juragan_fastprint/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/juragan_fastprint/juragan_fastprint/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('juragan_fastprint.listing', {
#             'root': '/juragan_fastprint/juragan_fastprint',
#             'objects': http.request.env['juragan_fastprint.juragan_fastprint'].search([]),
#         })

#     @http.route('/juragan_fastprint/juragan_fastprint/objects/<model("juragan_fastprint.juragan_fastprint"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('juragan_fastprint.object', {
#             'object': obj
#         })
