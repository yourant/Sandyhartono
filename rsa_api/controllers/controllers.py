# -*- coding: utf-8 -*-
from base64 import b64decode
from odoo import http, SUPERUSER_ID
from odoo.addons.web.controllers.main import ensure_db
from odoo.http import JsonRequest, WebRequest, Root, request
from odoo.tools.safe_eval import safe_eval
import functools
import json
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime


class SimpleApiRequest(JsonRequest, WebRequest):
    
    def _json_response(self, result=None, error=None):
        res = super(SimpleApiRequest, self)._json_response(result, error)
        json_response = json.loads(res.response[0])
        res.response[0] = json.dumps(json_response.get('result'))
        res.headers.set('Content-Length', len(res.response[0]))
        res.headers.set('Access-Control-Allow-Origin', '*')
        return res


get_request_old = Root.get_request


def get_request_new(self, httprequest):
        if ('/rsa/api/' in httprequest.path) and (httprequest.mimetype == "application/json"):
            return SimpleApiRequest(httprequest)
        else:
            return get_request_old(self, httprequest)
        

Root.get_request = get_request_new


def valid_response(status, data):
    try:
        return {
            'status': status,
            'response': data
        }
    except Exception as e:
        invalid_response(500, 'data_error', e)


def invalid_response(status, error, info):
    return {
        'status': status, 'response': {
            'error': error,
            'error_desc': info,
        }
    }

    
def invalid_token():
    return invalid_response(401, 'invalid_token', "Token is expired or invalid!")

    
def check_valid_token(func):

    @functools.wraps(func)
    def wrap(self, *args, **kwargs):
        ensure_db()

        if not request.uid:
            request.uid = SUPERUSER_ID
        
        headers = request.httprequest.headers
        access_token = headers.get('access_token') or (headers.get('Authorization') and headers.get('Authorization').split()[1])
        if not access_token:
            info = "Missing access token in request header!"
            error = 'access_token_not_found'
            return invalid_response(400, error, info)

        try:
            login, password = request.env['rsa'].decrypt(access_token).split(':')
            uid = request.session.authenticate(request.session.db, login, password)
            request.session.uid = uid
            request.uid = uid
            return func(self, *args, **kwargs)
        except Exception as e:
            return invalid_response(401, 'auth_error', e)

    return wrap


class ControllerREST(http.Controller):
    
    @http.route('/rsa/api/v1/signup', methods=['POST', 'GET'], type='json', auth='none', csrf=False, cors='*')
    def api_signup(self, **post):
        ensure_db()
        body = request.jsonrequest
        values = {}
        if body.get('ciphertext'):
            plaintext = request.env['rsa'].decrypt(body.get('ciphertext'))
            plaindict = json.loads(plaintext)
            values['login'] = plaindict.get('username') or None
            values['password'] = plaindict.get('password') or None
            values['name'] = plaindict.get('name') or None
        else:
            values['login'] = post.get('username') or body.get('username') or None
            values['password'] = post.get('password') or body.get('password') or None
            values['name'] = post.get('name') or body.get('name') or None
        
        if not values.get('login') or not values.get('password') or not values.get('name'):
            info = "Empty value of 'email' or 'username' or 'password'!"
            error = 'empty_name_or_username_or_password'
            return invalid_response(400, error, info)
        
        try:
            sign = request.env['res.users'].sudo().signup(values)
            if body.get('public_pem'):
                return valid_response(200, {
                    'ciphertext': request.env['rsa'].encrypt(json.dumps({
                        'db': sign[0],
                        'username': sign[1],
                        'password': sign[2]
                    }), public_pem=body.get('public_pem'))
                })
            else:
                return valid_response(200, {
                    'db': sign[0],
                    'username': sign[1],
                    'password': sign[2]
                })
        except Exception as e:
            error = 'invalid_signup'
            return invalid_response(400, error, e)
        
    @http.route('/rsa/api/v1/oauth2', methods=['POST', 'GET'], type='http', auth='none', csrf=False, cors='*')
    def api_oauth2(self, **kw):
        try:
            ensure_db()
            headers = request.httprequest.headers
            auth = headers.get('Authorization')
            auth = auth.split(' ')[1]
            auth = b64decode(auth)
            auth = auth.decode('utf-8')
            auth_list = auth.split(':')
            if not auth_list[0] or not auth_list[1]:
                error = 'empty_db_or_username_or_password'
                return json.dumps({'error': error})
            request.session.authenticate(request.session.db, auth_list[0], auth_list[1])
            return json.dumps({
                'access_token': request.env['rsa'].encrypt(auth),
                # 'expires_in': int((request.env.ref('rsa.ir_cron_renew_rsa_key').nextcall - datetime.now()).total_seconds()),
                # 'expired_at': request.env.ref('rsa.ir_cron_renew_rsa_key').nextcall.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                'public_pem': request.env['rsa'].get_public_pem(),
            })
        except Exception as e:
            return json.dumps({
                'error': '%s' % (e),
                'public_pem': request.env['rsa'].get_public_pem(),
            })
    
    @http.route('/rsa/api/v1/dbname', methods=['GET'], type="http", csrf=False, cors='*')
    def get_dbname(self, **kw):
        return json.dumps(valid_response(200, {
            'dbname': request.env.cr.dbname
        }))
        
    @http.route([
        '/rsa/api/v1/<model_name>/<method>',
        '/rsa/api/v1/<model_name>/<method>/<ids>'
    ], type='json', methods=['PATCH'], auth='none', csrf=False, cors='*')
    @check_valid_token
    def restapi_patch(self, model_name=False, method=False, ids=False, **kwargs):
        try:
            body = request.jsonrequest
            if ids:
                ids = safe_eval(ids)
                if not isinstance(ids, list) and not isinstance(ids, int):
                    return invalid_response(500, 'ids_error', 'IDs must be list or int.')
                if isinstance(ids, list):
                    for ida in ids:
                        if not isinstance(ida, int):
                            return invalid_response(500, 'ids_error', 'IDs content must int.')
            else:
                ids = []
            if model_name and method:
                if body.get('ciphertext'):
                    plaintext = request.env['rsa'].decrypt(body.get('ciphertext'))
                    plaindict = json.loads(plaintext)
                    body_context = plaindict.get('context', {})
                    body_args = plaindict.get('args', [])
                    body_kwargs = plaindict.get('kwargs', {})
                else:
                    body_context = body.get('context', {})
                    body_args = body.get('args', [])
                    body_kwargs = body.get('kwargs', {})
                object_ids = request.env[model_name].browse(ids).with_context(**body_context)
                object_res = getattr(object_ids, method)(*body_args, **body_kwargs)
                if body.get('public_pem'):
                    return valid_response(200, {
                        'ciphertext': request.env['rsa'].encrypt(json.dumps(object_res), public_pem=body.get('public_pem'))
                    })
                else:
                    return valid_response(200, object_res)
            else:
                return invalid_response(500, 'method_empty', 'Method should not be empty.')
        except Exception as e:
            return invalid_response(500, 'method_error', e)
