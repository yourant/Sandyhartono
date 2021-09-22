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
