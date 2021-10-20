# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import functools

from requests import HTTPError, ConnectionError as RequestsConnectionError
from odoo.exceptions import UserError

from odoo.addons.izi_marketplace.objects.utils.tools import mp
from odoo.addons.izi_tokopedia.objects.utils.tokopedia.exception import TokopediaAPIError


class TokopediaDecorator(object):
    @staticmethod
    def capture_error(method):
        @functools.wraps(method)
        def wrapper_decorator(*args, **kwargs):
            try:
                return method(*args, **kwargs)
            except TokopediaAPIError as tp_error:
                raise UserError(tp_error.args)
            except HTTPError as http_error:
                raise UserError(http_error.args)
            except RequestsConnectionError as conn_error:
                raise UserError(conn_error.args)

        return wrapper_decorator


mp.tokopedia = TokopediaDecorator()
