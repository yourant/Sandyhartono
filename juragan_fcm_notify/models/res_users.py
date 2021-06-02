# -*- coding: utf-8 -*-
import requests
from odoo import api, fields, models, _


class User(models.Model):
    _inherit = 'res.users'

    fcm_iid_token = fields.Char(string="IID Token", required=False)

    @api.model
    def fcm_get_config(self):
        res_config_settings = self.env['res.config.settings'].sudo()
        fcm_config = res_config_settings.get_fcm_config()
        return fcm_config

    @api.model
    def fcm_is_active(self):
        fcm_config = self.fcm_get_config()
        return fcm_config.get('fcm_active')

    @api.model
    def fcm_send(self, title, message, type_message, sticky=False):
        fcm_config = self.fcm_get_config()
        url = 'https://fcm.googleapis.com/fcm/send'
        payload = {
            "notification": {
                "title": title,
                "body": message,
                "icon": "fcm_icon"
            },
            "data": {
                "type": type_message,
                "sticky": sticky
            },
            "to": self.fcm_iid_token
        }
        headers = {
            'Authorization': 'key=%s' % fcm_config.get('fcm_server_key')
        }
        requests.post(url, json=payload, headers=headers)

    def fcm_notify_default(self, message, title=None, sticky=False):
        if self.fcm_is_active():
            for user in self:
                title = title or _('Default')
                user.fcm_send(title, message, "default", sticky)

    def fcm_notify_info(self, message, title=None, sticky=False):
        if self.fcm_is_active():
            for user in self:
                title = title or _('Information')
                user.fcm_send(title, message, "info", sticky)

    def fcm_notify_warning(self, message, title=None, sticky=False):
        if self.fcm_is_active():
            for user in self:
                title = title or _('Warning')
                user.fcm_send(title, message, "warning", sticky)

    def fcm_notify_success(self, message, title=None, sticky=False):
        if self.fcm_is_active():
            for user in self:
                title = title or _('Success')
                user.fcm_send(title, message, "success", sticky)

    def fcm_notify_danger(self, message, title=None, sticky=False):
        if self.fcm_is_active():
            for user in self:
                title = title or _('Danger')
                user.fcm_send(title, message, "danger", sticky)
