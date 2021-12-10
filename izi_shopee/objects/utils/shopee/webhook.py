# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import requests

from .api import ShopeeAPI


class ShopeeWebhook(ShopeeAPI):

    def register_webhook(self, **kwargs):
        webhook_payload = {
            'callback_url': kwargs.get('callback_url'),
            'push_config': kwargs.get('push_config'),
        }
        prepared_request = self.build_request('set_push_webhook',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.access_token, **{
                                                  'json': webhook_payload,
                                              })
        response = self.request(**prepared_request)
        return self.process_response('set_push_webhook', response, no_sanitize=True)
