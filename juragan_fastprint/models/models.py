# -*- coding: utf-8 -*-

from odoo import models, fields, api


class JuraganFastprintInit(models.AbstractModel):
    _name = 'juragan.fastprint.init'
    _description = 'Juragan Fastprint Init'
    
    @api.model
    def run(self):
        set_obj = self.env['res.config.settings']
        
        set_obj.create({
            'group_product_pricelist': True,
            'group_product_variant': True,
            'product_pricelist_setting': 'basic',
        }).execute()
