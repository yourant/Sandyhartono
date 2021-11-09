import base64
import logging
import werkzeug
import PyPDF2

from odoo import http, _
from odoo.exceptions import AccessError, UserError
from odoo.http import request


class ShopeeDownloadPDF(http.Controller):

    @http.route('/web/binary/download_pdf/<ids>', type='http', auth="public", website=True)
    def download_pdf(self, ids, **kw):
        pdf_list = []
        for so in ids.split('&'):
            so_awb_datas = request.env['sale.order'].sudo().search([('name', '=', so)]).mp_awb_datas
            pdf_list.append(so_awb_datas)

        pdf_files = base64.b64decode(b''.join(pdf_list))
        headers = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf_files))
        ]
        return http.request.make_response(pdf_files, headers)
