# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import time

from .api import TokopediaAPI


class TokopediaWebhook(TokopediaAPI):

    def register_webhook(self, **kwargs):
        webhook_payload = {
            'fs_id': self.tp_account.fs_id,
            'webhook_secret': kwargs.get('webhook_secret'),
        }
        if kwargs.get('order_status_url', False):
            webhook_payload.update({
                'order_notification_url': kwargs.get('order_notification_url'),
                'order_request_cancellation_url': kwargs.get('order_request_cancellation_url'),
                'order_status_url': kwargs.get('order_status_url'),
            })

        prepared_request = self.build_request('register_webhook', **{
            'force_params': True,
            'json': webhook_payload,
        })
        response = self.request(**prepared_request)
        return self.process_response('register_key', response, no_validate=True, no_sanitize=True)
