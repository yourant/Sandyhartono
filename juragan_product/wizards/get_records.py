from odoo import fields, models, api, _
from odoo.exceptions import UserError


class GetRecords(models.TransientModel):
    _name = 'wiz.get_records'
    start_offset = fields.Integer(string='Start Offset Records', default=0)
    end_offset = fields.Integer(string='End Offset Records', default=0)
    limit = fields.Integer(string='One Hit Limit Records', default=500)

    def get_record(self):
        if self.end_offset > 0:
            if self.limit > self.end_offset:
                raise UserError('If you set End Offset, End Offset must be higher from limit')
        server = self.env['webhook.server'].search([], limit=1)
        if server:
            try:
                server.get_records('product.product',
                                force_update=True,
                                domain_code='all_active',
                                offset=self.start_offset,
                                end_offset=self.end_offset,
                                limit=self.limit,
                                commit_every=100)
            except Exception as e:
                raise UserError(e)
