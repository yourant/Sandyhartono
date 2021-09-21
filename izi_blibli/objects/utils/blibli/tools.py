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
    return response.json()['content']


def process_response(response):
    return sanitize_response(validate_response(response))


def pagination_get_pages(limit=0, per_page=50):
    pages = []  # tuple of page number and total item per page
    page = 1

    if 0 < limit <= per_page:
        pages.append((page, limit))
    elif limit > per_page:
        total_page = limit // per_page
        remainder = limit % per_page

        while page <= total_page:
            pages.append((page, per_page))
            page += 1

        if remainder > 0:
            pages.append((total_page + 1, remainder))

    return pages
