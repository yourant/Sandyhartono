# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

class ShopeeAPIError(Exception):
    def __init__(self, sp_header):
        self.message = "Shopee API error with the code {error}: {message}"
        if sp_header.get('response') != '':
            self.message + ' caused by {response}'
        super(ShopeeAPIError, self).__init__(self.message.format(**sp_header))
