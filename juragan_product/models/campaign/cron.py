# -*- coding: utf-8 -*-
from odoo import api, fields, models


class Cron(models.Model):
    _inherit = 'ir.cron'

    campaign_id = fields.Many2one(comodel_name="juragan.campaign.job", string="Campaign", ondelete="cascade")
