# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from itertools import chain

import pytz
from odoo import models, fields, api, tools
from odoo.addons.base.models.res_partner import _tz_get
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT


class Pricelist(models.Model):
    _inherit = 'product.pricelist'

    @api.model
    def _is_price_rule_weekday_today(self, rule, date_time):
        if not date_time.tzinfo:
            raise UserError("No tzinfo available in datetime object! Please input localized datetime object.")
        rule_tz = pytz.timezone(rule.weekday_tz)
        if date_time.tzinfo.zone == rule.weekday_tz:
            day_number = date_time.strftime('%w')
        else:
            day_number = date_time.astimezone(rule_tz).strftime('%w')
        return getattr(rule, 'day_%s' % day_number)

    @api.model
    def _is_price_rule_weekday_all(self, rule):
        none_selected = all([getattr(rule, 'day_%s' % day_number) is False for day_number in range(0, 7)])
        all_selected = all([getattr(rule, 'day_%s' % day_number) for day_number in range(0, 7)])
        return none_selected or all_selected

    @api.model
    def _get_price_rule_weekday_closest_date_time(self, rule, date_time, date_time_type):
        closest_date_time = date_time
        if not self._is_price_rule_weekday_all(rule):
            while not self._is_price_rule_weekday_today(rule, closest_date_time):
                closest_date_time = closest_date_time + timedelta(days=1)
        rule_tz = pytz.timezone(rule.weekday_tz)
        rule_date_time = closest_date_time.astimezone(rule_tz)
        closest_date_time_str = '{date} {time}'.format(**{
            'date': rule_date_time.strftime(DEFAULT_SERVER_DATE_FORMAT),
            'time': '{}:00'.format(getattr(rule, 'time_%s' % date_time_type))
        })
        return rule_tz.localize(datetime.strptime(closest_date_time_str, DEFAULT_SERVER_DATETIME_FORMAT))

    @api.model
    def _get_price_rules_weekday_closest_date_time(self, rules, date_time, date_time_type):
        rules_date_time = [
            (rule, self._get_price_rule_weekday_closest_date_time(rule, date_time, date_time_type).astimezone(pytz.utc))
            for rule in rules]
        rule, closest_date_time = sorted(rules_date_time, key=lambda x: x[1])[0]
        return rule, closest_date_time.astimezone(pytz.timezone(rule.weekday_tz))

    # @api.multi
    def _compute_price_rule_datetime(self, products_qty_partner, date_time=False, tz=False, uom_id=False, **kwargs):
        self.ensure_one()
        uom_obj = self.env['uom.uom']
        if not tz:
            if self._context.get('tz'):
                current_tz = pytz.timezone(self._context.get('tz'))
            else:
                current_tz = pytz.utc
        else:
            current_tz = pytz.timezone(tz)
        if not date_time:
            if not self._context.get('date_time'):
                current_date_time = pytz.utc.localize(datetime.now())
            else:
                current_date_time = current_tz.localize(self._context.get('date_time'))
        else:
            current_date_time = current_tz.localize(date_time)
        current_date_time_utc = current_date_time.astimezone(pytz.utc)
        if not uom_id and self._context.get('uom'):
            uom_id = self._context['uom']
        if uom_id:
            # rebrowse with uom if given
            products = [item[0].with_context(uom=uom_id) for item in products_qty_partner]
            products_qty_partner = [(products[index], data_struct[1], data_struct[2]) for index, data_struct in
                                    enumerate(products_qty_partner)]
        else:
            products = [item[0] for item in products_qty_partner]

        if not products:
            return {}

        categ_ids = {}
        for p in products:
            categ = p.categ_id
            while categ:
                categ_ids[categ.id] = True
                categ = categ.parent_id
        categ_ids = list(categ_ids)

        is_product_template = products[0]._name == "product.template"
        if is_product_template:
            prod_tmpl_ids = [tmpl.id for tmpl in products]
            # all variants of all products
            prod_ids = [p.id for p in
                        list(chain.from_iterable([t.product_variant_ids for t in products]))]
        else:
            prod_ids = [product.id for product in products]
            prod_tmpl_ids = [product.product_tmpl_id.id for product in products]

        date_time = current_date_time_utc.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        # Load all rules
        self._cr.execute(
            'SELECT item.id '
            'FROM product_pricelist_item AS item '
            'LEFT JOIN product_category AS categ '
            'ON item.categ_id = categ.id '
            'WHERE (item.product_tmpl_id IS NULL OR item.product_tmpl_id = any(%s))'
            'AND (item.product_id IS NULL OR item.product_id = any(%s))'
            'AND (item.categ_id IS NULL OR item.categ_id = any(%s)) '
            'AND (item.pricelist_id = %s) '
            'AND (item.set_datetime = TRUE) '
            'AND (item.date_time_start<=%s) '
            'AND (item.date_time_end>=%s)'
            'ORDER BY item.applied_on, item.min_quantity desc, categ.complete_name desc, item.id desc',
            (prod_tmpl_ids, prod_ids, categ_ids, self.id, date_time, date_time))

        item_ids = [x[0] for x in self._cr.fetchall()]
        items = self.env['product.pricelist.item'].browse(item_ids)
        results = {}
        for product, qty, partner in products_qty_partner:
            results[product.id] = 0.0
            suitable_rule = False

            # Final unit price is computed according to `qty` in the `qty_uom_id` UoM.
            # An intermediary unit price may be computed according to a different UoM, in
            # which case the price_uom_id contains that UoM.
            # The final price will be converted to match `qty_uom_id`.
            qty_uom_id = self._context.get('uom') or product.uom_id.id
            price_uom_id = product.uom_id.id
            qty_in_product_uom = qty
            if qty_uom_id != product.uom_id.id:
                try:
                    qty_in_product_uom = uom_obj.browse([self._context['uom']])._compute_quantity(qty, product.uom_id)
                except UserError:
                    # Ignored - incompatible UoM in context, use default product UoM
                    pass

            # if Public user try to access standard price from website sale, need to call price_compute.
            # TDE SURPRISE: product can actually be a template
            price = product.price_compute('list_price')[product.id]

            price_uom = uom_obj.browse([qty_uom_id])
            for rule in items:
                if rule.min_quantity and qty_in_product_uom < rule.min_quantity:
                    continue
                if is_product_template:
                    if rule.product_tmpl_id and product.id != rule.product_tmpl_id.id:
                        continue
                    if rule.product_id and not (
                            product.product_variant_count == 1 and product.product_variant_id.id == rule.product_id.id):
                        # product rule acceptable on template if has only one variant
                        continue
                else:
                    if rule.product_tmpl_id and product.product_tmpl_id.id != rule.product_tmpl_id.id:
                        continue
                    if rule.product_id and product.id != rule.product_id.id:
                        continue

                if rule.categ_id:
                    cat = product.categ_id
                    while cat:
                        if cat.id == rule.categ_id.id:
                            break
                        cat = cat.parent_id
                    if not cat:
                        continue

                if rule.base == 'pricelist' and rule.base_pricelist_id:
                    price_tmp = \
                        rule.base_pricelist_id._compute_price_rule([(product, qty, partner)], current_date_time.date(),
                                                                   uom_id)[product.id][0]  # TDE: 0 = price, 1 = rule
                    price = rule.base_pricelist_id.currency_id.compute(price_tmp, self.currency_id, round=False)
                else:
                    # if base option is public price take sale price else cost price of product
                    # price_compute returns the price in the context UoM, i.e. qty_uom_id
                    price = product.price_compute(rule.base)[product.id]

                convert_to_price_uom = (lambda product_price: product.uom_id._compute_price(product_price, price_uom))

                if price is not False:
                    if rule.compute_price == 'fixed':
                        price = convert_to_price_uom(rule.fixed_price)
                    elif rule.compute_price == 'percentage':
                        price = (price - (price * (rule.percent_price / 100))) or 0.0
                    else:
                        # complete formula
                        price_limit = price
                        price = (price - (price * (rule.price_discount / 100))) or 0.0
                        if rule.price_round:
                            price = tools.float_round(price, precision_rounding=rule.price_round)

                        if rule.price_surcharge:
                            price_surcharge = convert_to_price_uom(rule.price_surcharge)
                            price += price_surcharge

                        if rule.price_min_margin:
                            price_min_margin = convert_to_price_uom(rule.price_min_margin)
                            price = max(price, price_limit + price_min_margin)

                        if rule.price_max_margin:
                            price_max_margin = convert_to_price_uom(rule.price_max_margin)
                            price = min(price, price_limit + price_max_margin)
                    suitable_rule = rule
                break
            # Final price conversion into pricelist currency
            if suitable_rule and suitable_rule.compute_price != 'fixed' and suitable_rule.base != 'pricelist':
                if suitable_rule.base == 'standard_price':
                    # The cost of the product is always in the company currency
                    price = product.cost_currency_id.compute(price, self.currency_id, round=False)
                else:
                    price = product.currency_id.compute(price, self.currency_id, round=False)

            results[product.id] = (price, suitable_rule and suitable_rule.id or False)

        return results

    # @api.multi
    def _compute_price_rule_weekday(self, products_qty_partner, date_time=False, tz=False, uom_id=False, **kwargs):
        self.ensure_one()
        pricelist_item_obj = self.env['product.pricelist.item']
        uom_obj = self.env['uom.uom']
        if not tz:
            if self._context.get('tz'):
                current_tz = pytz.timezone(self._context.get('tz'))
            else:
                current_tz = pytz.utc
        else:
            current_tz = pytz.timezone(tz)
        if not date_time:
            if not self._context.get('date_time'):
                current_date_time = pytz.utc.localize(datetime.now())
            else:
                current_date_time = current_tz.localize(self._context.get('date_time'))
        else:
            current_date_time = current_tz.localize(date_time)
        if not uom_id and self._context.get('uom'):
            uom_id = self._context['uom']
        if uom_id:
            # rebrowse with uom if given
            products = [item[0].with_context(uom=uom_id) for item in products_qty_partner]
            products_qty_partner = [(products[index], data_struct[1], data_struct[2]) for index, data_struct in
                                    enumerate(products_qty_partner)]
        else:
            products = [item[0] for item in products_qty_partner]

        if not products:
            return {}

        categ_ids = {}
        for p in products:
            categ = p.categ_id
            while categ:
                categ_ids[categ.id] = True
                categ = categ.parent_id
        categ_ids = list(categ_ids)

        is_product_template = products[0]._name == "product.template"
        if is_product_template:
            prod_tmpl_ids = [tmpl.id for tmpl in products]
            # all variants of all products
            prod_ids = [p.id for p in
                        list(chain.from_iterable([t.product_variant_ids for t in products]))]
        else:
            prod_ids = [product.id for product in products]
            prod_tmpl_ids = [product.product_tmpl_id.id for product in products]

        # Load all rules
        self._cr.execute(
            'SELECT item.id '
            'FROM product_pricelist_item AS item '
            'LEFT JOIN product_category AS categ '
            'ON item.categ_id = categ.id '
            'WHERE (item.product_tmpl_id IS NULL OR item.product_tmpl_id = any(%s))'
            'AND (item.product_id IS NULL OR item.product_id = any(%s))'
            'AND (item.categ_id IS NULL OR item.categ_id = any(%s)) '
            'AND (item.pricelist_id = %s) '
            'AND (item.set_weekday = TRUE) '
            'ORDER BY item.applied_on, item.min_quantity desc, categ.complete_name desc, item.id desc',
            (prod_tmpl_ids, prod_ids, categ_ids, self.id))

        item_ids = [x[0] for x in self._cr.fetchall()]
        items = pricelist_item_obj.browse(item_ids)
        results = {}
        suitable_rules = pricelist_item_obj
        for rule in items:
            if not self._is_price_rule_weekday_all(rule):
                if not self._is_price_rule_weekday_today(rule, current_date_time):
                    continue
            rule_tz = pytz.timezone(rule.weekday_tz)
            start_time_str = '{date} {time}'.format(**{
                'date': current_date_time.strftime(DEFAULT_SERVER_DATE_FORMAT),
                'time': '{}:00'.format(rule.time_start)
            })
            end_time_str = '{date} {time}'.format(**{
                'date': current_date_time.strftime(DEFAULT_SERVER_DATE_FORMAT),
                'time': '{}:00'.format(rule.time_end)
            })
            start_time = rule_tz.localize(datetime.strptime(start_time_str, DEFAULT_SERVER_DATETIME_FORMAT))
            end_time = rule_tz.localize(datetime.strptime(end_time_str, DEFAULT_SERVER_DATETIME_FORMAT))

            if start_time <= current_date_time.astimezone(rule_tz) <= end_time:
                suitable_rules |= rule
        for product, qty, partner in products_qty_partner:
            results[product.id] = 0.0
            suitable_rule = False

            # Final unit price is computed according to `qty` in the `qty_uom_id` UoM.
            # An intermediary unit price may be computed according to a different UoM, in
            # which case the price_uom_id contains that UoM.
            # The final price will be converted to match `qty_uom_id`.
            qty_uom_id = self._context.get('uom') or product.uom_id.id
            price_uom_id = product.uom_id.id
            qty_in_product_uom = qty
            if qty_uom_id != product.uom_id.id:
                try:
                    qty_in_product_uom = uom_obj.browse([self._context['uom']])._compute_quantity(qty, product.uom_id)
                except UserError:
                    # Ignored - incompatible UoM in context, use default product UoM
                    pass

            # if Public user try to access standard price from website sale, need to call price_compute.
            # TDE SURPRISE: product can actually be a template
            price = product.price_compute('list_price')[product.id]

            price_uom = uom_obj.browse([qty_uom_id])
            for rule in suitable_rules:
                if rule.min_quantity and qty_in_product_uom < rule.min_quantity:
                    continue
                if is_product_template:
                    if rule.product_tmpl_id and product.id != rule.product_tmpl_id.id:
                        continue
                    if rule.product_id and not (
                            product.product_variant_count == 1 and product.product_variant_id.id == rule.product_id.id):
                        # product rule acceptable on template if has only one variant
                        continue
                else:
                    if rule.product_tmpl_id and product.product_tmpl_id.id != rule.product_tmpl_id.id:
                        continue
                    if rule.product_id and product.id != rule.product_id.id:
                        continue

                if rule.categ_id:
                    cat = product.categ_id
                    while cat:
                        if cat.id == rule.categ_id.id:
                            break
                        cat = cat.parent_id
                    if not cat:
                        continue

                if rule.base == 'pricelist' and rule.base_pricelist_id:
                    price_tmp = \
                        rule.base_pricelist_id._compute_price_rule([(product, qty, partner)], current_date_time.date(),
                                                                   uom_id)[product.id][0]  # TDE: 0 = price, 1 = rule
                    price = rule.base_pricelist_id.currency_id.compute(price_tmp, self.currency_id, round=False)
                else:
                    # if base option is public price take sale price else cost price of product
                    # price_compute returns the price in the context UoM, i.e. qty_uom_id
                    price = product.price_compute(rule.base)[product.id]

                convert_to_price_uom = (lambda product_price: product.uom_id._compute_price(product_price, price_uom))

                if price is not False:
                    if rule.compute_price == 'fixed':
                        price = convert_to_price_uom(rule.fixed_price)
                    elif rule.compute_price == 'percentage':
                        price = (price - (price * (rule.percent_price / 100))) or 0.0
                    else:
                        # complete formula
                        price_limit = price
                        price = (price - (price * (rule.price_discount / 100))) or 0.0
                        if rule.price_round:
                            price = tools.float_round(price, precision_rounding=rule.price_round)

                        if rule.price_surcharge:
                            price_surcharge = convert_to_price_uom(rule.price_surcharge)
                            price += price_surcharge

                        if rule.price_min_margin:
                            price_min_margin = convert_to_price_uom(rule.price_min_margin)
                            price = max(price, price_limit + price_min_margin)

                        if rule.price_max_margin:
                            price_max_margin = convert_to_price_uom(rule.price_max_margin)
                            price = min(price, price_limit + price_max_margin)
                    suitable_rule = rule
                break
            # Final price conversion into pricelist currency
            if suitable_rule and suitable_rule.compute_price != 'fixed' and suitable_rule.base != 'pricelist':
                if suitable_rule.base == 'standard_price':
                    # The cost of the product is always in the company currency
                    price = product.cost_currency_id.compute(price, self.currency_id, round=False)
                else:
                    price = product.currency_id.compute(price, self.currency_id, round=False)

            results[product.id] = (price, suitable_rule and suitable_rule.id or False)
        return results

    # @api.multi
    def _recompute_price_rule(self, previous_result, products_qty_partner, date=False, uom_id=False, compute=False):
        if not compute:
            compute = super(Pricelist, self)._compute_price_rule
        results = previous_result.copy()
        for product_id, price_rule in previous_result.items():
            price, rule = price_rule
            if not rule:
                results.update(compute(products_qty_partner, date=date, uom_id=uom_id))
        return results

    # @api.multi
    def _compute_price_rule(self, products_qty_partner, date=False, uom_id=False):
        self.ensure_one()
        set_datetime = any(self.item_ids.mapped('set_datetime'))
        set_weekday = any(self.item_ids.mapped('set_weekday'))
        if any([set_datetime, set_weekday]):
            res = self._compute_price_rule_datetime(products_qty_partner, uom_id=uom_id)
            res = self._recompute_price_rule(res, products_qty_partner, uom_id=uom_id,
                                             compute=self._compute_price_rule_weekday)
            return res
        return super(Pricelist, self)._compute_price_rule(products_qty_partner, date, uom_id)


class PricelistItem(models.Model):
    _inherit = 'product.pricelist.item'

    MODES = [
        ('set_datetime', 'Set Datetime'),
        ('set_weekday', 'Set Weekday'),
    ]

    # TODO: Until we can handle the combination of set_datetime and set_weekday, this selection will still remain.
    set_mode = fields.Selection(string="Mode", selection=MODES, required=False)
    set_datetime = fields.Boolean(string="Set Datetime?")
    date_time_start = fields.Datetime(string="Start Datetime")
    date_time_end = fields.Datetime(string="End Datetime")
    set_weekday = fields.Boolean(string="Set Weekday?")
    time_start = fields.Char(string="Start Time", default="00:00")
    time_end = fields.Char(string="End Time", default="23:59")
    weekday_tz = fields.Selection(_tz_get, string='Timezone', default=lambda self: self._context.get('tz'))
    day_0 = fields.Boolean(string="Sunday")
    day_1 = fields.Boolean(string="Monday")
    day_2 = fields.Boolean(string="Tuesday")
    day_3 = fields.Boolean(string="Wednesday")
    day_4 = fields.Boolean(string="Thursday")
    day_5 = fields.Boolean(string="Friday")
    day_6 = fields.Boolean(string="Saturday")

    @api.onchange('set_mode')
    def change_set_mode(self):
        self.set_datetime = self.set_mode == 'set_datetime'
        self.set_weekday = self.set_mode == 'set_weekday'
