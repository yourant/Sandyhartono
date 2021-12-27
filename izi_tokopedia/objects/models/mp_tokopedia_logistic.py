# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import json

from odoo import api, fields, models


class MPTokopediaLogistic(models.Model):
    _name = 'mp.tokopedia.logistic'
    _inherit = 'mp.base'
    _description = "Marketplace Tokopedia Logistic"
    _rec_name = 'shipper_name'

    shipper_id = fields.Char(string="Shipper ID", readonly=True)
    shipper_name = fields.Char(string="Shipper Name", readonly=True)
    logo = fields.Char(string="Logo", readonly=True)
    service_ids = fields.One2many(comodel_name="mp.tokopedia.logistic.service", inverse_name="logistic_id",
                                  string="Services")
    product_id = fields.Many2one(comodel_name="product.product", string="Delivery Product", required=False,
                                 default=lambda self: self._get_default_product_id())

    @classmethod
    def _add_rec_mp_field_mapping(cls, mp_field_mappings=None):
        if not mp_field_mappings:
            mp_field_mappings = []

        marketplace = 'tokopedia'
        mp_field_mapping = {
            'mp_external_id': ('shipper_id', lambda env, r: str(r)),
            'shipper_id': ('shipper_id', lambda env, r: str(r)),
            'shipper_name': ('shipper_name', None),
            'logo': ('logo', None),
            'services': ('services', None)
        }

        mp_field_mappings.append((marketplace, mp_field_mapping))
        super(MPTokopediaLogistic, cls)._add_rec_mp_field_mapping(mp_field_mappings)

    @api.model
    def _get_default_product_id(self):
        mp_delivery_product_tmpl = self.env.ref('izi_marketplace.product_tmpl_mp_delivery', raise_if_not_found=False)
        if mp_delivery_product_tmpl:
            return mp_delivery_product_tmpl.product_variant_id.id
        return False

    @api.model
    def tokopedia_get_sanitizers(self, mp_field_mapping):
        default_sanitizer = self.get_default_sanitizer(mp_field_mapping, root_path='data')
        return {
            'logistic_info': default_sanitizer
        }

    @api.model
    def _finish_create_records(self, records):
        mp_tokopedia_logistic_service_obj = self.env['mp.tokopedia.logistic.service']

        mp_account = self.get_mp_account_from_context()
        mp_account_ctx = mp_account.generate_context().copy()

        records = super(MPTokopediaLogistic, self)._finish_create_records(records)
        tp_logistic_service_raws = []
        tp_logistic_service_sanitizeds = []

        for record in records:
            tp_logistic_raw = json.loads(record.raw, strict=False)
            tp_logistic_services = [dict(tp_logistic_service, **dict([('logistic_id', record.id)])) for
                                    tp_logistic_service in tp_logistic_raw['services']]
            tp_data_raw, tp_data_sanitized = mp_tokopedia_logistic_service_obj._prepare_mapping_raw_data(
                raw_data=tp_logistic_services)
            tp_logistic_service_raws.extend(tp_data_raw)
            tp_logistic_service_sanitizeds.extend(tp_data_sanitized)

        check_existing_records_params = {
            'identifier_field': 'service_id',
            'raw_data': tp_logistic_service_raws,
            'mp_data': tp_logistic_service_sanitizeds,
            'multi': isinstance(tp_logistic_service_sanitizeds, list)
        }
        check_existing_records = mp_tokopedia_logistic_service_obj.with_context(
            mp_account_ctx).check_existing_records(**check_existing_records_params)
        mp_tokopedia_logistic_service_obj.with_context(mp_account_ctx).handle_result_check_existing_records(
            check_existing_records)

        return records

    @api.model
    def _finish_update_records(self, records):
        records = super(MPTokopediaLogistic, self)._finish_update_records(records)
        self._finish_create_records(records)
        return records


class MPTokopediaLogisticService(models.Model):
    _name = 'mp.tokopedia.logistic.service'
    _inherit = 'mp.base'
    _description = 'Marketplace Tokopedia Logistic Service'
    _rec_name = 'service_name'

    MP_DELIVERY_TYPES = [
        ('pickup', 'Pickup'),
        ('drop off', 'Drop Off'),
        ('both', 'Pickup & Drop Off'),
        ('send_to_warehouse', 'Send to Warehouse')
    ]

    logistic_id = fields.Many2one(comodel_name="mp.tokopedia.logistic", string="Logistic", required=True,
                                  ondelete="restrict")
    service_id = fields.Char(string="Service ID", readonly=True)
    service_name = fields.Char(string="Service Name", readonly=True)
    service_desc = fields.Char(string="Service Description", readonly=True)
    delivery_type = fields.Selection(string="Delivery Type", readonly=True, selection=MP_DELIVERY_TYPES)
    product_id = fields.Many2one(comodel_name="product.product", string="Delivery Product", required=False)

    @classmethod
    def _add_rec_mp_field_mapping(cls, mp_field_mappings=None):
        if not mp_field_mappings:
            mp_field_mappings = []

        marketplace = 'tokopedia'
        mp_field_mapping = {
            'logistic_id': ('logistic_id', None),
            'mp_external_id': ('service_id', lambda env, r: str(r)),
            'service_id': ('service_id', lambda env, r: str(r)),
            'service_name': ('service_name', None),
            'service_desc': ('service_desc', None),
            'delivery_type': ('type_name', None)
        }

        mp_field_mappings.append((marketplace, mp_field_mapping))
        super(MPTokopediaLogisticService, cls)._add_rec_mp_field_mapping(mp_field_mappings)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        context = self._context
        domain = ['&', ('logistic_id', '=', context.get('logistic_id'))] + domain
        return super(MPTokopediaLogisticService, self).search_read(domain, fields, offset, limit, order)

    # @api.multi
    def get_delivery_product(self):
        self.ensure_one()
        if self.product_id:
            return self.product_id
        if self.logistic_id.product_id:
            return self.logistic_id.product_id
        return self.env['product.product']
