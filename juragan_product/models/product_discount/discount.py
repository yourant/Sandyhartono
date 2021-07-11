# -*- coding: utf-8 -*-
from odoo import api, fields, models

from odoo.addons.juragan_webhook import BigInteger
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
from dateutil import tz

import requests



class MPProductDiscount(models.Model):
    _name = 'mp.product.discount'

    DISCOUNT_STATE = [
        ('coming_soon', 'Coming Soon'),
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('redirected', 'Redirected'),
    ]

    # Special IZI fields
    izi_id = fields.Integer('IZI ID')
    izi_md5 = fields.Char()

    name = fields.Char(string='Discount Name')
    date_time_start = fields.Datetime(string='Discount Start Time')
    date_time_end = fields.Datetime(string='Discount End Time')
    mp_external_id = BigInteger(string='Discount ID')
    product_ids = fields.One2many('mp.product.discount.line', 'discount_id', string='Product')
    is_uploaded = fields.Boolean('Is Uploaded', default=False)
    discount_state = fields.Selection(DISCOUNT_STATE, compute='_compute_discount_status', store=True)
    end_discount = fields.Boolean('End Discount', default=False)

    @api.depends('discount_state', 'sp_discount_status', 'tp_discount_status', 'mp_shopee_id', 'mp_tokopedia_id')
    def _compute_discount_status(self):
        for discount in self:
            if discount.mp_tokopedia_id:
                tokopedia_discount_status = discount.tp_discount_status
                if tokopedia_discount_status in ['ACTIVE']:
                    discount_status = 'active'
                if tokopedia_discount_status in ['INACTIVE']:
                    discount_status = 'inactive'
                if tokopedia_discount_status in ['COMING SOON']:
                    discount_status = 'coming_soon'
                if tokopedia_discount_status in ['REDIRECTED']:
                    discount_status = 'redirected'
            elif discount.mp_shopee_id:
                shopee_discount_status = discount.sp_discount_status
                if shopee_discount_status in ['ongoing']:
                    discount_status = 'active'
                if shopee_discount_status in ['expired']:
                    discount_status = 'inactive'
                if shopee_discount_status in ['upcoming']:
                    discount_status = 'coming_soon'

            # Set Status
            discount.discount_state = discount_status
    
    def _set_tz(self, date_string, tz_from, tz_to):
        res = date_string
        if date_string:
            res = fields.Datetime.from_string(date_string).replace(tzinfo=tz.gettz(tz_from))
            res = res.astimezone(tz.gettz(tz_to))
            res = res.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        return res

    def izi_push(self):
        response_fields_from_izi = ['product_ids']
        server = self.env['webhook.server'].search(
            [('active', 'in', [False, True])],
            limit=1, order='write_date desc')

        if not server:
            form_view = self.env.ref('juragan_product.popup_message_wizard')
            view_id = form_view and form_view.id or False
            context = dict(self._context or {})
            context['message'] = 'Buatkan minimal 1 webhook server!'
            return {
                'name': 'Opps, Something Went Wrong.',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'view_type': 'form',
                'res_model': 'popup.message.wizard',
                'views': [(view_id,'form')],
                'view_id' : form_view.id,
                'target': 'new',
                'context': context,
            }
            
        json_data = {
            "id": self.izi_id,
            "name": self.name,
            "date_time_start": self._set_tz(self.date_time_start, 'UTC', self.env.user.tz),
            "date_time_end": self._set_tz(self.date_time_end, 'UTC', self.env.user.tz),
            "mp_external_id": self.mp_external_id,
            "is_uploaded": self.is_uploaded,
            "end_discount": self.end_discount,

            "mp_tokopedia_id": self.mp_tokopedia_id.izi_id,
            "tp_discount_status": self.tp_discount_status,
            "tp_discount_type": self.tp_discount_type,

            "mp_shopee_id": self.mp_shopee_id.izi_id,
            "tp_discount_status": self.tp_discount_status,
            "tp_discount_type": self.tp_discount_type,
        }

        discount_lines = []
        for discount_line in self.product_ids:
            discount_lines.append({
                "id": discount_line.izi_id,
                "discount_id": discount_line.discount_id.izi_id,
                "name": discount_line.name,
                "discount_percentage": discount_line.discount_percentage,
                "discounted_price": discount_line.discounted_price,
                "max_order": discount_line.max_order,
                "original_price": discount_line.original_price,
                "product_stg_id": discount_line.product_stg_id.izi_id,
                "product_stg_var_id": discount_line.product_stg_var_id.izi_id,
                "reserved_stock": discount_line.reserved_stock,
                "sp_normal_stock": discount_line.sp_normal_stock,
                "tp_event_id": discount_line.tp_event_id,
                "tp_join_flashsale": discount_line.tp_join_flashsale,
                "tp_remaining_quota": discount_line.tp_remaining_quota,
                "tp_use_warehouse": discount_line.tp_use_warehouse,
                "tp_warehouse_id": discount_line.tp_warehouse_id,
            })

        json_data.update({
            "discount_lines": discount_lines
        })

        jsondata = server.get_updated_izi_id(self, json_data)

        if self.izi_id:
            url = '{}/external/api/ui/update/mp.product.discount/{}'.format(
                server.name, self.izi_id)
            jsondata['record_was_exist'] = self.izi_id
        else:
            url = '{}/external/api/ui/create/mp.product.discount'.format(
                server.name)
        try:
            req = requests.post(
                url,
                headers={'X-Openerp-Session-Id': server.session_id},
                json=json_data)
            if req.status_code == 200:
                response = req.json()
                if response.get('code') == 200:
                    def process_response_data(mp_discount_product, response_data, response_key, server):
                        existing_data_ids = mp_discount_product[response_key]
                        response_data_ids = response_data.get(response_key)
                        if len(response_data.get(response_key)) > 0:
                            domain_url = "[('id', 'in', %s)]" % str(
                                response_data.get(response_key))
                            server.get_records(
                                mp_discount_product[response_key]._name, domain_url=domain_url, force_update=True)
                        for model_data_response in existing_data_ids:
                            if model_data_response.izi_id not in response_data_ids:
                                if model_data_response._fields.get('active') != None:
                                    if not model_data_response._fields.get('active').related:
                                        model_data_response.active = False
                                    else:
                                        model_data_response.unlink()
                                else:
                                    model_data_response.unlink()
                            elif model_data_response.izi_id == 0 or model_data_response.izi_id == False:
                                model_data_response.unlink()

                    response_data = response.get('data')
                    self.izi_id = response_data.get('id')

                    # get product staging by izi_id
                    domain_url = "[('id', 'in', [%s])]" % str(
                        response_data.get('id'))
                    server.get_records(
                        'mp.product.discount', domain_url=domain_url, force_update=True)

                    for response_field in response_fields_from_izi:
                        if response_field in response_data:
                            process_response_data(mp_discount_product=self, response_data=response_data, response_key=response_field, server=server)
        except Exception as e:
            form_view = self.env.ref('juragan_product.popup_message_wizard')
            view_id = form_view and form_view.id or False
            context = dict(self._context or {})
            context['message'] = str(e)
            return {
                'name': 'Opps, Something Went Wrong.',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'view_type': 'form',
                'res_model': 'popup.message.wizard',
                'views': [(view_id,'form')],
                'view_id' : form_view.id,
                'target': 'new',
                'context': context,
            }
        return True

    def mp_push(self):
        server = self.env['webhook.server'].search(
            [('active', 'in', [False, True])],
            limit=1, order='write_date desc')
        if not server:
            form_view = self.env.ref('juragan_product.popup_message_wizard')
            view_id = form_view and form_view.id or False
            context = dict(self._context or {})
            context['message'] = 'Buatkan minimal 1 webhook server!'
            return {
                'name': 'Opps, Something Went Wrong.',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'view_type': 'form',
                'res_model': 'popup.message.wizard',
                'views': [(view_id, 'form')],
                'view_id': form_view.id,
                'target': 'new',
                'context': context,
            }

        json_data = {
            "mp_product_discount_id": self.izi_id,
        }

        url = '{}/ui/product_discount/export'.format(server.name)

        try:
            req = requests.post(
                url,
                headers={'X-Openerp-Session-Id': server.session_id},
                json=json_data)
            if req.status_code == 200:
                response = req.json()
                if response.get('result').get('code') != 200:
                    form_view = self.env.ref('juragan_product.popup_message_wizard')
                    view_id = form_view and form_view.id or False
                    context = dict(self._context or {})
                    context['message'] = str(response.get('result').get('data').get('error_descrip'))
                    return {
                        'name': response.get('result').get('data').get('error'),
                        'type': 'ir.actions.act_window',
                        'view_mode': 'form',
                        'view_type': 'form',
                        'res_model': 'popup.message.wizard',
                        'views': [(view_id, 'form')],
                        'view_id': form_view.id,
                        'target': 'new',
                        'context': context,
                    }
            else:
                form_view = self.env.ref('juragan_product.popup_message_wizard')
                view_id = form_view and form_view.id or False
                context = dict(self._context or {})
                context['message'] = str()
                return {
                    'name': 'Opps, Something Went Wrong.',
                    'type': 'ir.actions.act_window',
                    'view_mode': 'form',
                    'view_type': 'form',
                    'res_model': 'popup.message.wizard',
                    'views': [(view_id, 'form')],
                    'view_id': form_view.id,
                    'target': 'new',
                    'context': context,
                }
        except Exception as e:
            form_view = self.env.ref('juragan_product.popup_message_wizard')
            view_id = form_view and form_view.id or False
            context = dict(self._context or {})
            context['message'] = str(e)
            return {
                'name': 'Opps, Something Went Wrong.',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'view_type': 'form',
                'res_model': 'popup.message.wizard',
                'views': [(view_id, 'form')],
                'view_id': form_view.id,
                'target': 'new',
                'context': context,
            }
        return True

    def mp_pull(self):
        server = self.env['webhook.server'].search(
            [('active', 'in', [False, True])],
            limit=1, order='write_date desc')
        if not server:
            form_view = self.env.ref('juragan_product.popup_message_wizard')
            view_id = form_view and form_view.id or False
            context = dict(self._context or {})
            context['message'] = 'Buatkan minimal 1 webhook server!'
            return {
                'name': 'Opps, Something Went Wrong.',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'view_type': 'form',
                'res_model': 'popup.message.wizard',
                'views': [(view_id,'form')],
                'view_id' : form_view.id,
                'target': 'new',
                'context': context,
            }
            
        json_data = {
            "mp_product_discount_id": self.izi_id,
        }

        url = '{}/ui/product_discount/import'.format(server.name)

        try:
            req = requests.post(
                url,
                headers={'X-Openerp-Session-Id': server.session_id},
                json=json_data)
            if req.status_code == 200:
                response = req.json()
                if response.get('result').get('code') != 200:
                    form_view = self.env.ref('juragan_product.popup_message_wizard')
                    view_id = form_view and form_view.id or False
                    context = dict(self._context or {})
                    context['message'] = str(response.get('result').get('error_descrip'))
                    return {
                        'name': response.get('result').get('error'),
                        'type': 'ir.actions.act_window',
                        'view_mode': 'form',
                        'view_type': 'form',
                        'res_model': 'popup.message.wizard',
                        'views': [(view_id,'form')],
                        'view_id' : form_view.id,
                        'target': 'new',
                        'context': context,
                    }
            else:
                form_view = self.env.ref('juragan_product.popup_message_wizard')
                view_id = form_view and form_view.id or False
                context = dict(self._context or {})
                context['message'] = str()
                return {
                    'name': 'Opps, Something Went Wrong.',
                    'type': 'ir.actions.act_window',
                    'view_mode': 'form',
                    'view_type': 'form',
                    'res_model': 'popup.message.wizard',
                    'views': [(view_id,'form')],
                    'view_id' : form_view.id,
                    'target': 'new',
                    'context': context,
                }
        except Exception as e:
            form_view = self.env.ref('juragan_product.popup_message_wizard')
            view_id = form_view and form_view.id or False
            context = dict(self._context or {})
            context['message'] = str(e)
            return {
                'name': 'Opps, Something Went Wrong.',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'view_type': 'form',
                'res_model': 'popup.message.wizard',
                'views': [(view_id,'form')],
                'view_id' : form_view.id,
                'target': 'new',
                'context': context,
            }
        return True

class MPProductDiscountLine(models.Model):
    _name = 'mp.product.discount.line'

    # Special IZI fields
    izi_id = fields.Integer('IZI ID')
    izi_md5 = fields.Char()

    name = fields.Char(string='Product Name')
    original_price = fields.Float(string='Original Price')
    discounted_price = fields.Float(string='Discounted Price')
    discount_percentage = fields.Float(string='Discounted Percentage')
    reserved_stock = fields.Integer(string='Reserved Quantity')
    max_order = fields.Integer(string='Purchase Limit')
    product_stg_id = fields.Many2one('product.staging', string='Product Staging')
    product_stg_var_id = fields.Many2one('product.staging.variant', string='Product Staging Variant')
    discount_id = fields.Many2one('mp.product.discount', string='Discount', ondelete='cascade')
