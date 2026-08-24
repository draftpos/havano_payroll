import io
import re
from PyPDF2 import PdfFileReader, PdfFileWriter
from odoo.tools.safe_eval import safe_eval
from odoo import http
from odoo.http import request

class HavanoPayrollController(http.Controller):

    @http.route(['/print/payslips'], type='http', auth='user')
    def get_payroll_report_print(self, list_ids='', **post):
        if not request.env.user.has_group('hr_payroll.group_hr_payroll_user') or not list_ids or re.search("[^0-9|,]", list_ids):
            return request.not_found()

        ids = [int(s) for s in list_ids.split(',')]
        payslips = request.env['hr.payslip'].browse(ids)

        pdf_writer = PdfFileWriter()
        payslip_reports = payslips._get_pdf_reports()

        for report, slips in payslip_reports.items():
            # Check if using the landscape layout format which should NOT be separated
            payslip_format = slips and slips[0].company_id.payslip_format or 'standard'
            
            if payslip_format == 'landscape_3_per_page':
                # Generate them all together in ONE single PDF rendering call
                pdf_content, _ = request.env['ir.actions.report'].\
                    with_context(lang=slips[0].employee_id.lang or slips.env.lang).\
                    sudo().\
                    _render_qweb_pdf(report, slips.ids, data={'company_id': slips[0].company_id})
                reader = PdfFileReader(io.BytesIO(pdf_content), strict=False)
                for page in range(reader.getNumPages()):
                    pdf_writer.addPage(reader.getPage(page))
            else:
                # Odoo standard behavior: separate PDFs concatenated
                for payslip in slips:
                    pdf_content, _ = request.env['ir.actions.report'].\
                        with_context(lang=payslip.employee_id.lang or payslip.env.lang).\
                        sudo().\
                        _render_qweb_pdf(report, payslip.id, data={'company_id': payslip.company_id})
                    reader = PdfFileReader(io.BytesIO(pdf_content), strict=False)

                    for page in range(reader.getNumPages()):
                        pdf_writer.addPage(reader.getPage(page))

        _buffer = io.BytesIO()
        pdf_writer.write(_buffer)
        merged_pdf = _buffer.getvalue()
        _buffer.close()

        if len(payslips) == 1 and payslips.struct_id.report_id.print_report_name:
            report_name = safe_eval(payslips.struct_id.report_id.print_report_name, {'object': payslips})
        else:
            report_name = "Payslips"

        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(merged_pdf)),
            ('Content-Disposition', 'attachment; filename=' + report_name + '.pdf;')
        ]

        return request.make_response(merged_pdf, headers=pdfhttpheaders)
