# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models


class WizardRecomputeMarketplaceExternalID(models.TransientModel):
    _name = 'wiz.recompute_mpxid'
    _description = 'Recompute Marketplace External ID Wizard'

    model_ids = fields.Many2many(comodel_name="ir.model", string="Objects", readonly=True)

    def _filter_models(self, model):
        obj = self.env[model.model]
        return obj._rec_mp_external_id is not None

    @api.model
    def default_get(self, fields_list):
        model_obj = self.env['ir.model']
        mp_base_obj = self.env['mp.base']

        mp_base_model_names = list(mp_base_obj._inherit_children)
        mp_base_models = model_obj.search([('model', 'in', mp_base_model_names)]).filtered(
            lambda m: self._filter_models(m))

        res = super(WizardRecomputeMarketplaceExternalID, self).default_get(fields_list)
        res.update({
            'model_ids': [(6, 0, mp_base_models.ids)]
        })
        return res

    def action_recompute(self):
        for model in self.model_ids:
            obj = self.env[model.model]
            records = obj.search([])

            need_recompute_field = obj._fields.get('mp_external_id')

            # Prepare recompute
            records._recompute_todo(need_recompute_field)

            # Do recompute
            obj.recompute()

            # Finish recompute
            records._recompute_done(need_recompute_field)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
