from odoo import fields, models, api, _
from odoo.exceptions import UserError


class StagingStockWizard(models.TransientModel):
    _name = 'staging.stock.wizard'
    qty_available = fields.Integer('Qty Available')

    def do_update_stock(self):
        product_staging_id = self.env['product.staging'].search(
            [('id', '=', self._context.get('product_staging_id', []))])
        default_loc = self.env['stock.inventory']._default_location_id()
        stock_location = self.env['stock.location'].browse(default_loc)
        if product_staging_id.mp_tokopedia_id:
            if self.qty_available < 1:
                raise UserError('You cannot set less than 1 quantity')
            stock_location = product_staging_id.mp_tokopedia_id.wh_id.lot_stock_id
            if not stock_location:
                stock_location = product_staging_id.product_template_id.mp_tokopedia_ids.wh_id.lot_stock_id
        elif product_staging_id.mp_shopee_id:
            stock_location = product_staging_id.mp_shopee_id.wh_id.lot_stock_id
            if not stock_location:
                stock_location = product_staging_id.product_template_id.mp_shopee_ids.wh_id.lot_stock_id
        elif product_staging_id.mp_lazada_id:
            stock_location = product_staging_id.mp_lazada_id.wh_id.lot_stock_id
            if not stock_location:
                stock_location = product_staging_id.product_template_id.mp_lazada_ids.wh_id.lot_stock_id
        if len(product_staging_id.product_variant_stg_ids) == 0:
            if product_staging_id.qty_available != self.qty_available:
                product_id = product_staging_id.product_template_id.product_variant_id.id
                stock_inventory = self.env['stock.inventory'].create({
                    'name': product_staging_id.product_template_id.product_variant_id.display_name,
                    'location_id': stock_location.id,
                    'product_id': product_id,
                    'filter': 'product',
                    'line_ids': [(0, 0, {
                        'product_id': product_id,
                        'location_id': stock_location.id,
                        'product_qty': self.qty_available,
                    })]
                })
                try:
                    stock_inventory.action_start()
                    stock_inventory.action_validate()
                except Exception as e:
                    stock_inventory.unlink()
                    raise UserError(str(e))
               

class StagingVariantStockWizard(models.TransientModel):
    _name = 'staging.variant.stock.wizard'
    qty_available = fields.Integer('Qty Available')

    def do_update_stock(self):
        product_staging_variant_id = self.env['product.staging.variant'].search(
            [('id', '=', self._context.get('product_staging_variant_id', []))])
        default_loc = self.env['stock.inventory']._default_location_id()
        stock_location = self.env['stock.location'].browse(default_loc)
        if product_staging_variant_id.product_stg_id.mp_tokopedia_id:
            if self.qty_available < 1:
                raise UserError('You cannot set less than 1 quantity')
            stock_location = product_staging_variant_id.product_stg_id.mp_tokopedia_id.wh_id.lot_stock_id
            if not stock_location:
                stock_location = product_staging_variant_id.product_stg_id.product_template_id.mp_tokopedia_ids.wh_id.lot_stock_id
        elif product_staging_variant_id.product_stg_id.mp_shopee_id:
            stock_location = product_staging_variant_id.product_stg_id.mp_shopee_id.wh_id.lot_stock_id
            if not stock_location:
                stock_location = product_staging_variant_id.product_stg_id.product_template_id.mp_shopee_ids.wh_id.lot_stock_id
        elif product_staging_variant_id.product_stg_id.mp_lazada_id:
            stock_location = product_staging_variant_id.product_stg_id.mp_lazada_id.wh_id.lot_stock_id
            if not stock_location:
                stock_location = product_staging_variant_id.product_stg_id.product_template_id.mp_lazada_ids.wh_id.lot_stock_id

        if product_staging_variant_id.qty_available != self.qty_available:
            product_id = product_staging_variant_id.product_id.id
            stock_inventory = self.env['stock.inventory'].create({
                'name': product_staging_variant_id.product_id.display_name,
                'location_id': stock_location.id,
                'product_id': product_id,
                'filter': 'product',
                'line_ids': [(0, 0, {
                    'product_id': product_id,
                    'location_id': stock_location.id,
                    'product_qty': self.qty_available,
                })]
            })
            try:
                stock_inventory.action_start()
                stock_inventory.action_validate()
            except Exception as e:
                stock_inventory.unlink()
                raise UserError(str(e))
