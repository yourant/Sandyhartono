# -*- coding: utf-8 -*-
from odoo import http

# class JuraganPricelistDatetime(http.Controller):
#     @http.route('/juragan_pricelist_datetime/juragan_pricelist_datetime/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/juragan_pricelist_datetime/juragan_pricelist_datetime/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('juragan_pricelist_datetime.listing', {
#             'root': '/juragan_pricelist_datetime/juragan_pricelist_datetime',
#             'objects': http.request.env['juragan_pricelist_datetime.juragan_pricelist_datetime'].search([]),
#         })

#     @http.route('/juragan_pricelist_datetime/juragan_pricelist_datetime/objects/<model("juragan_pricelist_datetime.juragan_pricelist_datetime"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('juragan_pricelist_datetime.object', {
#             'object': obj
#         })