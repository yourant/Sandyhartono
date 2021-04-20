# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.addons.juragan_webhook import BigMany2one, BigInteger
from odoo.exceptions import ValidationError


SHOP_STATUS = [
    ('0', 'Deleted'),
    ('1', 'Open'),
    ('2', 'Closed'),
    ('3', 'Moderated'),
    ('4', 'Inactive'),
    ('5', 'Moderated Permanently'),
    ('6', 'Incubate'),
    ('7', 'Schedule Active'),
]


class MPBigInt(models.AbstractModel):
    _name = 'mp.bigint'
    _description = 'Marketplace Big Integer ID'

    # @api.model_cr
    def init(self, columns=['id']):
        if self._is_an_ordinary_table():
            for column in columns:
                self._cr.execute('''
                    ALTER TABLE %(table)s
                    ALTER COLUMN %(column)s TYPE bigint
                    USING %(column)s::bigint;
                ''' % {
                    'table': self._table,
                    'column': column
                })


class MPTokopedia(models.Model):
    _name = 'mp.tokopedia'
    _description = 'Tokopedia Account'
    _order = 'active desc, name'

    name = fields.Char(readonly=True, )
    tp_user = fields.Char('Email', readonly=True, )
    active = fields.Boolean()
    shop_ids = fields.One2many('mp.tokopedia.shop', 'mp_id', string='Shop')
    wh_id = fields.Many2one(
        'stock.warehouse', string='Warehouse',)
    izi_id = fields.Integer('Izi ID')
    izi_md5 = fields.Char()

    def name_get(self):
        result = []
        for this in self:
            name = (not this.active and '[ Inactive ] ' or '') + str(this.tp_user or '')
            if this.name:
                name = '{} [{}]'.format(name, this.name)
            result.append((this.id, name))
        return result


class MPTokopediaCategory(models.Model):
    _name = 'mp.tokopedia.category'
    _description = 'Tokopedia Category'
    _rec_name = 'complete_name'
    _order = 'path'

    name = fields.Char(index=True, )
    complete_name = fields.Char()
    parent_id = fields.Many2one(
        'mp.tokopedia.category',
        'Parent Category', index=True, ondelete='cascade')
    child_ids = fields.One2many(
        'mp.tokopedia.category', 'parent_id', 'Child Categories')
    path = fields.Char()
    variants = fields.Many2many(
        'mp.tokopedia.category.variant',
        'mp_tokopedia_category_mp_tokopedia_category_variant_rel')
    prdc_ids = fields.One2many(
        'product.category', 'mp_tokopedia_category_id', 'Odoo Category')
    active = fields.Boolean(default=True)

    izi_id = fields.Integer('Izi ID')
    izi_md5 = fields.Char()

    @api.constrains('parent_id')
    def _check_parent_id(self):
        if not self._check_recursion():
            raise ValidationError(_(
                'You cannot create recursive departments.'))


class MPTokopediaCategoryValue(models.Model):
    _name = 'mp.tokopedia.category.value'
    _description = 'Tokopedia Category Value'
    _rec_name = 'value'

    value_id = fields.Many2one('mp.tokopedia.category.value')
    value = fields.Char()
    units = fields.Many2many('mp.tokopedia.category.unit', 'mp_tokopedia_category_unit_mp_tokopedia_category_value_rel')
    # hex_code = fields.Char()
    # icon = fields.Char()

    izi_id = fields.Integer('Izi ID')
    izi_md5 = fields.Char()


class MPTokopediaCategoryUnit(models.Model):
    _name = 'mp.tokopedia.category.unit'
    _description = 'Tokopedia Category Unit'

    unit_id = fields.Many2one(
        'mp.tokopedia.category.unit')
    name = fields.Char()
    # short_name = fields.Char()
    values = fields.Many2many(
        'mp.tokopedia.category.value',
        'mp_tokopedia_category_unit_mp_tokopedia_category_value_rel')
    variants = fields.Many2many(
        'mp.tokopedia.category.variant',
        'mp_tokopedia_category_variant_mp_tokopedia_category_unit_rel')
    variant_values = fields.Many2many(
        'mp.tokopedia.variant.value',
        'mp_tokopedia_category_unit_mp_tokopedia_variant_value_rel')

    izi_id = fields.Integer('Izi ID')
    izi_md5 = fields.Char()


class MPTokopediaCategoryVariant(models.Model):
    _name = 'mp.tokopedia.category.variant'
    _description = 'Tokopedia Category Variant'

    variant_id = fields.Many2one(
        'mp.tokopedia.category.variant')
    name = fields.Char()
    # identifier = fields.Char()
    # status = fields.Integer()
    # has_unit = fields.Integer()
    units = fields.Many2many('mp.tokopedia.category.unit', 'mp_tokopedia_category_variant_mp_tokopedia_category_unit_rel')

    categories = fields.Many2many(
        'mp.tokopedia.category',
        'mp_tokopedia_category_mp_tokopedia_category_variant_rel')

    izi_id = fields.Integer('Izi ID')
    izi_md5 = fields.Char()


class MPTokopediaEtalase(models.Model):
    _name = 'mp.tokopedia.etalase'
    _inherit = 'mp.bigint'
    _description = 'Tokopedia Etalase'
    _rec_name = 'etalase_name'

    etalase_id = BigMany2one('mp.tokopedia.etalase', readonly=True)
    etalase_name = fields.Char()
    # url = fields.Text()
    shop_id = BigMany2one(
        'mp.tokopedia.shop', ondelete='cascade',
        domain="[('mp_id','=',mp_id), ]")
    mp_id = fields.Many2one(
        'mp.tokopedia', string='Account', ondelete='cascade')
    active = fields.Boolean(default=True)

    izi_id = fields.Integer('Izi ID')
    izi_md5 = fields.Char()


class MPTokopediaShop(models.Model):
    _name = 'mp.tokopedia.shop'
    _inherit = 'mp.bigint'
    _description = 'Tokopedia Shop'
    _rec_name = 'shop_name'

    shop_id = BigMany2one('mp.tokopedia.shop', readonly=True, )
    user_id = BigInteger('User ID')
    shop_name = fields.Char()
    # logo = fields.Text()
    # shop_url = fields.Text()
    is_open = fields.Selection([
        ('0', 'Closed'),
        ('1', 'Open'),
    ])
    status = fields.Selection(SHOP_STATUS)
    # date_shop_created = fields.Date()
    # domain = fields.Char()
    # reason = fields.Char()

    district_id = fields.Char()
    # owner_id = fields.Char()
    province_name = fields.Char()
    subscribe_tokocabang = fields.Char()
    # warehouses = fields.Char()

    mp_id = fields.Many2one(
        'mp.tokopedia', string='Account', ondelete='cascade', )
    wh_id = fields.Many2one(
        'stock.warehouse', string='Warehouse', related='mp_id.wh_id')
    active = fields.Boolean(default=True)

    izi_id = fields.Integer('Izi ID')
    izi_md5 = fields.Char()


class MPTokopediaProductWsl(models.Model):
    _name = 'mp.tokopedia.product.wsl'
    _description = 'Tokopedia Product Wholesale'

    min_qty = BigInteger()
    price = BigInteger()
    active = fields.Boolean(default=True)
    izi_id = fields.Integer('Izi ID')
    izi_md5 = fields.Char()


# class WebhookServer(models.Model):
#     _inherit = 'webhook.server'

#     def get_mp_tokopedia(self, retry_login=True):
#         try:
#             if not self.session_id:
#                 self.retry_login(3)
#             r = requests.get(self.name + '/api/ui/read/list-detail/izi-mp-tokopedia', headers={
#                 'X-Openerp-Session-Id': self.session_id,
#             })
#             res = json.loads(r.text) if r.status_code == 200 else {}
#             if res['code'] == 401:
#                 if retry_login:
#                     self.retry_login(3)
#                     self.get_orders(retry_login=False)
#             if res['code'] == 200:
#                 MpTokopedia = self.env['mp.tokopedia'].sudo()
#                 for res_order_values in res['data']:
#                     res_values = self.mapping_field('sale.order', res_order_values)
#                     SaleOrder.create(res_values)
#         except Exception as e:
#             pass
