# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import functools

from requests import HTTPError
from odoo.exceptions import UserError

from odoo.addons.izi_marketplace.objects.utils.tools import mp
from odoo.addons.izi_blibli.objects.utils.blibli.exception import BlibliAPIError


class BlibliDecorator(object):
    @staticmethod
    def capture_error(method):
        @functools.wraps(method)
        def wrapper_decorator(*args, **kwargs):
            try:
                return method(*args, **kwargs)
            except BlibliAPIError as bli_error:
                raise UserError(bli_error.args)
            except HTTPError as http_error:
                raise UserError(http_error.args)
            except ConnectionError as conn_error:
                raise UserError(conn_error.args)

        return wrapper_decorator


mp.blibli = BlibliDecorator()
