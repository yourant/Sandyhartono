# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import http
from odoo.http import local_redirect, request


class IZIShopee(http.Controller):

    @http.route('/shopee-push/<model("mp.shopee"):mp_id>/', type='json', csrf=False, auth='public')
    def push(self, mp_id, **kwargs):
        print(request.jsonrequest)
        return ''

    @http.route('/api/user/auth/shopee/<model("mp.account"):mp_id>/', auth='public')
    def object(self, mp_id, **kwargs):
        mp_id.sudo().shopee_get_token(**kwargs)
        return '''
        <!DOCTYPE html>
        <html>
            <body>
                <script type="text/javascript">
                    /* alert('Auth Success.'); */
                    window.onunload = function() {window.opener.location.reload()}
                    window.close();
                </script>
            </body>
        </html>
        '''
