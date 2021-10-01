# -*- coding: utf-8 -*-

from typing import Optional, Any


def clean_csv_value(value: Optional[Any]) -> str:
    if value is None:
        return r'\N'
    return str(value).replace('\n', '\\n')
