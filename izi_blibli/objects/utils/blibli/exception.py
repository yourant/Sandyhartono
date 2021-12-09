# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

class BlibliAPIError(Exception):
    def __init__(self, bli_header):
        self.message = "Blibli API error with the code {errorCode}: {errorMessage}"
        super(BlibliAPIError, self).__init__(self.message.format(**bli_header))
