import base64

from PyPDF2 import PdfFileReader, PdfFileWriter
import io
import os

from odoo import http, _
from odoo.http import request


class ShopeeDownloadPDF(http.Controller):

    @http.route('/web/binary/download_pdf/<ids>', type='http', auth="public", website=True)
    def download_pdf(self, ids, **kw):
        dir = 'izi_shopee/data/file/'
        for f in os.listdir(dir):
            os.remove(os.path.join(dir, f))
        pdf_list = []
        output = PdfFileWriter()
        output_filename = ids
        for so in ids.split('&'):
            so_awb_datas = request.env['sale.order'].sudo().search([('name', '=', so)]).mp_awb_datas
            awb_file = PdfFileReader(io.BytesIO(base64.b64decode(so_awb_datas)))
            for page in awb_file.pages:
                output.addPage(page)
            pdf_list.append(so_awb_datas)

        headers = [
            ('Content-Type', 'application/pdf'),
            ('Content-Disposition', 'attachment; filename=' + '%s.pdf;' % output_filename)
        ]
        with open(os.path.join(dir, output_filename), 'wb') as f:
            output.write(f)
            f.close()
        filename = open(os.path.join(dir, output_filename), 'rb')
        return http.request.make_response(filename, headers)
