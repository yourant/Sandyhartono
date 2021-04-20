# -*- coding: utf-8 -*-
from odoo import models, fields


class MPLazada(models.Model):
    _name = 'mp.lazada'
    _description = 'Shopee Account'

    name = fields.Char(readonly=True, )
    active = fields.Boolean()

    izi_id = fields.Integer('Izi ID')
    izi_md5 = fields.Char()
