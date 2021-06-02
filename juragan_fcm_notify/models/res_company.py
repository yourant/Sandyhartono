# -*- coding: utf-8 -*-
from odoo import api, fields, models


class Company(models.Model):
    _inherit = 'res.company'

    fcm_icon = fields.Binary(string="FCM Icon")
