# -*- coding: utf-8 -*-
from odoo import http, tools
import io
import base64
from PIL import Image


class Juragan(http.Controller):

    @http.route('/jpg/<string:model>/<string:field>/<int:obj_id>.jpg', auth='public')
    def jpg(self, model, field, obj_id, **kw):
        data_png_b64 = http.request.env[model].sudo().browse(obj_id).mapped(field)[0] or b'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'
        data_png = base64.b64decode(data_png_b64)
        image = Image.open(io.BytesIO(data_png))
        image = image.convert('RGB')
        data_jpg = tools.image_save_for_web(image, format='JPEG')

        headers = [
            ('Content-Type', 'image/jpeg'),
            ('Content-Length', len(data_jpg))
        ]

        return http.request.make_response(data_jpg, headers)

    @http.route('/png/<string:model>/<string:field>/<int:obj_id>.png', auth='public')
    def png(self, model, field, obj_id, **kw):
        data_png_b64 = http.request.env[model].sudo().browse(obj_id).mapped(field)[0] or b'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'
        data_png = base64.b64decode(data_png_b64)

        headers = [
            ('Content-Type', 'image/png'),
            ('Content-Length', len(data_png))
        ]

        return http.request.make_response(data_png, headers)

#     @http.route('/api/user/auth/<string:mp_name>', auth='public')
#     @http.route('/api/user/auth/<string:mp_name>/<int:mp_id>', auth='public')
#     def auth(self, mp_name, mp_id=False, **kw):
#         return "auth %s" % (mp_name)

#     @http.route('/juragan/juragan/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/juragan/juragan/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('juragan.listing', {
#             'root': '/juragan/juragan',
#             'objects': http.request.env['juragan.juragan'].search([]),
#         })

#     @http.route('/juragan/juragan/objects/<model("juragan.juragan"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('juragan.object', {
#             'object': obj
#         })


# class JuraganProduct(http.Controller):
#     @http.route('/juragan_product/juragan_product/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/juragan_product/juragan_product/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('juragan_product.listing', {
#             'root': '/juragan_product/juragan_product',
#             'objects': http.request.env['juragan_product.juragan_product'].search([]),
#         })

#     @http.route('/juragan_product/juragan_product/objects/<model("juragan_product.juragan_product"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('juragan_product.object', {
#             'object': obj
#         })
