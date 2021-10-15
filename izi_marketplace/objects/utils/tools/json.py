# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import collections
from copy import deepcopy


def json_digger(data, tree_path, default=None):
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
                return default
        tree_path = '/'.join(tree)
        return json_digger(data[current_tree], tree_path)
    else:
        return data


def merge_dict(dict1, dict2):
    """Return a new dictionary by merging two dictionaries recursively."""

    result = deepcopy(dict1)

    for key, value in dict2.items():
        if isinstance(value, collections.Mapping):
            result[key] = merge_dict(result.get(key, {}), value)
        else:
            result[key] = deepcopy(dict2[key])

    return result
