# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import http
from odoo.http import *
import hmac
import logging
from datetime import datetime
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
_logger = logging.getLogger(__name__)


class IZIShopeeWebhook(http.Controller):

    # def verify_push_msg(self, url, request_body, partner_key, authorization):
    #     base_string = url + '|' + request_body
    #     call_auth = hmac.new(partner_key.encode(), base_string.encode(), hashlib.sha256).hexdigest()
    #     if call_auth != authorization:
    #         return False
    #     else:
    #         return True

    @http.route('/api/izi/webhook/sp/order', methods=['POST', 'GET'], type='json', auth='public')
    def sp_order(self, **kw):
        if request._request_type == 'json':
            json_body = request.jsonrequest
            # authorization = request.httprequest.headers.environ.get('HTTP_AUTHORIZATION')
            # url = request.httprequest.url
            # http_body = request.httprequest.data.decode()
            shopee_shop = request.env['mp.shopee.shop'].sudo().search(
                [('shop_id', '=', str(json_body.get('shop_id')))])
            if shopee_shop:
                mp_account = shopee_shop.mp_account_id
                # verify_push_msg = self.verify_push_msg(url, http_body, mp_account.sp_partner_key, authorization)
                if json_body.get('code') == 3:
                    _logger.info('Notification Shopee Order: %s with status %s' %
                                 (json_body.get('data').get('ordersn'), json_body.get('data').get('status')))
                    if json_body.get('data').get('status') != 'UNPAID':
                        mp_webhook_order_obj = request.env['mp.webhook.order'].sudo()
                        mp_webhook_order_obj.create({
                            'mp_invoice_number': json_body.get('data').get('ordersn'),
                            'sp_order_id': json_body.get('data').get('ordersn'),
                            'mp_account_id': mp_account.id,
                            'order_update_time': datetime.fromtimestamp(
                                time.mktime(time.gmtime(json_body.get('data').get('update_time'))))
                            .strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                            'sp_order_status': json_body.get('data').get('status')
                        })
                        _logger.info('Success Create Shopee Order: %s with status %s' %
                                     (json_body.get('data').get('ordersn'), json_body.get('data').get('status')))
                        if mp_account.mp_webhook_state == 'registered':
                            marketplace = mp_account.marketplace
                            kwargs = {'params': 'by_mp_invoice_number',
                                      'mp_invoice_number': json_body.get('data').get('ordersn'),
                                      'force_update': mp_account._context.get('force_update', False),
                                      'order_status': json_body.get('data').get('status')}
                            if hasattr(mp_account, '%s_get_orders' % marketplace):
                                getattr(mp_account, '%s_get_orders' % marketplace)(**kwargs)

        res = Response('Success', status=200)
        return res
