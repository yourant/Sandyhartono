# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import hashlib
import json
import logging

from odoo import api, fields, models, sql_db
from odoo.exceptions import ValidationError

from odoo.addons.izi_marketplace.objects.utils.tools import json_digger, StringIteratorIO, clean_csv_value


class MarketplaceBase(models.AbstractModel):
    _name = 'mp.base'
    _description = 'Marketplace Base Model'
    _rec_mp_external_id = None
    _rec_mp_field_mapping = {}

    @api.multi
    def _check_required_if_marketplace(self):
        """ If the field has 'required_if_marketplace="<marketplace>"' attribute, then it
        required if record.marketplace is <marketplace>. """
        empty_field = []
        for record in self:
            for k, f in record._fields.items():
                if getattr(f, 'required_if_marketplace', None) == record.marketplace and not record[k]:
                    empty_field.append(self.env['ir.model.fields'].search(
                        [('name', '=', k), ('model', '=', record._name)]).field_description)
        if empty_field:
            raise ValidationError(', '.join(empty_field))
        return True

    _constraints = [
        (_check_required_if_marketplace, 'Required fields not filled', []),
    ]

    mp_account_id = fields.Many2one(comodel_name="mp.account", string="Marketplace Account", required=True)
    marketplace = fields.Selection(string="Marketplace", readonly=True,
                                   selection=lambda env: env['mp.account']._fields.get('marketplace').selection,
                                   related="mp_account_id.marketplace", store=True)
    raw = fields.Text(string="Raw Data", readonly=True, required=True, default="{}")
    signature = fields.Char(string="Signature", readonly=True, required=False, default="",
                            help="MD5 hash of the marketplace data.")
    mp_external_id = fields.Char(string="Marketplace External ID", compute="_compute_mp_external_id")

    @classmethod
    def _build_model_attributes(cls, pool):
        super(MarketplaceBase, cls)._build_model_attributes(pool)
        cls._add_rec_mp_external_id()
        cls._add_rec_mp_field_mapping()
        cls._validate_rec_mp_field_mapping()

    @classmethod
    def _add_rec_mp_external_id(cls, mp_external_id_fields=None):
        if mp_external_id_fields:
            if not cls._rec_mp_external_id:
                cls._rec_mp_external_id = {}
            cls._rec_mp_external_id = dict(cls._rec_mp_external_id, **dict(mp_external_id_fields))

    @classmethod
    def _add_rec_mp_field_mapping(cls, mp_field_mappings=None):
        if mp_field_mappings:
            cls._rec_mp_field_mapping = dict(cls._rec_mp_field_mapping, **dict(mp_field_mappings))

    @classmethod
    def _validate_rec_mp_field_mapping(cls):
        """You can add validation for _rec_mp_field_mapping here!"""
        pass

    @api.model
    def _create_new_env(self):
        new_cr = sql_db.db_connect(self.env.cr.dbname).cursor()
        uid, context = self.env.uid, self.env.context
        new_env = api.Environment(new_cr, uid, context)
        return new_env

    @api.model
    def _notify(self, notif_type, message, title=None, notif_sticky=False):
        notif_env = self._create_new_env()
        getattr(notif_env.user, 'notify_%s' % notif_type)(message, title=title, sticky=notif_sticky)
        notif_env.cr.commit()
        notif_env.cr.close()

    @api.model
    def _logger(self, marketplace, message, level="info", notify=False, notif_type="info", notif_sticky=False):
        logger = logging.getLogger(__name__)

        log_message = "[%s] %s" % (marketplace.upper(), message)

        getattr(logger, level)(log_message)

        if notify:
            self._notify(notif_type, message, notif_sticky=notif_sticky)

    @api.model
    def log_skip(self, marketplace, need_skip_records, notify=False, notif_type="info", notif_sticky=False):
        num_skip = len(need_skip_records)
        log_message = "Skipping {num_skip} existing  record(s) of {model}"
        self._logger(marketplace, log_message.format(**{'num_skip': num_skip, 'model': self._name}), notify=notify,
                     notif_type=notif_type, notif_sticky=notif_sticky)

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
                mp_external_id = getattr(rec, rec._rec_mp_external_id.get(rec.marketplace, ''), False)
            if mp_external_id:
                mp_external_id = str(mp_external_id)
            rec.mp_external_id = mp_external_id

    @api.model
    def _field_lookup_mp_external_id(self, marketplace):
        if isinstance(self._rec_mp_external_id, str):
            return self._rec_mp_external_id
        elif isinstance(self._rec_mp_external_id, dict):
            return self._rec_mp_external_id.get(marketplace)

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
    def get_mp_account_from_context(self):
        mp_account_obj = self.env['mp.account']

        context = self._context
        if not context.get('mp_account_id'):
            raise ValidationError("Please define mp_account_id in context!")

        return mp_account_obj.browse(context.get('mp_account_id'))

    @api.model
    def get_mp_partner(self, mp_account, values):
        res_partner_obj = self.env['res.partner']

        partner = False
        shipping_address = False

        if mp_account.partner_id:
            partner = mp_account.partner_id
            if values.get('mp_recipient_address_phone'):
                shipping_address = res_partner_obj.sudo().search(
                    [('parent_id', '=', partner.id), ('phone', '=', values.get('mp_recipient_address_phone'))], limit=1)

        else:
            if not partner and values.get('mp_recipient_address_phone'):
                partner = res_partner_obj.sudo().search(
                    [('phone', '=', values.get('mp_recipient_address_phone')),
                     ('type', '=', 'delivery')], limit=1)

            if not partner:
                partner = res_partner_obj.sudo().search(
                    [('phone', '=', values.get('mp_recipient_address_phone')),
                     ('type', '=', 'contact')], limit=1)
            else:
                partner = partner.parent_id
                shipping_address = partner

            if not partner:
                partner = self.env['res.partner'].sudo().create({
                    'name': values.get('mp_recipient_address_name'),
                    'phone': values.get('mp_recipient_address_phone'),
                })

        if not shipping_address:
            shipping_address = self.env['res.partner'].sudo().create({
                'type': 'delivery',
                'parent_id': partner.id,
                'phone': values.get('mp_recipient_address_phone'),
                'name': values.get('mp_recipient_address_name'),
                'street': values.get('mp_recipient_address_full'),
                'city': values.get('mp_recipient_address_city'),
                'street2': values.get('mp_recipient_address_district', '') + ' ' +
                values.get('mp_recipient_address_city', '') + ' ' +
                values.get('mp_recipient_address_state', '') + ' ' +
                values.get('mp_recipient_address_country', ''),
                'zip': values.get('mp_recipient_address_zipcode'),
            })
        else:
            shipping_address.sudo().write({
                'name': values.get('mp_recipient_address_name'),
                'street': values.get('mp_recipient_address_full'),
                'city': values.get('mp_recipient_address_city'),
                'street2': values.get('mp_recipient_address_district', '') + ' ' +
                values.get('mp_recipient_address_city', '') + ' ' +
                values.get('mp_recipient_address_state', '') + ' ' +
                values.get('mp_recipient_address_country', ''),
                'zip': values.get('mp_recipient_address_zipcode'),
                'type': 'delivery',
            })

        return partner, shipping_address

    @api.model
    def _prepare_mapping_raw_data(self, response=None, raw_data=None, sanitizer=None, endpoint_key=None):
        if response:
            raw_data = response.json()

        mp_account = self.get_mp_account_from_context()
        marketplace = mp_account.marketplace

        mp_field_mapping = self._get_rec_mp_field_mapping(marketplace)
        if not sanitizer:
            if endpoint_key:
                sanitizer = self.get_sanitizers(marketplace).get(endpoint_key)
            if not sanitizer:
                sanitizer = self.get_default_sanitizer(mp_field_mapping)
        return sanitizer(raw_data=raw_data)  # return (raw_data, sanitized_data)

    @api.model
    def mapping_raw_data(self, raw_data=None, sanitized_data=None, values=None):
        """Please inherit this method for each marketplace data model to define data handling method!"""

        mp_account_obj = self.env['mp.account']

        if not isinstance(sanitized_data, dict):
            raise ValidationError(
                "sanitized_data should be in dictionary format! You may need iteration to handling multiple data.")

        context = self._context
        if not context.get('mp_account_id'):
            raise ValidationError("Please define mp_account_id in context!")

        mp_account = mp_account_obj.browse(context.get('mp_account_id'))

        if not raw_data:
            raw_data = {}

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
            values[field_name] = mp_raw_handler(self.env, sanitized_data[field_name])

        values.update({
            'mp_account_id': mp_account.id,
            'raw': self.format_raw_data(raw_data),
            'signature': self.generate_signature(sanitized_data)
        })

        return self.with_context(context)._finish_mapping_raw_data(sanitized_data, values)

    @api.model
    def _finish_mapping_raw_data(self, sanitized_data, values):
        return sanitized_data, values

    @api.model
    def _run_mapping_raw_data(self, raw_data=None, sanitized_data=None, multi=False):
        context = self._context.copy()
        if multi:
            raw_datas = raw_data
            sanitized_datas = sanitized_data
            values_list = []

            for index, sanitized_data in enumerate(sanitized_datas):
                context['index'] = index
                sanitized_data, values = self.with_context(context)._run_mapping_raw_data(raw_data=raw_datas[index],
                                                                                          sanitized_data=sanitized_data)
                values_list.append(values)

            return sanitized_datas, values_list
        sanitized_data, values = self.mapping_raw_data(raw_data, sanitized_data)
        return sanitized_data, values

    @api.model
    def format_raw_data(self, raw, indent=4):
        return json.dumps(raw, indent=indent)

    @api.model
    def generate_signature(self, raw):
        return hashlib.md5(json.dumps(raw).encode()).hexdigest()

    @api.model
    def enable_currencies(self, xml_ids):
        for xml_id in xml_ids:
            currency = self.env.ref(xml_id)
            currency.write({'active': True})

    @api.model
    def enable_group_technical_features(self, xml_ids):
        insert_implied_groups = [(4, self.env.ref(xml_id).id) for xml_id in xml_ids]
        self.env.ref('base.group_user').write({'implied_ids': insert_implied_groups})

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
        def sanitize(response=None, raw_data=None):
            if response:
                raw_data = response.json()
            if root_path:
                raw_data = raw_data[root_path]
            if mp_field_mapping:
                keys = mp_field_mapping.keys()
                mp_data = dict((key, json_digger(raw_data, mp_field_mapping[key][0])) for key in keys)
                # return: (raw_data, sanitized_data)
                return raw_data, self.remap_raw_data(mp_data)
            else:
                # return: (raw_data, None)
                return raw_data, None

        return sanitize

    @api.model
    def get_sanitizers(self, marketplace):
        mp_field_mapping = self._get_rec_mp_field_mapping(marketplace)

        if hasattr(self, '%s_get_sanitizers' % marketplace):
            return getattr(self, '%s_get_sanitizers' % marketplace)(mp_field_mapping)
        return {}

    @api.model
    def search_mp_records(self, marketplace, mp_external_id, operator="="):
        mp_external_id_field = self._field_lookup_mp_external_id(marketplace)
        return self.search([(mp_external_id_field, operator, mp_external_id)])

    @api.model
    def check_existing_records(self, identifier_field, raw_data, mp_data, multi=False):
        mp_account_obj = self.env['mp.account']
        record_obj = self.env[self._name]

        context = self._context.copy()
        if not context.get('mp_account_id'):
            raise ValidationError("Please define mp_account_id in context!")

        mp_account = mp_account_obj.browse(context.get('mp_account_id'))
        marketplace = mp_account.marketplace

        log_msg_updating = "{model}: ({num}) Found existing record with ID {rec_id} is need to be updated: {rec_name}"
        log_msg_skipping = "{model}: ({num}) Found existing record with ID {rec_id} is need to be skipped: {rec_name}"
        log_msg_creating = "{model}: ({num}) Found data need to be created!"

        if multi:
            raw_datas = raw_data
            mp_datas = mp_data
            check_existing_records = {
                'need_update_records': [],
                'need_create_records': [],
                'need_skip_records': []
            }

            self._logger(marketplace, "Looking for existing records of %s is started... Please wait!" % self._name,
                         notify=True, notif_sticky=True)

            for index, mp_data in enumerate(mp_datas):
                context['index'] = index
                existing_record = self.with_context(context).check_existing_records(identifier_field, raw_datas[index],
                                                                                    mp_data)
                for key in existing_record.keys():
                    check_existing_records[key].append(existing_record[key])

            log_msg_data = {
                'log_msg': '%s: {num} record(s) need to be {action}!' % self._name,
                'need_update': {
                    'num': len(check_existing_records['need_update_records']),
                    'action': 'updated'
                },
                'need_create': {
                    'num': len(check_existing_records['need_create_records']),
                    'action': 'created'
                },
                'need_skip': {
                    'num': len(check_existing_records['need_skip_records']),
                    'action': 'skipped'
                },
            }
            self._logger(marketplace, "Looking for existing records of %s is finished!" % self._name, notify=True,
                         notif_sticky=True)
            self._logger(marketplace, log_msg_data['log_msg'].format(**log_msg_data['need_update']), notify=True,
                         notif_sticky=True)
            self._logger(marketplace, log_msg_data['log_msg'].format(**log_msg_data['need_create']), notify=True,
                         notif_sticky=True)
            self._logger(marketplace, log_msg_data['log_msg'].format(**log_msg_data['need_skip']), notify=True,
                         notif_sticky=True)
            return check_existing_records

        sanitized_data, values = self.mapping_raw_data(raw_data=raw_data, sanitized_data=mp_data)
        mp_external_id_field = self._field_lookup_mp_external_id(marketplace)
        record = record_obj.search([(mp_external_id_field, '=', values[identifier_field])])
        if record.exists():
            current_signature = self.generate_signature(sanitized_data)
            if current_signature != record.signature or context.get('force_update'):
                self._logger(marketplace, log_msg_updating.format(**{
                    'num': context.get('index', 0) + 1,
                    'model': self._name,
                    'rec_id': record.id,
                    'rec_name': record.display_name
                }))
                return {'need_update_records': (record, values, raw_data, sanitized_data)}
            if context.get('force_update_raw'):
                values = {'raw': values.get('raw')}
                return {'need_update_records': (record, values, raw_data, sanitized_data)}
            self._logger(marketplace, log_msg_skipping.format(**{
                'num': context.get('index', 0) + 1,
                'model': self._name,
                'rec_id': record.id,
                'rec_name': record.display_name
            }))
            return {'need_skip_records': (record, {})}
        self._logger(marketplace, log_msg_creating.format(model=self._name, num=context.get('index', 0) + 1))
        return {'need_create_records': (raw_data, sanitized_data)}

    @api.model
    def handle_result_check_existing_records(self, result):
        mp_account_obj = self.env['mp.account']
        context = self._context.copy()
        if not context.get('mp_account_id'):
            raise ValidationError("Please define mp_account_id in context!")

        mp_account = mp_account_obj.browse(context.get('mp_account_id'))
        marketplace = mp_account.marketplace
        if 'need_update_records' in result and result['need_update_records']:
            self.with_context(context).update_records(result['need_update_records'])

        if 'need_create_records' in result and result['need_create_records']:
            mp_data_raw, mp_data_sanitized = self._prepare_create_records(result['need_create_records'])
            create_records_params = {
                'raw_data': mp_data_raw,
                'mp_data': mp_data_sanitized,
                'multi': isinstance(mp_data_sanitized, list)
            }
            self.with_context(context).create_records(**create_records_params)

        if 'need_skip_records' in result and result['need_skip_records']:
            self.log_skip(marketplace, result['need_skip_records'])

    @api.model
    def _prepare_create_records(self, need_create_records):
        if not isinstance(need_create_records, list):
            need_create_records = [need_create_records]
        raw_data = [need_create_record[0] for need_create_record in need_create_records]
        sanitized_data = [need_create_record[1] for need_create_record in need_create_records]
        return raw_data, sanitized_data

    @api.model
    def create_records(self, raw_data, mp_data, multi=False):
        mp_account_obj = self.env['mp.account']
        record_obj = self.env[self._name]

        context = self._context
        if not context.get('mp_account_id'):
            raise ValidationError("Please define mp_account_id in context!")

        mp_account = mp_account_obj.browse(context.get('mp_account_id'))
        marketplace = mp_account.marketplace

        log_message = "Creating {model} with ID {rec_id}: {rec_name}"

        if multi:
            raw_datas = raw_data
            mp_datas = mp_data
            records = record_obj
            self._logger(marketplace,
                         "Creating %d record(s) of %s started... Please wait!" % (len(mp_datas), record_obj._name),
                         notify=True, notif_sticky=True)

            for index, mp_data in enumerate(mp_datas):
                records |= self.create_records(raw_datas[index], mp_data)
                self._logger(marketplace,
                             "%s: Created %d of %d" % (record_obj._name, len(records), len(mp_datas)))

            return self.with_context(context)._finish_create_records(records)

        sanitized_data, values = self.mapping_raw_data(raw_data=raw_data, sanitized_data=mp_data)
        record = record_obj.create(values)
        self._logger(marketplace, log_message.format(**{
            'model': record_obj._name,
            'rec_id': record.id,
            'rec_name': record.display_name
        }))
        return record

    @api.model
    def _finish_create_records(self, records):
        return records

    @api.model
    def update_records(self, need_update_records):
        mp_account_obj = self.env['mp.account']
        record_obj = self.env[self._name]
        records = record_obj

        context = self._context
        if not context.get('mp_account_id'):
            raise ValidationError("Please define mp_account_id in context!")

        mp_account = mp_account_obj.browse(context.get('mp_account_id'))
        marketplace = mp_account.marketplace

        if not isinstance(need_update_records, list):
            need_update_records = [need_update_records]

        self._logger(marketplace, "Updating %d record(s) of %s started... Please wait!" % (
            len(need_update_records), record_obj._name), notify=True, notif_sticky=True)

        for need_update_record in need_update_records:
            record, values, raw_data, sanitized_data = need_update_record
            record.write(values)
            log_message = "Updating {model} with ID {rec_id}: {rec_name}"
            self._logger(marketplace, log_message.format(**{
                'model': record_obj._name,
                'rec_id': record.id,
                'rec_name': record.display_name
            }))
            records |= record
            self._logger(marketplace,
                         "%s: Updated %d of %d" % (record_obj._name, len(records), len(need_update_records)))
        return self.with_context(context)._finish_update_records(records)

    @api.model
    def _finish_update_records(self, records):
        return records

    @api.model
    def pg_select(self, table_name, columns, where=None, null_value=None):
        """Do SELECT query from database directly and return its result."""

        _sql = "SELECT %s FROM %s" % (",".join(columns), table_name)

        if where:
            _sql = "%s WHERE %s" % (_sql, where)

        self._cr.execute(_sql)
        results = self._cr.dictfetchall()
        for result in results:
            for field, value in result.items():
                if value == 'False':
                    result[field] = null_value
        return results

    @api.model
    def pg_copy_from(self, table_name, record_datas, null_value=None):
        """Convert list of dict to be CSV file-like object and then
         import it to DB using PostgreSQL COPY FROM feature.

         This is EXPERIMENTAL FEATURE, use it wisely!
         """

        for record_data in record_datas:
            for field, value in record_data.items():
                if not value:
                    record_data[field] = null_value

        # Prepare CSV file like object
        records_string_iterator = StringIteratorIO(
            ('|'.join(map(clean_csv_value, tuple(record_data.values()))) + '\n') for record_data in record_datas)

        # Import CSV file like object into DB
        self._cr._obj.copy_from(records_string_iterator, table_name, sep='|', columns=list(record_datas[0].keys()))

    @api.model
    def do_recompute(self, model, domain=None, records=None, skip_fields=None):
        if not skip_fields:
            skip_fields = []

        if not domain:
            domain = []

        if not records:
            records = model.search(domain)

        # Get compute fields of the model
        need_recompute_fields = []
        for fname, field in model._fields.items():
            if field.store and (field.compute or field.related) and fname not in skip_fields:
                need_recompute_fields.append(field)

        # Prepare to recompute
        for need_recompute_field in need_recompute_fields:
            records._recompute_todo(need_recompute_field)

        # Do recompute
        model.recompute()

        # Finish recompute
        for need_recompute_field in need_recompute_fields:
            records._recompute_done(need_recompute_field)