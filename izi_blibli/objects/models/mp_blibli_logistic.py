# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models


class MPBlibliLogistic(models.Model):
    _name = 'mp.blibli.logistic'
    _inherit = 'mp.base'
    _description = 'Marketplace Blibli Logistic'
    _rec_mp_external_id = 'logistics_code'

    logistics_name = fields.Char(string="Logistic Name", readonly=True, mp_raw=True)
    info_additional = fields.Char(string="Additional Information", readonly=True, mp_raw=True)
    info_highlight = fields.Char(string="Highlight Information", readonly=True, mp_raw=True)
    is_selected = fields.Boolean(string='Enabled', readonly=True, mp_raw=True)
    geolocation = fields.Boolean(string='Geolocation', readonly=True)
    logistics_code = fields.Char(string="Logistic Code", readonly=True)

    @classmethod
    def _build_model_attributes(cls, pool):

        cls._rec_mp_field_mapping = dict(cls._rec_mp_field_mapping, **{
            'blibli': {
                'logistics_code': ('code', None),
                'logistics_name': ('name', None),
                'is_selected': ('selected', None),
                'geolocation': ('geolocation', None),
                'info_additional': ('information/additional', None),
                'info_highlight': ('information/highlighted', None),
            }
        })
        super(MPBlibliLogistic, cls)._build_model_attributes(pool)

    @ api.model
    def blibli_get_sanitizers(self, mp_field_mapping):
        default_sanitizer = self.get_default_sanitizer(mp_field_mapping, root_path='content')
        return {
            'logistic': default_sanitizer
        }
