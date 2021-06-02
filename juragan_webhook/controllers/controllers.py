# -*- coding: utf-8 -*-
import json
import logging
import base64
import functools
from odoo import http, tools
from odoo.http import request


_logger = logging.getLogger(__name__)
db_name = tools.config.get('db_name')


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
    _logger.error("Token is expired or invalid!")
    return invalid_response(
        401, 'invalid_token', "Token is expired or invalid!")


def check_valid_token(func):

    @functools.wraps(func)
    def wrap(self, *args, **kwargs):
        headers = request.httprequest.headers
        access_token = headers.get('access_token') or (headers.get('Authorization') and headers.get('Authorization').split()[1])
        if not access_token:
            info = "Missing access token in request header!"
            error = 'access_token_not_found'
            _logger.error(info)
            return invalid_response(400, error, info)
        access_token_data = request.env['oauth.access_token'].sudo().search(
            [('token', '=', access_token)], order='id DESC', limit=1)

        if access_token_data._get_access_token(
                user_id=access_token_data.user_id.id) != access_token:
            return invalid_token()

        request.session.uid = access_token_data.user_id.id
        request.uid = access_token_data.user_id.id
        return func(self, *args, **kwargs)

    return wrap


class WebhookClient(http.Controller):

    @http.route('/webhook/client', csrf=False, type='json', auth='public')
    @check_valid_token
    def webhook_client(self, **kw):
        raw_data = http.request.jsonrequest
        # print(json.dumps(raw_data, indent=2))
        model_obj = http.request.env[raw_data.get(
            'model')].sudo().with_context(webhook=False)
        load_msg = model_obj.load(raw_data.get('keys'), raw_data.get('datas'))
        # print(json.dumps(load_msg, indent=2))
        if load_msg.get('ids') and raw_data.get('method') == 'unlink':
            model_obj.browse(load_msg.get('ids')).unlink()
        return load_msg

    @http.route([
        '/webhook/patch',
        '/webhook/patch/<model_name>/<method>',
    ], type='json', auth='none', method=['PATCH'], crsf=False, cors='*')
    @check_valid_token
    def webhook_patch(
            self, model_name=False, method=False, ids=False, **kwargs):
        try:
            raw_data = http.request.jsonrequest
            model_obj = http.request.env[model_name or raw_data.get('model')].sudo().with_context(webhook=False)
            method = method or raw_data.get('method')
            load_msg = model_obj.load(
                raw_data.get('keys'), raw_data.get('datas'))
            if load_msg.get('ids'):
                ids = load_msg.get('ids')
                if not isinstance(ids, list) and not isinstance(ids, int):
                    return invalid_response(
                        500, 'ids_error', 'IDs must be list or int.')
                if isinstance(ids, list):
                    for id in ids:
                        if not isinstance(id, int):
                            return invalid_response(
                                500, 'ids_error', 'IDs content must int.')
            else:
                ids = []
            if model_obj and method:
                object_ids = model_obj.browse(ids).with_context(
                    **raw_data.get('context', {}))
                return valid_response(
                    200,
                    getattr(object_ids, method)(
                        *raw_data.get('args', []),
                        **raw_data.get('kwargs', {})))
            else:
                return invalid_response(
                    500, 'method_empty', 'Method should not be empty.')
        except Exception as e:
            return invalid_response(500, 'method_error', e)

    # Login in odoo database and get access tokens:

    @http.route(
        '/api/v1/oauth2', methods=['POST', 'GET'],
        type='http', auth='none', csrf=False, cors='*')
    def api_oauth2(self, **kw):
        try:
            headers = request.httprequest.headers
            db = kw.get('db') or db_name
            auth = headers.get('Authorization')
            auth = auth.split(' ')[1]
            auth = base64.b64decode(auth)
            auth = auth.decode('utf-8').split(':')
            if not db or not auth[0] or not auth[1]:
                error = 'empty_db_or_username_or_password'
                return json.dumps({'error': error})
            request.session.authenticate(db, auth[0], auth[1])
            uid = request.session.uid
            access_token = request.env['oauth.access_token']._get_access_token(
                user_id=uid, create=True)
            expires_in = 'juragan_webhook.oauth2_access_token_expires_in'
            return json.dumps({
                'access_token': access_token,
                'expires_in': request.env.ref(expires_in).sudo().value,
            })
        except Exception as e:
            return json.dumps({'error': e.args[0]})
