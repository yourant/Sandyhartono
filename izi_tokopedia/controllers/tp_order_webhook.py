# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import http
from odoo.http import *
import base64
import requests
import logging
import json

from datetime import datetime
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT

_logger = logging.getLogger(__name__)


class IZITokopedia(http.Controller):
    @http.route('/api/izi/webhook/tp/order/notification', methods=['POST', 'GET'], type='json', auth='public')
    def tp_order_notification(self, **kw):
        if request._request_type == 'json':
            json_body = request.jsonrequest
            fs_id = json_body.get('fs_id', False)
            _logger.info('New Order From Tokopedia: %s' % (json_body.get('order_id,', '')))
            if fs_id:
                mp_account = request.env['mp.account'].sudo().search([('tp_fs_id', '=', fs_id)])
                if mp_account.mp_webhook_state == 'registered':
                    marketplace = mp_account.marketplace
                    order_status = str(json_body.get('order_status'))
                    mp_webhook_order_obj = request.env['mp.webhook.order'].sudo()
                    mp_webhook_order_obj.create({
                        'mp_invoice_number': json_body.get('invoice_num,', ''),
                        'tp_order_id': str(json_body.get('order_id,', False)),
                        'mp_account_id': mp_account.id,
                        'order_update_time': datetime.fromtimestamp(
                            time.mktime(time.gmtime(json_body.get('create_time'))))
                        .strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                        'tp_order_status': order_status,
                        'raw': json.dumps(json_body, indent=4)
                    })
                    _logger.info('Success Create Tokopedia Order: %s with status %s' %
                                 (json_body.get('invoice_num'), order_status))
                    kwargs = {'params': 'by_mp_invoice_number',
                              'mp_order_id': json_body.get('order_id'),
                              'force_update': mp_account._context.get('force_update', False)}
                    if hasattr(mp_account, '%s_get_orders' % marketplace):
                        getattr(mp_account, '%s_get_orders' % marketplace)(**kwargs)
        res = Response('Success', status=200)
        return res

    @http.route('/api/izi/webhook/tp/order/request/cancel', methods=['POST', 'GET'], type='json', auth='public')
    def tp_order_cancel(self, **kw):
        if request._request_type == 'json':
            json_body = request.jsonrequest
            mp_account = request.env['mp.account'].sudo().search([('marketplace', '=', 'tokopedia')], limit=1)
            if mp_account.mp_webhook_state == 'registered':
                marketplace = mp_account.marketplace
                kwargs = {'params': 'by_mp_invoice_number',
                          'mp_order_id': json_body.get('order_id'),
                          'force_update': mp_account._context.get('force_update', False)}
                if hasattr(mp_account, '%s_get_orders' % marketplace):
                    getattr(mp_account, '%s_get_orders' % marketplace)(**kwargs)
        res = Response('Success', status=200)
        return res

    @http.route('/api/izi/webhook/tp/order/status', methods=['POST', 'GET'], type='json', auth='public')
    def tp_order_status(self, **kw):
        if request._request_type == 'json':
            json_body = request.jsonrequest
            fs_id = json_body.get('fs_id', False)
            order_status = str(json_body.get('order_status'))
            if order_status not in ['220', '221', '11', '100', '103', '200']:
                if fs_id:
                    _logger.info('New Order Status Change From Tokopedia: %s with status %s' %
                                 (json_body.get('order_id,', ''), json_body.get('order_status')))
                    mp_account = request.env['mp.account'].sudo().search([('tp_fs_id', '=', fs_id)])
                    if mp_account.mp_webhook_state == 'registered':
                        marketplace = mp_account.marketplace
                        kwargs = {'params': 'by_mp_invoice_number',
                                  'mp_order_id': json_body.get('order_id'),
                                  'force_update': mp_account._context.get('force_update', False),
                                  'skip_create': True}
                        if hasattr(mp_account, '%s_get_orders' % marketplace):
                            getattr(mp_account, '%s_get_orders' % marketplace)(**kwargs)
        res = Response('Success', status=200)
        return res
