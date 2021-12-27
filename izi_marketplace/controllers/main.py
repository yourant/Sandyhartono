# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import http, SUPERUSER_ID


# class Notify(http.Controller):
#     @http.route('/log/notify', auth='none', csrf=False)
#     def notify(self, **kw):
#         http.request.uid = SUPERUSER_ID
#         user_id = http.request.env['res.users'].sudo().search([('id', '=', kw.get('user_id'))])
#         if kw.get('user_id'):
#             del kw['user_id']
#         notif_type = kw.get('notif_type', 'info')
#         if kw.get('notif_type'):
#             del kw['notif_type']
#         if user_id:
#             getattr(user_id, 'notify_%s' % (notif_type))(**kw)
