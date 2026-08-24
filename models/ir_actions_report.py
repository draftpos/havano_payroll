from odoo import models, api

class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    @api.model
    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        report = self._get_report(report_ref)
        if report.report_name == 'hr_payroll.report_payslip' and res_ids:
            payslips = self.env['hr.payslip'].browse(res_ids)
            if payslips:
                # Assume all payslips being printed belong to the same company
                company = payslips[0].company_id
                if company.payslip_format == 'landscape_3_per_page':
                    landscape_pf = self.env.ref('havano_payroll.paperformat_landscape_payslip_3_per_page', raise_if_not_found=False)
                    if landscape_pf:
                        report = report.with_context(landscape_paperformat_id=landscape_pf.id)
        return super(IrActionsReport, self)._render_qweb_pdf(report, res_ids, data)

    def _get_paperformat(self):
        self.ensure_one()
        if self.env.context.get('landscape_paperformat_id'):
            pf = self.env['report.paperformat'].browse(self.env.context.get('landscape_paperformat_id'))
            if pf.exists():
                return pf
        return super(IrActionsReport, self)._get_paperformat()
