# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    fcm_active = fields.Boolean(string="Enable Push Notification", default=False, config_parameter="fcm_active")
    fcm_api_key = fields.Char(string="apiKey", config_parameter="fcm_api_key")
    fcm_auth_domain = fields.Char(string="authDomain", config_parameter="fcm_auth_domain")
    fcm_project_id = fields.Char(string="projectId", config_parameter="fcm_project_id")
    fcm_storage_bucket = fields.Char(string="storageBucket", config_parameter="fcm_storage_bucket")
    fcm_messaging_sender_id = fields.Char(string="messagingSenderId", config_parameter="fcm_messaging_sender_id")
    fcm_app_id = fields.Char(string="appId", config_parameter="fcm_app_id")
    fcm_measurement_id = fields.Char(string="measurementId", config_parameter="fcm_measurement_id")
    fcm_vapid_key = fields.Char(string="vapidKey", config_parameter="fcm_vapid_key")
    fcm_server_key = fields.Char(string="serverKey", config_parameter="fcm_server_key")
    fcm_icon = fields.Binary(string="Icon", related="company_id.fcm_icon", readonly=False)

    @staticmethod
    def get_fcm_config_fields():
        return ['fcm_active', 'fcm_api_key', 'fcm_auth_domain', 'fcm_project_id', 'fcm_storage_bucket',
                'fcm_messaging_sender_id', 'fcm_app_id', 'fcm_measurement_id', 'fcm_vapid_key', 'fcm_server_key']

    def get_fcm_config(self):
        icp_sudo = self.env['ir.config_parameter'].sudo()
        res = {}
        for fcm_config_field in self.get_fcm_config_fields():
            if fcm_config_field == 'fcm_active':
                res.update({fcm_config_field: icp_sudo.get_param(fcm_config_field, 'False').lower() == 'true'})
                continue
            res.update({fcm_config_field: icp_sudo.get_param(fcm_config_field)})
        return res

    # def get_values(self):
    #     res = super(ResConfigSettings, self).get_values()
    #     res.update(self.get_fcm_config())
    #     return res
    #
    # def set_values(self):
    #     super(ResConfigSettings, self).set_values()
    #     icp_sudo = self.env['ir.config_parameter'].sudo()
    #     for fcm_config_field in self.get_fcm_config_fields():
    #         if fcm_config_field == 'fcm_active':
    #             icp_sudo.set_param(fcm_config_field, 1 if self.fcm_active else 0)
    #             continue
    #         icp_sudo.set_param(fcm_config_field, getattr(self, fcm_config_field))
