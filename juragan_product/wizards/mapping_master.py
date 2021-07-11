from odoo import fields, models, api, _
from odoo.exceptions import UserError


class MappingMasterWizard(models.TransientModel):
    _name = 'mapping.master.wizard'

    is_name = fields.Boolean('Name', default=True)
    is_default_code = fields.Boolean('Default Code', default=True)
    is_description_sale = fields.Boolean('Description Sale', default=True)
    is_list_price = fields.Boolean('List Price', default=True)
    is_qty_available = fields.Boolean('Qty Available', default=True)
    is_min_order = fields.Boolean('Min Order', default=True)
    is_weight = fields.Boolean('Weight', default=True)
    is_length = fields.Boolean('length', default=True)
    is_width = fields.Boolean('Width', default=True)
    is_height = fields.Boolean('Height', default=True)

    name = fields.Char('Name')
    default_code = fields.Char('Default Code')
    description_sale = fields.Text('Description Sale')
    list_price = fields.Float('List Price')
    qty_available = fields.Integer('Qty Available')
    min_order = fields.Integer('Min Order')
    weight = fields.Float('Weight')
    length = fields.Integer('Length')
    width = fields.Integer('Width')
    height = fields.Integer('Height')

    def do_mapping_fields(self):
        product_tmpl_id = self.env['product.template'].search(
            [('id', '=', self._context.get('product_tmpl_id', []))])
        
        if product_tmpl_id:
            for product_staging_id in product_tmpl_id.product_staging_ids:
                values = {}
                if self.is_name:
                    values['name'] = self.name
                if self.is_default_code:
                    values['default_code'] = self.default_code
                if self.is_description_sale:
                    values['description_sale'] = self.description_sale
                if self.is_list_price:
                    values['list_price'] = self.list_price
                if self.is_min_order:
                    values['min_order'] = self.min_order
                if self.is_weight:
                    weight = self.weight
                    if product_staging_id.mp_shopee_id:
                        weight = weight / 1000
                    values['weight'] = weight
                if self.is_length:
                    values['length'] = self.length
                if self.is_width:
                    values['width'] = self.width
                if self.is_height:
                    values['height'] = self.height
                
                product_tmpl_id.write(values)
                product_staging_id.write(values)

                if self.is_qty_available:
                    stock_location = self.env['stock.location']
                    if product_staging_id.mp_tokopedia_id:
                        if self.qty_available < 0:
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
                    if not stock_location:
                        raise UserError("Source location is not defined, please set the default source location for each "
                                        "marketplace account!")
                    if len(product_staging_id.product_variant_stg_ids) == 0:
                        if product_staging_id.qty_available != self.qty_available:
                            product_id = product_staging_id.product_template_id.product_variant_id.id
                            stock_inventory = self.env['stock.inventory'].create({
                                'name': product_staging_id.product_template_id.product_variant_id.display_name,
                                'location_ids': [(6, 0, stock_location.ids)],
                                'product_ids': [(6, 0, [product_id])],
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