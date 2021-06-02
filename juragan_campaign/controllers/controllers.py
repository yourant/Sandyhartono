# -*- coding: utf-8 -*-
# from odoo import http


# class JuraganCampaign(http.Controller):
#     @http.route('/juragan_campaign/juragan_campaign/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/juragan_campaign/juragan_campaign/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('juragan_campaign.listing', {
#             'root': '/juragan_campaign/juragan_campaign',
#             'objects': http.request.env['juragan_campaign.juragan_campaign'].search([]),
#         })

#     @http.route('/juragan_campaign/juragan_campaign/objects/<model("juragan_campaign.juragan_campaign"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('juragan_campaign.object', {
#             'object': obj
#         })
