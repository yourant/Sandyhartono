# -*- coding: utf-8 -*-
from odoo import http
from odoo.service.security import check_session
from odoo.addons.web.controllers.main import ensure_db, Home
from odoo.service import security
from odoo.http import request, local_redirect
import odoo


class RSAController(http.Controller):

    @http.route('/rsa/pem/public', auth='none')
    def index(self, **kw):
        return request.env['rsa'].get_public_pem()
    
    @http.route('/rsa/encrypt/<string:data>', auth='none')
    def encrypt(self, data, **kw):
        return request.env['rsa'].encrypt(data)
    
    @http.route('/rsa/test', auth='none')
    def test(self, **kw):
        return request.env['rsa'].encrypt('''
            {
                "kwargs": {
                    "fields": ["name", "display_name"]
                }
            }
        ''')


class Home(Home):

    @http.route('/web/login/rsa/<string:rsa_token>', type='http', auth="none", sitemap=False)
    def web_login_token(self, rsa_token, redirect=None, **kw):
        ensure_db()
        request.params['login_success'] = False
        if request.httprequest.method == 'GET' and redirect and request.session.uid:
            return http.redirect_with_hash(redirect)

        if not request.uid:
            request.uid = odoo.SUPERUSER_ID

        values = request.params.copy()
        try:
            values['databases'] = http.db_list()
        except odoo.exceptions.AccessDenied:
            values['databases'] = None

        if True:
            old_uid = request.uid
            try:
                request.params['login'], request.params['password'] = request.env['rsa'].decrypt(rsa_token).split(':')
                uid = request.session.authenticate(request.session.db, request.params['login'], request.params['password'])
                request.params['login_success'] = True
                return http.redirect_with_hash(self._login_redirect(uid, redirect=redirect))
            except odoo.exceptions.AccessDenied as e:
                request.uid = old_uid
                if e.args == odoo.exceptions.AccessDenied().args:
                    values['error'] = _("Wrong login/password")
                else:
                    values['error'] = e.args[0]

        if 'login' not in values and request.session.get('auth_login'):
            values['login'] = request.session.get('auth_login')

        if not odoo.tools.config['list_db']:
            values['disable_database_manager'] = True

        response = request.render('web.login', values)
        response.headers['X-Frame-Options'] = 'DENY'
        return response
