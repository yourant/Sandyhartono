# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

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
        return self.process_response('register_key', self.request(**prepared_request), no_sanitize=True)
