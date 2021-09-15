# -*- coding: utf-8 -*-
import itertools
import json
import logging
import operator
from datetime import datetime, timedelta
from pprint import pprint

import pytz
from odoo import api, fields, models
from odoo.addons.base.models.res_partner import _tz_get
from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT

_logger = logging.getLogger(__name__)


class JuraganCampaign(models.Model):
    _name = 'juragan.campaign'
    _description = 'Juragan Campaign'

    STATES = [
        ('draft', 'Planning'),
        ('done', 'Scheduled'),
        ('cancel', 'Canceled'),
    ]

    READONLY_STATES = {
        'done': [('readonly', True)],
        'cancel': [('readonly', True)],
    }

    CAMPAIGN_PURPOSE = [
        ('reguler', 'Reguler'),
        ('wholesale', 'Wholesale'),
    ]

    MP_TYPES = [
        ('mp.tokopedia', 'Tokopedia'),
        ('mp.shopee', 'Shopee'),
        ('mp.lazada', 'Lazada'),
    ]

    MP_ACCOUNT_FIELDS_PRODUCT_STAGINGS = {
        'mp.tokopedia': 'mp_tokopedia_id',
        'mp.shopee': 'mp_shopee_id',
        'mp.lazada': 'mp_lazada_id'
    }

    MODES = [
        ('set_datetime', 'Set Datetime'),
        ('set_weekday', 'Set Weekday'),
    ]

    def _get_default_currency_id(self):
        return self.env.user.company_id.currency_id.id

    name = fields.Char(string="Campaign Name", required=True, states=READONLY_STATES)
    currency_id = fields.Many2one("res.currency", "Currency", default=_get_default_currency_id, required=True,
                                  states=READONLY_STATES)
    company_id = fields.Many2one("res.company", "Company", states=READONLY_STATES)
    sequence = fields.Integer(default=16, states=READONLY_STATES)
    pricelist_id = fields.Many2one(comodel_name="product.pricelist", string="Target Pricelist", required=False,
                                   ondelete="cascade", states=READONLY_STATES)
    state = fields.Selection(STATES, string='Status', default='draft', required=True)
    pricelist_item_ids = fields.One2many("product.pricelist.item", "campaign_id", "Pricelist Items", copy=True,
                                         states=READONLY_STATES)
    campaign_purpose = fields.Selection(string="Campaign Purpose", selection=CAMPAIGN_PURPOSE,
                                        required=True)
    campaign_job_ids = fields.One2many(comodel_name="juragan.campaign.job", inverse_name="campaign_id",
                                       string="Campaign Jobs", required=False)
    campaign_job_count = fields.Integer(string="Campaign Jobs", compute="_compute_campaign_job_count")
    # TODO: Until we can handle the combination of set_datetime and set_weekday, this selection will still remain.
    set_mode = fields.Selection(string="Mode", selection=MODES, required=False, states=READONLY_STATES)
    set_datetime = fields.Boolean(string="Set Datetime?", states=READONLY_STATES)
    date_time_start = fields.Datetime(string="Start Datetime", states=READONLY_STATES)
    date_time_end = fields.Datetime(string="End Datetime", states=READONLY_STATES)
    set_weekday = fields.Boolean(string="Set Weekday?", states=READONLY_STATES)
    time_start = fields.Char(string="Start Time", default="00:00", states=READONLY_STATES)
    time_end = fields.Char(string="End Time", default="23:59", states=READONLY_STATES)
    weekday_tz = fields.Selection(_tz_get, string='Timezone', default=lambda self: self._context.get('tz'),
                                  states=READONLY_STATES)
    day_0 = fields.Boolean(string="Sunday", states=READONLY_STATES)
    day_1 = fields.Boolean(string="Monday", states=READONLY_STATES)
    day_2 = fields.Boolean(string="Tuesday", states=READONLY_STATES)
    day_3 = fields.Boolean(string="Wednesday", states=READONLY_STATES)
    day_4 = fields.Boolean(string="Thursday", states=READONLY_STATES)
    day_5 = fields.Boolean(string="Friday", states=READONLY_STATES)
    day_6 = fields.Boolean(string="Saturday", states=READONLY_STATES)

    @api.model
    def create(self, values):
        if not self.env.context.get('sync_discount'):
            self.check_start_end_datetime(values)
        return super(JuraganCampaign, self).create(values)

    def write(self, values):
        if not self.env.context.get('sync_discount'):
            self.check_start_end_datetime(values)
        return super(JuraganCampaign, self).write(values)

    def check_start_end_datetime(self, values):
        date_time_start = False
        date_time_end = False
        # check if date_time_start is set
        if 'date_time_start' in values:
            if type(values['date_time_start']) == str:
                date_time_start = datetime.strptime(values['date_time_start'], '%Y-%m-%d %H:%M:%S')
            else:
                date_time_start = values['date_time_start']
            # check if date_time_start at least 10 minutes more than now
            if date_time_start < datetime.today() + timedelta(minutes=10):
                raise ValidationError('You are only allowed to set Start Datetime at least 10 minutes more than current date time')
        # check if date_time_end is set
        if 'date_time_end' in values:
            if type(values['date_time_end']) == str:
                date_time_end = datetime.strptime(values['date_time_end'], '%Y-%m-%d %H:%M:%S')
            else:
                date_time_end = values['date_time_end']
            # check if difference between date_time_start and date_time_end at least 1 hour
            if date_time_end - timedelta(hours=1) < date_time_start:
                raise ValidationError('You are only allowed to set End Datetime at least 1 hour more than Start Datetime')


    @api.onchange('set_mode')
    def change_set_mode(self):
        self.set_datetime = self.set_mode == 'set_datetime'
        self.set_weekday = self.set_mode == 'set_weekday'

    @api.onchange('date_time_start')
    def change_date_time_start(self):
        if self.date_time_start:
            # check if date_time_start is less than current date
            if self.date_time_start < datetime.today().replace(hour=0, minute=0, second=0, microsecond=0):
                self.date_time_start = False
                return {
                    'warning': {
                        'title': 'Not Allowed',
                        'message': 'Set date at least today',
                    }
                }

    @api.onchange('date_time_end')
    def change_date_time_end(self):
        if self.date_time_end:
            # check if date_time_end is less than current date
            if self.date_time_end < datetime.today().replace(hour=0, minute=0, second=0, microsecond=0):
                self.date_time_end = False
                return {
                    'warning': {
                        'title': 'Not Allowed',
                        'message': 'Set date at least today',
                    }
                }

    def action_run(self):
        # TODO: Need validaton before run
        self.ensure_one()
        pricelist_obj = self.env['product.pricelist']
        campaign_job_obj = self.env['juragan.campaign.job']
        if not self.pricelist_item_ids:
            raise UserError("No price rules defined, please set campaign correctly!")
        values = {
            'state': 'done',
        }
        if not self.pricelist_id:
            values['pricelist_id'] = pricelist_obj.create({
                'name': self.name,
                'currency_id': self.currency_id.id,
                'company_id': self.company_id.id,
                'sequence': self.sequence
            }).id
        self.write(values)
        self.pricelist_item_ids.write({'pricelist_id': self.pricelist_id.id})
        campaign_job_obj.init_jobs(self)
        self.campaign_job_ids.setup()

    def action_draft(self):
        self.ensure_one()
        # Make sure to rollback all previous applied wholesale
        interval_end_jobs = self.campaign_job_ids.filtered(
            lambda j: j.execution_type == 'interval_end' and j.state == 'waiting')
        for job in interval_end_jobs:
            job.execute()
        if 'failed' in interval_end_jobs.mapped('state'):
            # self.env.cr.commit()
            raise UserError("Some jobs is failed, please check the campaign job list to review.")

        self.campaign_job_ids.unlink()
        self.pricelist_item_ids.write({'pricelist_id': False})
        self.write({'state': 'draft'})

    def action_cancel(self):
        self.ensure_one()
        if self.state != 'draft':
            self.action_draft()
        self.write({'state': 'cancel'})

    def open_wizard_campaign_reguler(self):
        self.ensure_one()
        action = self.env.ref('juragan_product.action_window_wizard_juragan_campaign_reguler').read()[0]
        context = json.loads(action['context'])
        context.update({
            'form_view_ref': 'juragan_ui.form_wizard_juragan_campaign_reguler',
            'default_campaign_id': self.id,
        })
        action['context'] = context
        return action

    # @api.multi
    def open_wizard_campaign_wholesale(self):
        self.ensure_one()
        action = self.env.ref('juragan_product.action_window_wizard_juragan_campaign_wholesale').read()[0]
        context = json.loads(action['context'])
        context.update({
            'form_view_ref': 'juragan_ui.form_wizard_juragan_campaign_wholesale',
            'default_campaign_id': self.id,
        })
        action['context'] = context
        return action

    # @api.multi
    def _compute_campaign_job_count(self):
        for campaign in self:
            campaign.campaign_job_count = len(campaign.campaign_job_ids)


class JuraganCampaignJob(models.Model):
    _name = 'juragan.campaign.job'
    _description = 'Juragan Campaign Job'
    _order = 'scheduled_at'

    STATES = [
        ('waiting', 'Waiting Execution'),
        ('done', 'Executed'),
        ('cancel', 'Canceled'),
        ('failed', 'Failed')
    ]

    # These execution type is only used as an indicator to decide what need to do next in your own custom method.
    EXEC_TYPE = [
        ('immediately', 'Immediately'),  # Indicating the job should be executed immediately.
        ('interval_start', 'Interval Start'),  # Indicating the job should be executed at the start of the interval.
        ('interval_end', 'Interval End'),  # Indicating the job should be executed at the end of the interval.
        ('continuously', 'Continuously')  # Indicating the job should be executed continuously
    ]

    MP_ACCOUNT_FIELDS_PRODUCT_STAGINGS = JuraganCampaign.MP_ACCOUNT_FIELDS_PRODUCT_STAGINGS

    campaign_id = fields.Many2one(comodel_name="juragan.campaign", string="Campaign", required=True, ondelete="cascade")
    campaign_purpose = fields.Selection(string="Campaign Purpose", selection=JuraganCampaign.CAMPAIGN_PURPOSE,
                                        required=True)
    name = fields.Char(string="Description", required=False)
    scheduled_at = fields.Datetime(string="Scheduled at", required=True)
    execution_type = fields.Selection(string="Execution Type", selection=EXEC_TYPE, required=True,
                                      default='immediately')
    state = fields.Selection(string="Status", selection=STATES, required=True, default="waiting")
    pricelist_item_ids = fields.Many2many(comodel_name="product.pricelist.item", string="Pricelist Items")
    cron_ids = fields.One2many(comodel_name="ir.cron", inverse_name="campaign_id", string="Cron Jobs",
                               context={'active_test': False})
    total_execution = fields.Integer(string="Total Execution", default=0)
    extra_context = fields.Text(string="Extra Context", default="{}")

    # @api.multi
    def _create_cron(self, name=False, interval_number=0, interval_type=False, nextcall=False, numbercall=False,
                     code=False):
        self.ensure_one()
        cron_obj = self.env['ir.cron']
        if not code:
            code = "job = model.browse(%s); job.execute()" % self.id
        return cron_obj.create({
            'name': 'Campaign %s: %s' % (self.campaign_id.name, name or self.name),
            'model_id': self.env.ref('juragan_product.model_juragan_campaign_job').id,
            'user_id': self.env.ref('base.user_root').id,
            'interval_number': interval_number,
            'interval_type': interval_type,
            'nextcall': nextcall or self.scheduled_at,
            'numbercall': numbercall or 1,
            'doall': True,
            'code': code
        })

    @api.model
    def init_jobs(self, campaign):
        pricelist_items = campaign.pricelist_item_ids

        for campaign_purpose in list(set(pricelist_items.mapped('campaign_purpose'))):
            common_values = {
                'campaign_id': campaign.id,
                'campaign_purpose': campaign_purpose
            }
            # Filter pricelist items based on campaign purpose
            items = pricelist_items.filtered(lambda pli: pli.campaign_purpose == campaign_purpose)

            if hasattr(self, '%s_init_job' % campaign_purpose):
                getattr(self, '%s_init_job' % campaign_purpose)(common_values, items)

    # @api.multi
    def setup(self, execute=False):
        for job in self:
            if hasattr(job, '%s_setup_job' % job.campaign_purpose):
                getattr(job, '%s_setup_job' % job.campaign_purpose)(execute)

    # @api.multi
    def execute(self):
        for job in self:
            if hasattr(job, '%s_execute_job' % job.campaign_purpose):
                getattr(job, '%s_execute_job' % job.campaign_purpose)()


class JuraganCampaignJobReguler(models.Model):
    _inherit = 'juragan.campaign.job'

    product_stg_price_ids = fields.One2many(comodel_name="product.staging.price", inverse_name="related_job_id",
                                            string="Product Staging Price", required=False)

    @api.model
    def reguler_init_job(self, common_values, items):
        # Filter pricelist items based on set_datetime parameter
        items_with_set_datetime = items.filtered(lambda pli: pli.set_datetime)
        items_with_set_weekday = items.filtered(lambda pli: pli.set_weekday)
        items_general = items - items_with_set_datetime - items_with_set_weekday

        # Items with set_datetime will generate jobs with 'interval start' type.
        # So in the method that will be executed first, you need to create another jobs with 'interval end' type.
        for date_time_start in list(set(items_with_set_datetime.mapped('date_time_start'))):
            self.create(dict(common_values, **{
                'execution_type': 'interval_start',
                'scheduled_at': date_time_start,
                'pricelist_item_ids': [(6, 0, items_with_set_datetime.filtered(
                    lambda pli: pli.date_time_start == date_time_start).ids)]
            }))

        # items_with_set_weekday will generate job to run continuously
        if items_with_set_weekday:
            self.create(dict(common_values, **{
                'execution_type': 'continuously',
                'scheduled_at': fields.Datetime.now(),
                'pricelist_item_ids': [(6, 0, items_with_set_weekday.ids)]
            }))

        # items_general will executed immediately
        if items_general:
            self.create(dict(common_values, **{
                'execution_type': 'immediately',
                'scheduled_at': fields.Datetime.now(),
                'pricelist_item_ids': [(6, 0, items_general.ids)]
            }))

    # @api.multi
    def reguler_setup_job(self, execute=False):
        for job in self:
            values = {}
            if job.execution_type == 'interval_start':
                values.update({
                    'name': "Apply temporary reguler rules."
                })
            elif job.execution_type == 'interval_end':
                values.update({
                    'name': "Roll back the temporary reguler rules to the initial price."
                })
            elif job.execution_type == 'continuously':
                values.update({
                    'name': "Making schedules for the nearest upcoming reguler rules that need to be applied."
                })
            elif job.execution_type == 'immediately':
                values.update({
                    'name': "Apply permanent reguler rules immediately",
                })
                execute = True

            if not execute:
                cron = job._create_cron(name=values.get('name'))
                values.update({'cron_ids': [(4, cron.id)]})
            else:
                job.execute()
            job.write(values)

    # @api.multi
    def _reset_reguler_rule(self):
        self.ensure_one()

        product_stg_obj = self.env['product.staging']

        data = {}
        initial_prices = self.product_stg_price_ids
        product_stgs = product_stg_obj
        if initial_prices:
            _logger.info(
                "Restoring initial price of product stagings: product_stg price ids: %s" % initial_prices)
            product_stgs |= initial_prices.mapped('product_stg_id')
            if self._context.get('keep_current'):
                data.update({
                    'will_removed_campaign_regulers': product_stgs._create_price(self)
                })
            for initial_price in initial_prices:
                initial_price.product_stg_id.write({'list_price': initial_price.initial_list_price})
            initial_prices.unlink()
        return data

    # @api.multi
    def reguler_execute_job(self):
        self.ensure_one()

        pricelist_obj = self.env['product.pricelist']
        pricelist_item_obj = self.env['product.pricelist.item']
        product_stg_obj = self.env['product.staging']
        product_stg_price_obj = self.env['product.staging.price']
        campaign_job_obj = self.env['juragan.campaign.job']

        extra_context = json.loads(self.extra_context)
        pricelist_items = self.pricelist_item_ids
        if self.execution_type == 'interval_start':
            # 0. Reset back the reguler rules if it's related to this job
            self._reset_reguler_rule()

            # 1. Get product templates
            product_tmpls = pricelist_items.mapped('product_tmpl_id')

            # 2. Get marketplace accounts
            mp_accounts_data = {}
            for pricelist_item in pricelist_items:
                mp_name = pricelist_item.mp_id._name
                if mp_name in mp_accounts_data:
                    mp_accounts_data[mp_name] |= pricelist_item.mp_id
                else:
                    mp_accounts_data[mp_name] = pricelist_item.mp_id

            # 3. Get product stagings based on product tmpl and mp account
            _filter_by_mp_accounts = " OR ".join(["ps.%s IN %s" % (
                self.MP_ACCOUNT_FIELDS_PRODUCT_STAGINGS[mp_name],
                str(mp_accounts.ids).translate(str.maketrans('[]', '()'))
            ) for mp_name, mp_accounts in mp_accounts_data.items()])

            _sql_query = "SELECT id FROM product_staging AS ps " \
                         "WHERE (ps.product_template_id IN %s) " \
                         "AND (%s)" \
                         % (str(product_tmpls.ids).translate(str.maketrans('[]', '()')), _filter_by_mp_accounts)
            self.env.cr.execute(_sql_query)
            product_stg_ids = [res['id'] for res in self.env.cr.dictfetchall()]
            product_stgs = product_stg_obj.browse(product_stg_ids)

            # 4. Process reguler campaign for each product stagings and each mp account
            for product_stg in product_stgs:
                # 4.1. Keep current reguler rule stored as initial reguler rule for this product staging
                initial_price = product_stg._create_price(self)
                _logger.info("Collectiong current reguler price: (%s) %s: %s" % (
                    product_stg.id, product_stg.name, initial_price.initial_list_price))

                # 4.2. Find pricelist rule for this product staging
                valid_prices, valid_rules = [], pricelist_item_obj

                def _filter_pli(pli):
                    return pli.product_tmpl_id == product_stg.product_template_id \
                           and pli.mp_id == getattr(product_stg,
                                                    self.MP_ACCOUNT_FIELDS_PRODUCT_STAGINGS[pli.mp_id._name])

                for item in pricelist_items.filtered(_filter_pli).sorted('min_quantity'):
                    pricelist = item.pricelist_id
                    price, rule_id = pricelist.get_product_price_rule(product_stg.product_template_id,
                                                                      item.min_quantity, self.env.user.partner_id)
                    if rule_id != item.id:
                        continue
                    valid_prices.append(price)
                    valid_rules |= item
                # 4.3. Set campaign price into product staging
                if valid_prices:
                    product_stg.write({'list_price': valid_prices[0]})
                    _logger.info(
                        "New reguler price applied: (%s) %s: %s" % (product_stg.id, product_stg.name, product_stg.list_price))

            # 5. Push updated product stagings to marketplace
            _logger.info("Pushing reguler rules to marketplace...")
            try:
                product_stgs.upload_product_stg_izi()
                push_status_data = {
                    mp_name: {
                        product_stg.name: product_stg.read(
                            ['name', 'list_price'])
                        for product_stg in product_stgs
                    }
                    for mp_name in mp_accounts_data.keys()
                }
                pprint(push_status_data)
                extra_context.update({
                    'debug': push_status_data
                })
            except UserError as e:
                msg = "Something wrong happen during push data to marketplace: message: %s." % e.name
                _logger.error(msg)
                self._reset_reguler_rule()
                extra_context.update({
                    'debug': msg
                })
                self.write({'state': 'failed', 'extra_context': json.dumps(extra_context, indent=4)})
                return False

            # 6. Planning next execution to roll back the campaign wholesale rules to initial price
            future_jobs = campaign_job_obj
            future_job_set_datetime_data = list(
                set(pricelist_items.filtered(lambda pli: pli.set_datetime is True).mapped('date_time_end')))
            if future_job_set_datetime_data and future_job_set_datetime_data[0] is not False:
                for date_time_end in future_job_set_datetime_data:
                    extra_context.update({'previous_job_id': self.id})
                    future_jobs |= self.create({
                        'campaign_id': self.campaign_id.id,
                        'campaign_purpose': self.campaign_purpose,
                        'execution_type': 'interval_end',
                        'scheduled_at': date_time_end,
                        'pricelist_item_ids': [(6, 0, pricelist_items.filtered(
                            lambda pli: pli.set_datetime is True and pli.date_time_end == date_time_end).ids)],
                        'extra_context': json.dumps(extra_context, indent=4)
                    })
            else:
                if extra_context.get('future_job_set_weekday_data'):
                    for today_schedule_end, rule_ids in extra_context.get('future_job_set_weekday_data'):
                        extra_context.update({'previous_job_id': self.id, 'keep_on_pricelist': True})
                        existing_schedule_domain = [
                            ('campaign_id', '=', self.campaign_id.id),
                            ('campaign_purpose', '=', self.campaign_purpose),
                            ('execution_type', '=', 'interval_end'),
                            ('scheduled_at', '=', today_schedule_end)
                        ]
                        existing_schedule = campaign_job_obj.search(existing_schedule_domain, limit=1)
                        if existing_schedule.exists():
                            existing_schedule.write({'pricelist_item_ids': [(4, rule_id) for rule_id in rule_ids]})
                        else:
                            future_jobs |= self.create({
                                'campaign_id': self.campaign_id.id,
                                'campaign_purpose': self.campaign_purpose,
                                'execution_type': 'interval_end',
                                'scheduled_at': today_schedule_end,
                                'pricelist_item_ids': [(6, 0, rule_ids)],
                                'extra_context': json.dumps(extra_context, indent=4)
                            })

            future_jobs.setup()

            # 7. Finalize this job
            extra_context.update({
                'current_job_id': self.id
            })
            extra_context.pop('previous_job_id')
            self.write({
                'total_execution': self.total_execution + 1,
                'state': 'done',
                'extra_context': json.dumps(extra_context, indent=4)
            })
        elif self.execution_type == 'interval_end':
            # 1. Get marketplace accounts
            mp_accounts_data = {}
            for pricelist_item in pricelist_items:
                mp_name = pricelist_item.mp_id._name
                if mp_name in mp_accounts_data:
                    mp_accounts_data[mp_name] |= pricelist_item.mp_id
                else:
                    mp_accounts_data[mp_name] = pricelist_item.mp_id

            # 2. Find related reguler rule from current job, otherwise find it from previouse job.
            job = self
            if not job.product_stg_wholesale_ids:
                job = campaign_job_obj.browse(int(extra_context.get('previous_job_id', 0)))
            initial_product_stg_prices = job.product_stg_price_ids
            product_stgs = product_stg_obj
            will_removed_campaign_regulers = product_stg_price_obj
            if initial_product_stg_prices:
                product_stgs |= initial_product_stg_prices.mapped('product_stg_id')
                reset_data = job.with_context(({'keep_current': True}))._reset_reguler_rule()
                if reset_data.get('will_removed_campaign_regulers'):
                    will_removed_campaign_regulers |= reset_data.get('will_removed_campaign_regulers')

            # 3. Remove campaign wholesale price rules from active pricelist
            if not extra_context.get('keep_on_pricelist'):
                _logger.info("Removing campaign reguler price rules from active pricelist.")
                self.pricelist_item_ids.write({'pricelist_id': False})

            # 4. Push updated product stagings to marketplace
            for product_stg in product_stgs:
                _logger.info("Pushing reguler rules to marketplace: product: %s" % product_stg.name)
                try:
                    product_stg.upload_product_stg_izi()
                    push_status_data = {
                        mp_name: {
                            product_stg.name: product_stg.read(
                                ['name', 'list_price'])
                            for product_stg in product_stgs
                        }
                        for mp_name in mp_accounts_data.keys()
                    }
                    pprint(push_status_data)
                    extra_context.update({
                        'debug': push_status_data
                    })
                    will_removed_campaign_regulers.unlink()
                except UserError as e:
                    msg = "Something wrong happen during push data to marketplace: message: %s\n" \
                          "Failed to restore wholesale rule, action will be reverted: product staging: %s" \
                          % (e.name, product_stg.name)
                    _logger.error(msg)
                    self.with_context({'keep_current': True})._reset_reguler_rule()
                    self.pricelist_item_ids.write({'pricelist_id': self.campaign_id.pricelist_id.id})
                    extra_context.update({
                        'current_job_id': self.id,
                        'debug': msg
                    })
                    self.write({'state': 'failed', 'extra_context': json.dumps(extra_context, indent=4)})
                    return False

            # 5. Finalize this job
            self.write({
                'total_execution': self.total_execution + 1,
                'state': 'done',
                'extra_context': json.dumps(extra_context, indent=4)
            })

        elif self.execution_type == "continuously":
            utcnow = pytz.utc.localize(datetime.utcnow())

            # Check is there rule applied for today
            rules_weekday_all = pricelist_items.filtered(lambda pli: pricelist_obj._is_price_rule_weekday_all(pli))
            rules_weekday_today = pricelist_items.filtered(
                lambda pli: pricelist_obj._is_price_rule_weekday_today(pli, utcnow))

            # If none, find the closest date time of rule to start
            rules_weekday_later = pricelist_item_obj
            if not rules_weekday_all and not rules_weekday_today:
                closest_rule_to_start = pricelist_obj._get_price_rules_weekday_closest_date_time(pricelist_items,
                                                                                                 utcnow, 'start')
                rules_weekday_later |= closest_rule_to_start

            # Make schedule to apply the rules today
            rules_weekday_all_schedules_start = [
                ('interval_start', rule,
                 pricelist_obj._get_price_rule_weekday_closest_date_time(rule, utcnow, 'start').astimezone(pytz.utc))
                for rule in rules_weekday_all]
            rules_weekday_all_schedules_end = [
                ('interval_end', rule,
                 pricelist_obj._get_price_rule_weekday_closest_date_time(rule, utcnow, 'end').astimezone(pytz.utc))
                for rule in rules_weekday_all]
            rules_weekday_today_schedules_start = [
                ('interval_start', rule,
                 pricelist_obj._get_price_rule_weekday_closest_date_time(rule, utcnow, 'start').astimezone(pytz.utc))
                for rule in rules_weekday_today]
            rules_weekday_today_schedules_end = [
                ('interval_end', rule,
                 pricelist_obj._get_price_rule_weekday_closest_date_time(rule, utcnow, 'end').astimezone(pytz.utc))
                for rule in rules_weekday_today]
            today_schedules_start, today_schedules_end = {}, {}
            for schedule in sorted(itertools.chain(
                    rules_weekday_all_schedules_start, rules_weekday_all_schedules_end,
                    rules_weekday_today_schedules_start, rules_weekday_today_schedules_end
            ), key=lambda x: x[-1]):
                execution_type, rule, date_time = schedule
                date_time_str = date_time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                if execution_type == 'interval_start':
                    if date_time_str in today_schedules_start.keys():
                        today_schedules_start[date_time_str] |= rule
                    else:
                        today_schedules_start[date_time_str] = rule
                elif execution_type == 'interval_end':
                    if date_time_str in today_schedules_end.keys():
                        today_schedules_end[date_time_str] |= rule
                    else:
                        today_schedules_end[date_time_str] = rule

            # Generate jobs based on today's schedule
            today_jobs = campaign_job_obj
            for today_schedule_start, rules in today_schedules_start.items():
                extra_context.update({
                    'previous_job_id': self.id,
                    'future_job_set_weekday_data': [(today_schedule_end, rules_end.ids) for
                                                    today_schedule_end, rules_end in today_schedules_end.items()]
                })
                today_jobs |= self.create({
                    'campaign_id': self.campaign_id.id,
                    'campaign_purpose': self.campaign_purpose,
                    'execution_type': 'interval_start',
                    'scheduled_at': today_schedule_start,
                    'pricelist_item_ids': [(6, 0, rules.ids)],
                    'extra_context': json.dumps(extra_context, indent=4)
                })
            today_jobs.setup()

            # Make this job executing itself once a day to make a daily schedules
            tz = pytz.timezone(self.env.user.tz or pytz.utc.zone)
            nextcall_str = '{date} {time}'.format(**{
                'date': (utcnow.astimezone(tz) + timedelta(days=1)).strftime(DEFAULT_SERVER_DATE_FORMAT),
                'time': '00:00:00'
            })
            nextcall = tz.localize(datetime.strptime(nextcall_str, DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(pytz.utc)
            self.write({'scheduled_at': nextcall.strftime(DEFAULT_SERVER_DATETIME_FORMAT)})
            self.setup()

            # Finalize this job
            self.write({
                'total_execution': self.total_execution + 1,
                'extra_context': json.dumps(extra_context, indent=4)
            })
        elif self.execution_type == "immediately":
            extra_context.update({
                'immediately': True,
                'wholesale_remove_force': True
            })
            immediate_job = self.create({
                'campaign_id': self.campaign_id.id,
                'campaign_purpose': self.campaign_purpose,
                'execution_type': 'interval_start',
                'scheduled_at': self.scheduled_at,
                'pricelist_item_ids': [(6, 0, self.pricelist_item_ids.ids)],
                'extra_context': json.dumps(extra_context, indent=4)
            })
            immediate_job.setup(execute=True)

            # Finalize this job
            self.write({
                'total_execution': self.total_execution + 1,
                'state': 'done',
                'extra_context': json.dumps(extra_context, indent=4)
            })


class JuraganCampaignJobWholesale(models.Model):
    _inherit = 'juragan.campaign.job'

    product_stg_wholesale_ids = fields.One2many(comodel_name="product.staging.wholesale", inverse_name="related_job_id",
                                                string="Product Staging Wholesales", required=False)

    @api.model
    def wholesale_init_job(self, common_values, items):
        # Filter pricelist items based on set_datetime parameter
        items_with_set_datetime = items.filtered(lambda pli: pli.set_datetime)
        items_with_set_weekday = items.filtered(lambda pli: pli.set_weekday)
        items_general = items - items_with_set_datetime - items_with_set_weekday

        # Items with set_datetime will generate jobs with 'interval start' type.
        # So in the method that will be executed first, you need to create another jobs with 'interval end' type.
        for date_time_start in list(set(items_with_set_datetime.mapped('date_time_start'))):
            self.create(dict(common_values, **{
                'execution_type': 'interval_start',
                'scheduled_at': date_time_start,
                'pricelist_item_ids': [(6, 0, items_with_set_datetime.filtered(
                    lambda pli: pli.date_time_start == date_time_start).ids)]
            }))

        # items_with_set_weekday will generate job to run continuously
        if items_with_set_weekday:
            self.create(dict(common_values, **{
                'execution_type': 'continuously',
                'scheduled_at': fields.Datetime.now(),
                'pricelist_item_ids': [(6, 0, items_with_set_weekday.ids)]
            }))

        # items_general will executed immediately
        if items_general:
            self.create(dict(common_values, **{
                'execution_type': 'immediately',
                'scheduled_at': fields.Datetime.now(),
                'pricelist_item_ids': [(6, 0, items_general.ids)]
            }))

    # @api.multi
    def wholesale_setup_job(self, execute=False):
        for job in self:
            values = {}
            if job.execution_type == 'interval_start':
                values.update({
                    'name': "Apply temporary wholesale rules."
                })
            elif job.execution_type == 'interval_end':
                values.update({
                    'name': "Roll back the temporary wholesale rules to the initial price."
                })
            elif job.execution_type == 'continuously':
                values.update({
                    'name': "Making schedules for the nearest upcoming wholesale rules that need to be applied."
                })
            elif job.execution_type == 'immediately':
                values.update({
                    'name': "Apply permanent wholesale rules immediately",
                })
                execute = True

            if not execute:
                cron = job._create_cron(name=values.get('name'))
                values.update({'cron_ids': [(4, cron.id)]})
            else:
                job.execute()
            job.write(values)

    # @api.multi
    def _reset_wholesale_rule(self):
        self.ensure_one()

        product_stg_obj = self.env['product.staging']

        data = {}
        initial_product_stg_wholesales = self.product_stg_wholesale_ids
        product_stgs = product_stg_obj
        if initial_product_stg_wholesales:
            _logger.info(
                "Restoring initial price of product stagings: wholesale ids: %s" % initial_product_stg_wholesales.ids)
            product_stgs |= initial_product_stg_wholesales.mapped('initial_product_stg_id')
            if self._context.get('keep_current'):
                data.update({
                    'will_removed_campaign_wholesales': product_stgs.mapped('product_wholesale_ids')
                })
                for product_stg in product_stgs:
                    product_stg.product_wholesale_ids.write({
                        'product_stg_id': False,
                        'initial_product_stg_id': product_stg.id,
                        'related_job_id': self.id
                    })
            else:
                product_stgs.mapped('product_wholesale_ids').unlink()
            for initial_product_stg_wholesale in initial_product_stg_wholesales:
                initial_product_stg_wholesale.write({
                    'product_stg_id': initial_product_stg_wholesale.initial_product_stg_id.id
                })
            initial_product_stg_wholesales.write({'related_job_id': False, 'initial_product_stg_id': False})
        return data

    # @api.multi
    def wholesale_execute_job(self):
        self.ensure_one()

        pricelist_obj = self.env['product.pricelist']
        pricelist_item_obj = self.env['product.pricelist.item']
        product_stg_obj = self.env['product.staging']
        product_stg_wholesale_obj = self.env['product.staging.wholesale']
        campaign_job_obj = self.env['juragan.campaign.job']

        extra_context = json.loads(self.extra_context)
        pricelist_items = self.pricelist_item_ids
        if self.execution_type == 'interval_start':
            # 0. Reset back the wholesale rules if it's related to this job
            self._reset_wholesale_rule()

            # 1. Get product templates
            product_tmpls = pricelist_items.mapped('product_tmpl_id')

            # 2. Get marketplace accounts
            mp_accounts_data = {}
            for pricelist_item in pricelist_items:
                mp_name = pricelist_item.mp_id._name
                if mp_name in mp_accounts_data:
                    mp_accounts_data[mp_name] |= pricelist_item.mp_id
                else:
                    mp_accounts_data[mp_name] = pricelist_item.mp_id

            # 3. Get product stagings based on product tmpl and mp account
            _filter_by_mp_accounts = " OR ".join(["ps.%s IN %s" % (
                self.MP_ACCOUNT_FIELDS_PRODUCT_STAGINGS[mp_name],
                str(mp_accounts.ids).translate(str.maketrans('[]', '()'))
            ) for mp_name, mp_accounts in mp_accounts_data.items()])

            _sql_query = "SELECT id FROM product_staging AS ps " \
                         "WHERE (ps.product_template_id IN %s) " \
                         "AND (%s)" \
                         % (str(product_tmpls.ids).translate(str.maketrans('[]', '()')), _filter_by_mp_accounts)
            self.env.cr.execute(_sql_query)
            product_stg_ids = [res['id'] for res in self.env.cr.dictfetchall()]
            product_stgs = product_stg_obj.browse(product_stg_ids)

            # 4. Process wholesale campaign for each product stagings and each mp account
            for product_stg in product_stgs:
                # 4.1. Keep current wholesale rule stored as initial wholesale rule for this product staging
                _logger.info(
                    "Collecting current wholesale rules: wholesale ids: %s" % product_stg.product_wholesale_ids.ids)
                product_stg.product_wholesale_ids.write({
                    'product_stg_id': False,
                    'initial_product_stg_id': product_stg.id,
                    'related_job_id': self.id
                })
                # 4.2. Find pricelist rule for this product staging
                valid_prices, valid_rules = [], pricelist_item_obj
                for item in pricelist_items.filtered(
                        lambda pli: pli.product_tmpl_id == product_stg.product_template_id and pli.mp_id == getattr(
                            product_stg, self.MP_ACCOUNT_FIELDS_PRODUCT_STAGINGS[pli.mp_id._name])).sorted(
                    'min_quantity'):
                    pricelist = item.pricelist_id
                    price, rule_id = pricelist.get_product_price_rule(product_stg.product_template_id,
                                                                      item.min_quantity, self.env.user.partner_id)
                    if rule_id != item.id:
                        continue
                    valid_prices.append(price)
                    valid_rules |= item
                campaign_min_qtys = valid_rules.mapped('min_quantity')
                campaign_max_qtys = list(map(operator.sub, campaign_min_qtys[1:], [1] * len(campaign_min_qtys[1:]))) + [
                    10000]
                # 4.3. Creating campaign wholesale based on pricelist rule
                campaign_product_stg_wholesales = product_stg_wholesale_obj
                if len(valid_prices) == len(campaign_min_qtys) == len(campaign_max_qtys):
                    for index, price in enumerate(valid_prices):
                        campaign_product_stg_wholesales |= product_stg_wholesale_obj.create({
                            'product_stg_id': product_stg.id,
                            'min_qty': campaign_min_qtys[index],
                            'max_qty': campaign_max_qtys[index],
                            'price_wholesale': price
                        })
                _logger.info('New wholesale rules applied: wholesale ids: %s' % campaign_product_stg_wholesales.ids)

            # 5. Push updated product stagings to marketplace
            _logger.info("Pushing wholesale rules to marketplace...")
            try:
                product_stgs.upload_product_stg_izi()
                push_status_data = {
                    mp_name: {
                        product_stg.name: product_stg.product_wholesale_ids.read(
                            ['min_qty', 'max_qty', 'price_wholesale'])
                        for product_stg in product_stgs
                    }
                    for mp_name in mp_accounts_data.keys()
                }
                pprint(push_status_data)
                extra_context.update({
                    'debug': push_status_data
                })
            except UserError as e:
                msg = "Something wrong happen during push data to marketplace: message: %s." % e.name
                _logger.error(msg)
                self._reset_wholesale_rule()
                extra_context.update({
                    'debug': msg
                })
                self.write({'state': 'failed', 'extra_context': json.dumps(extra_context, indent=4)})
                return False

            # 6. Planning next execution to roll back the campaign wholesale rules to initial price
            future_jobs = campaign_job_obj
            future_job_set_datetime_data = list(
                set(pricelist_items.filtered(lambda pli: pli.set_datetime is True).mapped('date_time_end')))
            if future_job_set_datetime_data and future_job_set_datetime_data[0] is not False:
                for date_time_end in future_job_set_datetime_data:
                    extra_context.update({'previous_job_id': self.id})
                    future_jobs |= self.create({
                        'campaign_id': self.campaign_id.id,
                        'campaign_purpose': self.campaign_purpose,
                        'execution_type': 'interval_end',
                        'scheduled_at': date_time_end,
                        'pricelist_item_ids': [(6, 0, pricelist_items.filtered(
                            lambda pli: pli.set_datetime is True and pli.date_time_end == date_time_end).ids)],
                        'extra_context': json.dumps(extra_context, indent=4)
                    })
            else:
                if extra_context.get('future_job_set_weekday_data'):
                    for today_schedule_end, rule_ids in extra_context.get('future_job_set_weekday_data'):
                        extra_context.update({'previous_job_id': self.id, 'keep_on_pricelist': True})
                        existing_schedule_domain = [
                            ('campaign_id', '=', self.campaign_id.id),
                            ('campaign_purpose', '=', self.campaign_purpose),
                            ('execution_type', '=', 'interval_end'),
                            ('scheduled_at', '=', today_schedule_end)
                        ]
                        existing_schedule = campaign_job_obj.search(existing_schedule_domain, limit=1)
                        if existing_schedule.exists():
                            existing_schedule.write({'pricelist_item_ids': [(4, rule_id) for rule_id in rule_ids]})
                        else:
                            future_jobs |= self.create({
                                'campaign_id': self.campaign_id.id,
                                'campaign_purpose': self.campaign_purpose,
                                'execution_type': 'interval_end',
                                'scheduled_at': today_schedule_end,
                                'pricelist_item_ids': [(6, 0, rule_ids)],
                                'extra_context': json.dumps(extra_context, indent=4)
                            })

            future_jobs.setup()

            # 7. Finalize this job
            extra_context.update({
                'current_job_id': self.id
            })
            extra_context.pop('previous_job_id')
            self.write({
                'total_execution': self.total_execution + 1,
                'state': 'done',
                'extra_context': json.dumps(extra_context, indent=4)
            })
        elif self.execution_type == 'interval_end':

            # 1. Get marketplace accounts
            mp_accounts_data = {}
            for pricelist_item in pricelist_items:
                mp_name = pricelist_item.mp_id._name
                if mp_name in mp_accounts_data:
                    mp_accounts_data[mp_name] |= pricelist_item.mp_id
                else:
                    mp_accounts_data[mp_name] = pricelist_item.mp_id

            # 2. Find related wholesale rule from current job, otherwise find it from previouse job.
            job = self
            if not job.product_stg_wholesale_ids:
                job = campaign_job_obj.browse(int(extra_context.get('previous_job_id', 0)))
            initial_product_stg_wholesales = job.product_stg_wholesale_ids
            product_stgs = product_stg_obj
            will_removed_campaign_wholesales = product_stg_wholesale_obj
            if initial_product_stg_wholesales:
                product_stgs |= initial_product_stg_wholesales.mapped('initial_product_stg_id')
                reset_data = job.with_context({'keep_current': True})._reset_wholesale_rule()
                if reset_data.get('will_removed_campaign_wholesales'):
                    will_removed_campaign_wholesales |= reset_data.get('will_removed_campaign_wholesales')

            # 3. Remove campaign wholesale price rules from active pricelist
            if not extra_context.get('keep_on_pricelist'):
                _logger.info("Removing campaign wholesale price rules from active pricelist.")
                self.pricelist_item_ids.write({'pricelist_id': False})

            # 4. Push updated product stagings to marketplace
            for product_stg in product_stgs:
                _logger.info("Pushing wholesale rules to marketplace: product: %s" % product_stg.name)
                try:
                    product_stg.upload_product_stg_izi()
                    push_status_data = {
                        mp_name: {
                            product_stg.name: product_stg.product_wholesale_ids.read(
                                ['min_qty', 'max_qty', 'price_wholesale'])
                            for product_stg in product_stgs
                        }
                        for mp_name in mp_accounts_data.keys()
                    }
                    pprint(push_status_data)
                    extra_context.update({
                        'debug': push_status_data
                    })
                    will_removed_campaign_wholesales.unlink()
                except UserError as e:
                    msg = "Something wrong happen during push data to marketplace: message: %s\n" \
                          "Failed to restore wholesale rule, action will be reverted: product staging: %s" \
                          % (e.name, product_stg.name)
                    _logger.error(msg)
                    self.with_context({'keep_current': True})._reset_wholesale_rule()
                    self.pricelist_item_ids.write({'pricelist_id': self.campaign_id.pricelist_id.id})
                    extra_context.update({
                        'current_job_id': self.id,
                        'debug': msg
                    })
                    self.write({'state': 'failed', 'extra_context': json.dumps(extra_context, indent=4)})
                    return False

            # 5. Finalize this job
            self.write({
                'total_execution': self.total_execution + 1,
                'state': 'done',
                'extra_context': json.dumps(extra_context, indent=4)
            })
        elif self.execution_type == "continuously":
            utcnow = pytz.utc.localize(datetime.utcnow())

            # Check is there rule applied for today
            rules_weekday_all = pricelist_items.filtered(lambda pli: pricelist_obj._is_price_rule_weekday_all(pli))
            rules_weekday_today = pricelist_items.filtered(
                lambda pli: pricelist_obj._is_price_rule_weekday_today(pli, utcnow))

            # If none, find the closest date time of rule to start
            rules_weekday_later = pricelist_item_obj
            if not rules_weekday_all and not rules_weekday_today:
                closest_rule_to_start = pricelist_obj._get_price_rules_weekday_closest_date_time(pricelist_items,
                                                                                                 utcnow, 'start')
                rules_weekday_later |= closest_rule_to_start

            # Make schedule to apply the rules today
            rules_weekday_all_schedules_start = [
                ('interval_start', rule,
                 pricelist_obj._get_price_rule_weekday_closest_date_time(rule, utcnow, 'start').astimezone(pytz.utc))
                for rule in rules_weekday_all]
            rules_weekday_all_schedules_end = [
                ('interval_end', rule,
                 pricelist_obj._get_price_rule_weekday_closest_date_time(rule, utcnow, 'end').astimezone(pytz.utc))
                for rule in rules_weekday_all]
            rules_weekday_today_schedules_start = [
                ('interval_start', rule,
                 pricelist_obj._get_price_rule_weekday_closest_date_time(rule, utcnow, 'start').astimezone(pytz.utc))
                for rule in rules_weekday_today]
            rules_weekday_today_schedules_end = [
                ('interval_end', rule,
                 pricelist_obj._get_price_rule_weekday_closest_date_time(rule, utcnow, 'end').astimezone(pytz.utc))
                for rule in rules_weekday_today]
            today_schedules_start, today_schedules_end = {}, {}
            for schedule in sorted(itertools.chain(
                    rules_weekday_all_schedules_start, rules_weekday_all_schedules_end,
                    rules_weekday_today_schedules_start, rules_weekday_today_schedules_end
            ), key=lambda x: x[-1]):
                execution_type, rule, date_time = schedule
                date_time_str = date_time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                if execution_type == 'interval_start':
                    if date_time_str in today_schedules_start.keys():
                        today_schedules_start[date_time_str] |= rule
                    else:
                        today_schedules_start[date_time_str] = rule
                elif execution_type == 'interval_end':
                    if date_time_str in today_schedules_end.keys():
                        today_schedules_end[date_time_str] |= rule
                    else:
                        today_schedules_end[date_time_str] = rule

            # Generate jobs based on today's schedule
            today_jobs = campaign_job_obj
            for today_schedule_start, rules in today_schedules_start.items():
                extra_context.update({
                    'previous_job_id': self.id,
                    'future_job_set_weekday_data': [(today_schedule_end, rules_end.ids) for
                                                    today_schedule_end, rules_end in today_schedules_end.items()]
                })
                today_jobs |= self.create({
                    'campaign_id': self.campaign_id.id,
                    'campaign_purpose': self.campaign_purpose,
                    'execution_type': 'interval_start',
                    'scheduled_at': today_schedule_start,
                    'pricelist_item_ids': [(6, 0, rules.ids)],
                    'extra_context': json.dumps(extra_context, indent=4)
                })
            today_jobs.setup()

            # Make this job executing itself once a day to make a daily schedules
            tz = pytz.timezone(self.env.user.tz or pytz.utc.zone)
            nextcall_str = '{date} {time}'.format(**{
                'date': (utcnow.astimezone(tz) + timedelta(days=1)).strftime(DEFAULT_SERVER_DATE_FORMAT),
                'time': '00:00:00'
            })
            nextcall = tz.localize(datetime.strptime(nextcall_str, DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(pytz.utc)
            self.write({'scheduled_at': nextcall.strftime(DEFAULT_SERVER_DATETIME_FORMAT)})
            self.setup()

            # Finalize this job
            self.write({
                'total_execution': self.total_execution + 1,
                'extra_context': json.dumps(extra_context, indent=4)
            })

        elif self.execution_type == "immediately":
            extra_context.update({
                'immediately': True,
                'wholesale_remove_force': True
            })
            immediate_job = self.create({
                'campaign_id': self.campaign_id.id,
                'campaign_purpose': self.campaign_purpose,
                'execution_type': 'interval_start',
                'scheduled_at': self.scheduled_at,
                'pricelist_item_ids': [(6, 0, self.pricelist_item_ids.ids)],
                'extra_context': json.dumps(extra_context, indent=4)
            })
            immediate_job.setup(execute=True)

            # Finalize this job
            self.write({
                'total_execution': self.total_execution + 1,
                'state': 'done',
                'extra_context': json.dumps(extra_context, indent=4)
            })


class CampaignRegulerWizard(models.TransientModel):
    _name = 'wizard.juragan.campaign.reguler'
    _inherit = 'product.pricelist.item'
    _description = 'Juragan Campaign Reguler Wizard'

    campaign_id = fields.Many2one(comodel_name="juragan.campaign", string="Campaign", required=True)
    mp_id = fields.Reference(JuraganCampaign.MP_TYPES, string='Marketplace', required=True)
    applied_on = fields.Selection(
        [('4_batch_filter', 'Batch Products with Filter'), ('5_products', 'Select Multi Products'),
         ('1_product', 'Single Product')], "Apply On", default='4_batch_filter',
        required=True, help='Pricelist Item applicable on selected option')
    product_tmpl_domain_filter = fields.Char(string="Filters", default="[]")
    product_tmpl_ids = fields.Many2many(comodel_name="product.template", relation="pli_product_tmpl_rel",
                                        column1="pricelist_item_id", column2="product_tmpl_id", string="Products")

    # pricelist_item_ids = fields.One2many("wizard.juragan.campaign.wholesale.item", "wizard_id", "Pricelist Items")

    @api.model
    def default_get(self, fields_list):
        res = super(CampaignRegulerWizard, self).default_get(fields_list)
        if 'campaign_id' in res:
            campaign = self.env['juragan.campaign'].browse(res['campaign_id'])
            res.update(campaign.read([
                'set_mode', 'set_datetime', 'date_time_start', 'date_time_end',
                'set_weekday', 'time_start', 'time_end', 'weekday_tz',
                'day_0', 'day_1', 'day_2', 'day_3', 'day_4', 'day_5', 'day_6'
            ])[0])
        return res

    def add(self):
        product_tmpl_obj = self.env['product.template']

        items_data = []
        if self.applied_on == '1_product':
            items_data.append(dict(self.copy_data()[0], **{
                'applied_on': self.applied_on,
                'product_tmpl_id': self.product_tmpl_id.id
            }))
        elif self.applied_on == '5_products':
            for product_tmpl in self.product_tmpl_ids:
                items_data.append(dict(self.copy_data()[0], **{
                    'applied_on': '1_product',
                    'product_tmpl_id': product_tmpl.id
                }))
        elif self.applied_on == '4_batch_filter':
            domain = json.loads(self.product_tmpl_domain_filter)
            product_tmpls = product_tmpl_obj.search(domain)
            for product_tmpl in product_tmpls:
                items_data.append(dict(self.copy_data()[0], **{
                    'applied_on': '1_product',
                    'product_tmpl_id': product_tmpl.id
                }))
        for item_data in items_data:
            removed_fields = ['product_tmpl_domain_filter', 'product_tmpl_ids']
            for removed_field in removed_fields:
                item_data.pop(removed_field)
            item_data.update({
                'campaign_id': self.campaign_id.id,
                'mp_id': '%s,%s' % (self.mp_id._name, self.mp_id.id),
                'pricelist_id': False,
                'campaign_purpose': 'reguler'
            })
        values = [(0, 0, value) for value in items_data]
        self.campaign_id.write({
            'pricelist_item_ids': values
        })


class CampaignWholesaleWizard(models.TransientModel):
    _name = 'wizard.juragan.campaign.wholesale'
    _inherit = 'product.pricelist.item'
    _description = 'Juragan Campaign Wholesale Wizard'

    campaign_id = fields.Many2one(comodel_name="juragan.campaign", string="Campaign", required=True)
    mp_id = fields.Reference(JuraganCampaign.MP_TYPES, string='Marketplace', required=True)
    pricelist_item_ids = fields.One2many("wizard.juragan.campaign.wholesale.item", "wizard_id", "Pricelist Items")

    @api.model
    def default_get(self, fields_list):
        res = super(CampaignWholesaleWizard, self).default_get(fields_list)
        campaign = self.env['juragan.campaign'].browse(res['campaign_id'])
        res.update(campaign.read([
            'set_mode', 'set_datetime', 'date_time_start', 'date_time_end',
            'set_weekday', 'time_start', 'time_end', 'weekday_tz',
            'day_0', 'day_1', 'day_2', 'day_3', 'day_4', 'day_5', 'day_6'
        ])[0])
        return res

    def add(self):
        if not self.pricelist_item_ids:
            raise ValidationError("No price rules defined, please set wholesale rule correctly!")
        fields_list = [
            'set_datetime', 'date_time_start', 'date_time_end',
            'set_weekday', 'time_start', 'time_end', 'weekday_tz',
            'day_0', 'day_1', 'day_2', 'day_3', 'day_4', 'day_5', 'day_6'
        ]
        self_data = {k: getattr(self, k) for k in fields_list}
        items_data = [item.copy_data()[0] for item in self.pricelist_item_ids]
        for item_data in items_data:
            item_data.update(dict(self_data, **{
                'campaign_id': self.campaign_id.id,
                'mp_id': '%s,%s' % (self.mp_id._name, self.mp_id.id),
                'pricelist_id': False,
                'campaign_purpose': 'wholesale'
            }))
        values = [(0, 0, value) for value in items_data]
        self.campaign_id.write({
            'pricelist_item_ids': values
        })


class CampaignWholesaleItemWizard(models.TransientModel):
    _name = 'wizard.juragan.campaign.wholesale.item'
    _inherit = 'product.pricelist.item'
    _description = 'Juragan Campaign Wholesale Item Wizard'

    wizard_id = fields.Many2one(comodel_name="wizard.juragan.campaign.wholesale", string="Wizard")
    mp_id = fields.Reference(related="wizard_id.mp_id")

    # @api.one
    @api.depends('wizard_id.pricelist_item_ids')
    def _get_pricelist_item_name_price_campaign(self):
        self.ensure_one()
        super(CampaignWholesaleItemWizard, self)._get_pricelist_item_name_price_campaign()
