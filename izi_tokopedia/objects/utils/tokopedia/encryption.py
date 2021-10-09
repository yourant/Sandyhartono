# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import time

from .api import TokopediaAPI


class TokopediaEncryption(TokopediaAPI):

    def register_public_key(self, public_key_file):
        params = {'upload': 1}
        files = {'public_key': public_key_file}

        prepared_request = self.build_request('register_key', **{
            'force_params': True,
            'params': params,
            'files': files
        })
        response = self.request(**prepared_request)
        tp_limit_rate_reset = abs(float(response.headers.get('X-Ratelimit-Reset-After', 0)))
        if tp_limit_rate_reset > 0:
            self._logger.info(
                "Order: Too many requests, Tokopedia asking to waiting for %s second(s)" % str(tp_limit_rate_reset))
            time.sleep(tp_limit_rate_reset + 1)
        no_validate = response.status_code == 429
        return self.process_response('register_key', response, no_validate=no_validate, no_sanitize=True)
