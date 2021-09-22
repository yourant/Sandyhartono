# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

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
