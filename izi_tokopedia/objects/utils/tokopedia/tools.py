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


def json_digger(data, tree_path):
    if isinstance(data, list):
        result = []
        for d in data:
            result.append(json_digger(d, tree_path))
        return result
    elif isinstance(data, dict):
        tree = tree_path.split('/')
        current_tree = tree.pop(0)
        if not tree:
            try:
                return data[current_tree]
            except KeyError:
                return None
        tree_path = '/'.join(tree)
        return json_digger(data[current_tree], tree_path)
    else:
        return data


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
