# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import json

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.izi_tokopedia.objects.utils.tokopedia.tools import json_digger


class MarketplaceBase(models.AbstractModel):
    _name = 'mp.base'
    _description = 'Marketplace Base Model'
    _rec_mp_external_id = None
    _rec_mp_field_mapping = {}

    mp_account_id = fields.Many2one(comodel_name="mp.account", string="Marketplace Account", required=True)
    marketplace = fields.Selection(related="mp_account_id.marketplace", readonly=True)
    raw = fields.Text(string="Raw Data", readonly=True, required=True, default="{}")
    mp_external_id = fields.Char(string="Marketplace External ID", compute="_compute_mp_external_id")

    @classmethod
    def _build_model_attributes(cls, pool):
        super(MarketplaceBase, cls)._build_model_attributes(pool)
        cls._validate_rec_mp_field_mapping()

    @classmethod
    def _validate_rec_mp_field_mapping(cls):
        """You can add validation for _rec_mp_field_mapping here!"""
        pass

    @api.model
    def _get_rec_mp_field_mapping(self, marketplace):
        return self._rec_mp_field_mapping.get(marketplace, None)

    @api.multi
    def _compute_mp_external_id(self):
        for rec in self:
            mp_external_id = False
            if isinstance(rec._rec_mp_external_id, str):
                mp_external_id = getattr(rec, rec._rec_mp_external_id, False)
            elif isinstance(rec._rec_mp_external_id, dict):
                mp_external_id = getattr(rec, rec._rec_mp_external_id.get(rec.marketplace), False)
            if mp_external_id:
                mp_external_id = str(mp_external_id)
            rec.mp_external_id = mp_external_id

    @api.model
    def _get_mp_raw_fields(self, marketplace=None):
        mp_field_mapping = None
        if marketplace:
            mp_field_mapping = self._get_rec_mp_field_mapping(marketplace)

        raw_data_fields = []
        for field_name, field in self._fields.items():
            if getattr(field, 'mp_raw', False):
                raw_data_fields.append((field_name, getattr(field, 'mp_raw_handler', None)))

            if mp_field_mapping and field_name in mp_field_mapping:
                raw_data_fields.append((field_name, mp_field_mapping[field_name][1]))
        return raw_data_fields

    @api.model
    def mapping_raw_data(self, raw_data=None, sanitized_data=None, values=None):
        """Please inherit this method for each marketplace data model to define data handling method!"""

        mp_account_obj = self.env['mp.account']

        if not isinstance(sanitized_data, dict):
            raise ValidationError(
                "raw_data should be in dictionary format! You may need iteration to handling multiple data.")

        context = self._context
        if not context.get('mp_account_id'):
            raise ValidationError("Please define mp_account_id in context!")

        mp_account = mp_account_obj.browse(context.get('mp_account_id'))

        if not sanitized_data:
            sanitized_data = {}

        if not values:
            values = {}

        raw_data_fields = self._get_mp_raw_fields(mp_account.marketplace)
        for raw_data_field in raw_data_fields:
            field_name, mp_raw_handler = raw_data_field
            if not mp_raw_handler:
                values[field_name] = sanitized_data[field_name]
                continue
            values[field_name] = mp_raw_handler(sanitized_data[field_name])

        values.update({
            'mp_account_id': mp_account.id,
            'raw': self.format_raw_data(raw_data)
        })

        return sanitized_data, values

    @api.model
    def format_raw_data(self, raw, indent=4):
        return json.dumps(raw, indent=indent)

    @api.model
    def remap_raw_data(self, raw):
        datas = []
        # check if all values are list object
        is_list_values = [isinstance(values, list) for values in list(raw.values())]
        if all(is_list_values):
            # check if all length of list are equal
            if len(list(set([len(values) for values in list(raw.values())]))) == 1:
                list_length = list(set([len(values) for values in list(raw.values())]))[0]
                list_values = [values for values in list(raw.values())]
                for value_index in range(0, list_length):
                    data = {}
                    for key_index, key in enumerate(raw.keys()):
                        data.update({
                            key: list_values[key_index][value_index]
                        })
                    datas.append(data)
            return datas
        else:
            return raw

    @api.model
    def get_default_sanitizer(self, mp_field_mapping, root_path=None):
        def sanitize(response):
            response_data = response.json()
            if root_path:
                response_data = response_data[root_path]
            if mp_field_mapping:
                keys = mp_field_mapping.keys()
                mp_data = dict((key, json_digger(response_data, mp_field_mapping[key][0])) for key in keys)
                return response_data, self.remap_raw_data(mp_data)
            else:
                return response_data, None
        return sanitize

    @api.model
    def get_sanitizers(self, marketplace):
        mp_field_mapping = self._get_rec_mp_field_mapping(marketplace)

        if hasattr(self, '%s_get_sanitizers' % marketplace):
            return getattr(self, '%s_get_sanitizers' % marketplace)(mp_field_mapping)
        return {}

    @api.model
    def create_records(self, raw_data, mp_data, multi=False):
        record_obj = self.env[self._name]

        if multi:
            mp_datas = mp_data
            records = record_obj

            for mp_data in mp_datas:
                records |= self.create_records(raw_data, mp_data)

            return records

        raw_data, values = self.mapping_raw_data(raw_data=raw_data, sanitized_data=mp_data)
        return record_obj.create(values)
