# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

class TokopediaAPIError(Exception):
    def __init__(self, tp_header):
        self.message = "Tokopedia API error with the code {error_code}: {messages}."
        if tp_header.get('reason') != '':
            self.message = '%s\n\n Reason: {reason}' % self.message
        super(TokopediaAPIError, self).__init__(self.message.format(**tp_header))
