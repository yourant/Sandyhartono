import base64

from PyPDF2 import PdfFileReader, PdfFileWriter
import io
import os
import logging
from odoo import http, _
from odoo.http import request
_logger = logging.getLogger(__name__)


class ShopeeDownloadPDF(http.Controller):

    @http.route('/web/binary/download_pdf/<ids>', type='http', auth="public", website=True)
    def download_pdf(self, ids, **kw):
        path = 'izi_shopee/data/file/'
        base_path = os.path.abspath(os.getcwd())
        final_path = base_path + path
        _logger.info(final_path)
        if not os.path.isdir(final_path):
            os.mkdir(final_path)
        for f in os.listdir(path):
            os.remove(os.path.join(final_path, f))
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
        with open(os.path.join(final_path, output_filename), 'wb') as f:
            output.write(f)
            f.close()
        filename = open(os.path.join(final_path, output_filename), 'rb')
        return http.request.make_response(filename, headers)
