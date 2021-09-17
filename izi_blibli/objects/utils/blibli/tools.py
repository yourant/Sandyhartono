# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import json

from .exception import BlibliAPIError


def validate_response(response):
    if response.status_code != 200:
        res = json.loads(response.text)
        raise BlibliAPIError(res)
    return response


def sanitize_response(response):
    return response.json()['data']


def process_response(response):
    return sanitize_response(validate_response(response))
