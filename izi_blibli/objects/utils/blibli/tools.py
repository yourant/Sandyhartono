# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import json
from dateutil.relativedelta import relativedelta

from .exception import BlibliAPIError


def validate_response(response):
    if response.status_code != 200:
        res = json.loads(response.text)
        raise BlibliAPIError(res)
    return response


def sanitize_response(response):
    return response.json()


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


def pagination_date_range(from_date, to_date, max_interval_day=3):
    date_ranges = []
    one_second = relativedelta(seconds=1)
    interval_day = relativedelta(days=max_interval_day)

    while from_date < to_date:
        total_days = (to_date - from_date).days

        if total_days <= max_interval_day:
            date_ranges.append((from_date, to_date))
            from_date = to_date
        else:
            start_interval_day = from_date
            end_interval_day = from_date + interval_day

            if end_interval_day > to_date:
                end_interval_day = to_date
                from_date = to_date

            date_ranges.append((start_interval_day, end_interval_day))
            if from_date != to_date:
                from_date = end_interval_day + one_second
    return date_ranges
