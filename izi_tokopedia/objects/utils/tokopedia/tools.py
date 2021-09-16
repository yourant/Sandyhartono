# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from .exception import TokopediaAPIError


def validate_response(response):
    if response.status_code != 200:
        if response.status_code != 500:
            response.raise_for_status()
        raise TokopediaAPIError(response.json()['header'])
    return response


def sanitize_response(response):
    return response.json()['data']


def process_response(response):
    return sanitize_response(validate_response(response))
