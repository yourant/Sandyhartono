from odoo import api, fields, models

from odoo.addons.juragan_webhook import BigInteger


class MPProductDiscount(models.Model):
    _inherit = 'mp.product.discount'

    TOKOPEDIA_DISCOUNT_STATUS = [
        ('ACTIVE', 'ACTIVE'),
        ('INACTIVE', 'INACTIVE'),
        ('COMING SOON', 'COMING SOON'),
        ('REDIRECTED', 'REDIRECTED')
    ]

    TOKOPEDIA_DISCOUNT_TYPE = [
        ('1', 'Slash Price'),
    ]

    mp_tokopedia_id = fields.Many2one('mp.tokopedia', string='Tokopedia Account')
    tp_discount_type = fields.Selection(TOKOPEDIA_DISCOUNT_TYPE)
    tp_discount_status = fields.Selection(TOKOPEDIA_DISCOUNT_STATUS)


class MPProductDiscountLine(models.Model):
    _inherit = 'mp.product.discount.line'

    tp_remaining_quota = fields.Integer(string='Tokopedia Remaining Quota')
    tp_join_flashsale = fields.Boolean('Join Flash Sale')
    tp_use_warehouse = fields.Boolean('Use Warehouse')
    tp_warehouse_id = BigInteger()
    tp_event_id = BigInteger()
