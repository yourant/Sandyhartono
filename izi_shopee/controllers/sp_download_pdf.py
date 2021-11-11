import base64

from PyPDF2 import PdfFileReader, PdfFileWriter
import io
import logging
from odoo import http, _
from odoo.http import request
_logger = logging.getLogger(__name__)


class ShopeeDownloadPDF(http.Controller):

    @http.route('/web/binary/shopee/download_pdf/<ids>', type='http', auth="public", website=True)
    def download_pdf(self, ids, **kw):
        output_stream = io.BytesIO()
        output = PdfFileWriter()
        output_filename = ids
        for so in ids.split('&'):
            so_awb_datas = request.env['sale.order'].sudo().search([('name', '=', so)]).mp_awb_datas
            awb_file = PdfFileReader(io.BytesIO(base64.b64decode(so_awb_datas)))
            for page in awb_file.pages:
                output.addPage(page)

        headers = [
            ('Content-Type', 'application/pdf'),
            ('Content-Disposition', 'attachment; filename=' + '%s.pdf;' % output_filename)
        ]
        output.write(output_stream)
        data = output_stream.getvalue()
        return http.request.make_response(data, headers)
