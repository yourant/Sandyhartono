# -*- coding: utf-8 -*-
import json
import logging

from odoo import api, fields, models

from ..campaign.campaign import JuraganCampaign as BaseJuraganCampaign

_logger = logging.getLogger(__name__)


class JuraganCampaign(models.Model):
    _inherit = 'juragan.campaign'

    CAMPAIGN_PURPOSE = [
        ('mp_discount', 'Marketplace Discount')
    ]

    campaign_purpose = fields.Selection(selection_add=CAMPAIGN_PURPOSE)
    mp_id = fields.Reference(BaseJuraganCampaign.MP_TYPES, string='Marketplace', required=False)
    discount_id = fields.Many2one(comodel_name="mp.product.discount", string="Marketplace Discount", required=False)
    discount_data_md5 = fields.Char()

    @api.model
    def create(self, values):
        campaign = super(JuraganCampaign, self).create(values)
        if campaign.campaign_purpose == 'mp_discount' and not campaign.discount_id:
            campaign._create_discount()
        return campaign

    def unlink(self):
        for campaign in self:
            campaign.discount_id.unlink()
        return super(JuraganCampaign, self).unlink()

    @api.onchange('campaign_purpose')
    def _onchange_campaign_purpose(self):
        if self.campaign_purpose == 'mp_discount':
            self.set_mode = 'set_datetime'

    def open_wizard_campaign_mp_discount(self):
        self.ensure_one()
        action = self.env.ref('juragan_product.action_window_wizard_juragan_campaign_mp_discount').read()[0]
        context = json.loads(action['context'])
        context.update({
            'form_view_ref': 'juragan_ui.form_wizard_juragan_campaign_mp_discount',
            'default_campaign_id': self.id,
        })
        action['context'] = context
        return action

    def _prepare_discount_values_from_campaign(self, current_discount=None):
        discount_values = {
            'name': self.name,
            'date_time_start': self.date_time_start,
            'date_time_end': self.date_time_end
        }

        if self.mp_id._name == 'mp.tokopedia':
            tp_discount_status = (current_discount and current_discount.tp_discount_status) or 'COMING SOON'
            tp_discount_type = (current_discount and current_discount.tp_discount_type) or '1'

            discount_values.update({
                'mp_tokopedia_id': self.mp_id.id,
                'tp_discount_status': tp_discount_status,
                'tp_discount_type': tp_discount_type
            })
        elif self.mp_id._name == 'mp.shopee':
            sp_discount_status = (current_discount and current_discount.sp_discount_status) or 'upcoming'

            discount_values.update({
                'mp_shopee_id': self.mp_id.id,
                'sp_discount_status': sp_discount_status
            })

        return discount_values

    def _create_discount(self):
        self.ensure_one()
        product_discount_obj = self.env['mp.product.discount']
        product_discount_values = self._prepare_discount_values_from_campaign()
        product_discount = product_discount_obj.create(product_discount_values)
        self.write({'discount_id': product_discount.id})
        return product_discount

    def _prepare_campaign_values_from_discount(self, discount, update=False):
        # prepare value to create/update campaign rule
        mp_id = '%s,%s'
        if discount.mp_tokopedia_id:
            mp_id = mp_id % (discount.mp_tokopedia_id._name, discount.mp_tokopedia_id.id)
        if discount.mp_shopee_id:
            mp_id = mp_id % (discount.mp_shopee_id._name, discount.mp_shopee_id.id)

        # prepare value to create/update campaign
        campaign_values = {
            'discount_id': discount.id,
            'discount_data_md5': discount.izi_md5,
            'mp_id': mp_id,
            'name': discount.name,
            'campaign_purpose': 'mp_discount',
            'set_mode': 'set_datetime',
            'set_datetime': True,
            'date_time_start': discount.date_time_start,
            'date_time_end': discount.date_time_end,
        }
        if update:
            # Update One2Many not supported yet, simply return current values
            return campaign_values

        campaign_rule_insert = []
        for discount_line in discount.product_ids:
            campaign_rule_insert.append(
                (0, 0, self._prepare_campaign_rule_values_from_discount_line(discount_line, update=update)))

        campaign_values.update({
            'pricelist_item_ids': campaign_rule_insert
        })

        return campaign_values

    def _prepare_campaign_rule_values_from_discount_line(self, discount_line, update=False):
        # get discount
        product_discount = discount_line.discount_id

        # prepare value to create/update campaign rule
        mp_id = '%s,%s'
        if product_discount.mp_tokopedia_id:
            mp_id = mp_id % (product_discount.mp_tokopedia_id._name, product_discount.mp_tokopedia_id.id)
        if product_discount.mp_shopee_id:
            mp_id = mp_id % (product_discount.mp_shopee_id._name, product_discount.mp_shopee_id.id)

        campaign_rule_values = {
            'discount_line_id': discount_line.id,
            'discount_line_data_md5': discount_line.izi_md5,
            'mp_id': mp_id,
            'campaign_purpose': 'mp_discount',
            'applied_on': '1_product',
            'product_tmpl_id': discount_line.product_stg_id.product_template_id.id,
            'date_time_start': product_discount.date_time_start,
            'date_time_end': product_discount.date_time_end,
            'compute_price': 'fixed',
            'fixed_price': discount_line.discounted_price
        }

        if update:
            campaign_rule_values.update({'campaign_id': self.id})

        return campaign_rule_values

    def _sync_with_discount(self, remove_campaign=False, update_campaign_rule=False, remove_campaign_rule=False,
                            add_campaign_rule=False):
        self.ensure_one()

        product_discount_line_obj = self.env['mp.product.discount.line'].sudo()

        # first we need to reset campaign to draft
        if self.state == 'done':
            _logger.info("Reset campaign to draft: %s" % self.name)
            self.action_draft()

        # check if it needs to be removed
        if remove_campaign:
            _logger.info("Removing campaign: %s" % self.name)
            self.unlink()
            return

        # get discount
        product_discount = self.discount_id

        # check discount status
        discount_status = product_discount.discount_state

        if discount_status == 'inactive':
            _logger.info("Cancelling campaign: %s" % self.name)
            self.action_cancel()
            return

        # prepare value to update campaign
        campaign_values = {
            'name': product_discount.name,
            'campaign_purpose': 'mp_discount',
            'set_mode': 'set_datetime',
            'date_time_start': product_discount.date_time_start,
            'date_time_end': product_discount.date_time_end
        }
        # update campaign
        _logger.info("Updating campaign: %s" % self.name)
        self.write(campaign_values)

        # remove campaign rule
        if remove_campaign_rule:
            campaign_rules_to_remove = self.pricelist_item_ids.filtered(lambda p: p.id in remove_campaign_rule)
            _logger.info("Removing campaign rules: %s" % campaign_rules_to_remove.ids)
            campaign_rules_to_remove.unlink()

        # update campaign rule
        if update_campaign_rule:
            for pli in self.pricelist_item_ids.filtered(
                    lambda p: p.discount_line_data_md5 != p.discount_line_id.izi_md5):
                # noinspection PyTypeChecker
                campaign_rule_values = self._prepare_campaign_rule_values_from_discount_line(pli.discount_line_id,
                                                                                             update=True)
                _logger.info("Updating campaign rule: %s: %s" % (pli.campaign_id.name, pli.product_tmpl_id.name))
                pli.write(campaign_rule_values)

        # create campaign rule
        if add_campaign_rule:
            product_discount_lines = product_discount_line_obj.browse(add_campaign_rule)
            for product_discount_line in product_discount_lines:
                campaign_rule = self.pricelist_item_ids.create(
                    self._prepare_campaign_rule_values_from_discount_line(product_discount_line, update=True))
                _logger.info("New campaign rule created: %s: %s"
                             % (campaign_rule.campaign_id.name, campaign_rule.product_tmpl_id.name))

        # run the campaign if discount is active
        if discount_status == 'active':
            _logger.info("Running campaign: %s" % self.name)
            self.action_run()

        # set campaign to draft if discount is coming soon
        if discount_status == 'coming_soon' and self.state != 'draft':
            _logger.info("Set campaign to draft for caming soon discount: %s" % self.name)
            self.action_draft()

    def sync_with_discount(self, force=False):
        # find campaign that need to be updated
        for mp_campaign in self:
            # get product discount
            mp_campaign_product_discount = mp_campaign.discount_id

            # if campaign losing its discount, then it need to be removed
            if not mp_campaign_product_discount:
                mp_campaign._sync_with_discount(remove_campaign=True)
                continue

            # if hash is different then there's data changed and campaign need to be updated
            campaign_need_update = mp_campaign.discount_data_md5 != mp_campaign_product_discount.izi_md5

            campaign_rule_need_update = []
            discount_line_ids_need_add, campaign_rule_ids_need_remove = [], []

            discount_line_count = len(mp_campaign_product_discount.product_ids)
            campaign_rule_count = len(mp_campaign.pricelist_item_ids)
            if discount_line_count > campaign_rule_count:
                # if number of discount line greater than number of campaign rule, then there's new discount line
                # that need to be added as campaign rule in this campaign
                discount_line_ids_need_add += list(set(mp_campaign_product_discount.product_ids.ids) - \
                                              set(mp_campaign.pricelist_item_ids.mapped('discount_line_id').ids))

            # find campaign rule that need to be updated or removed
            for pli in mp_campaign.pricelist_item_ids:
                # get product discount line
                mp_campaign_product_discount_line = pli.discount_line_id

                # if campaign rule losing its discount line, then it needs to be removed
                if not mp_campaign_product_discount_line:
                    campaign_rule_ids_need_remove.append(pli.id)
                    continue

                # if hash is different then there's data changed and campaign rule need to be updated
                campaign_rule_need_update.append(
                    pli.discount_line_data_md5 != mp_campaign_product_discount_line.izi_md5)

            if any(campaign_rule_need_update) and campaign_need_update is False:
                campaign_need_update = True
            if campaign_rule_ids_need_remove and campaign_need_update is False:
                campaign_need_update = True
            if discount_line_ids_need_add and campaign_need_update is False:
                campaign_need_update = True
            if force:
                campaign_need_update = True
                campaign_rule_need_update = [True]
            if campaign_need_update:
                sync_data = {
                    'update_campaign_rule': any(campaign_rule_need_update),
                    'remove_campaign_rule': campaign_rule_ids_need_remove,
                    'add_campaign_rule': discount_line_ids_need_add
                }
                mp_campaign.with_context(sync_discount=True)._sync_with_discount(**sync_data)

    def action_push(self):
        self.ensure_one()
        discount_values = self._prepare_discount_values_from_campaign(self.discount_id)
        product_discount = self.discount_id
        product_discount.write(discount_values)
        for pli in self.pricelist_item_ids:
            discount_line_values = pli._prepare_discount_line_values_from_campaign_rule()
            pli.discount_line_id.write(discount_line_values)
        self.discount_id.izi_push()
        return self.discount_id.mp_push()


class CampaignMarketplaceDiscountWizard(models.TransientModel):
    _name = 'wizard.juragan.campaign.mp_discount'
    _inherit = 'product.pricelist.item'
    _description = 'Juragan Campaign Marketplace Discount Wizard'

    MODES = [
        ('set_datetime', 'Set Datetime')
    ]

    set_mode = fields.Selection(string="Mode", selection=MODES, required=False)
    campaign_id = fields.Many2one(comodel_name="juragan.campaign", string="Campaign", required=True)
    mp_id = fields.Reference(BaseJuraganCampaign.MP_TYPES, string='Marketplace', required=True)
    applied_on = fields.Selection(
        [('5_products', 'Select Multi Products'), ('1_product', 'Single Product')], "Apply On", default='1_product',
        required=True, help='Pricelist Item applicable on selected option')
    product_tmpl_ids = fields.Many2many(comodel_name="product.template", relation="pli_mp_discount_product_tmpl_rel",
                                        column1="pricelist_item_id", column2="product_tmpl_id", string="Products")
    compute_price = fields.Selection([('fixed', 'Fix Price'), ('percentage', 'Percentage (discount)')], index=True,
                                     default='fixed')

    @api.model
    def default_get(self, fields_list):
        res = super(CampaignMarketplaceDiscountWizard, self).default_get(fields_list)
        if 'campaign_id' in res:
            campaign = self.env['juragan.campaign'].browse(res['campaign_id'])
            res_values = campaign.read([
                'campaign_purpose',
                'set_mode', 'set_datetime', 'date_time_start', 'date_time_end',
                'set_weekday', 'time_start', 'time_end', 'weekday_tz',
                'day_0', 'day_1', 'day_2', 'day_3', 'day_4', 'day_5', 'day_6'
            ])[0]
            if campaign.mp_id:
                res_values.update({'mp_id': '%s,%s' % (campaign.mp_id._name, campaign.mp_id.id)})
            res.update(res_values)
        return res

    def add(self):
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

        for item_data in items_data:
            removed_fields = ['product_tmpl_ids']
            for removed_field in removed_fields:
                item_data.pop(removed_field)
            item_data.update({
                'campaign_id': self.campaign_id.id,
                'mp_id': '%s,%s' % (self.mp_id._name, self.mp_id.id),
                'pricelist_id': False,
                'campaign_purpose': self.campaign_purpose
            })
        values = [(0, 0, value) for value in items_data]
        self.campaign_id.write({
            'pricelist_item_ids': values
        })
        self.campaign_id.pricelist_item_ids._create_discount_lines()
