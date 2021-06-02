# -*- coding: utf-8 -*-
from base64 import b64decode

from odoo import http
from odoo.http import request
from odoo.modules import get_resource_path
from odoo.tools import file_open, mimetypes


class FCM(http.Controller):
    @http.route('/fcm_config', type="json", auth='user')
    def get_fcm_config(self):
        res_config_settings = request.env['res.config.settings'].sudo()
        return res_config_settings.get_fcm_config()

    @http.route(['/fcm_icon'], type='http', auth="public")
    def icon(self):
        company = request.env.user.company_id
        if company.fcm_icon:
            icon = b64decode(company.fcm_icon)
        else:
            icon = file_open(get_resource_path('juragan_fcm_notify', 'static/description/icon.png'), 'rb').read()
        icon_mime = mimetypes.guess_mimetype(icon)
        return request.make_response(icon, headers={'Content-Type': icon_mime})

    @http.route(['/firebase-messaging-sw.js'], type='http', auth="public")
    def robots(self):
        res_config_settings = request.env['res.config.settings'].sudo()
        fcm_config = res_config_settings.get_fcm_config()
        qcontext = {'config': fcm_config}
        return request.render('juragan_fcm_notify.firebase_messaging_sw', qcontext, mimetype='text/javascript')
