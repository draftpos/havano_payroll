from odoo import models, api

class ReportZimStatutory(models.AbstractModel):
    _name = 'report.havano_payroll.report_zim_statutory'
    _description = 'Zimbabwe Statutory Reports PDF'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['havano.zim.report.wizard'].browse(docids)
        wizard = docs[0]
        
        report_data = []
        report_title = ""
        if wizard.report_type == 'nec':
            report_data = self.env['havano.nec.report'].search([('payslip_run_id', '=', wizard.payslip_run_id.id)])
            report_title = "NEC Report"
        elif wizard.report_type == 'nssa_p4':
            report_data = self.env['havano.nssa.p4.report'].search([('payslip_run_id', '=', wizard.payslip_run_id.id)])
            report_title = "NSSA P4 Report"
        elif wizard.report_type == 'nssa_employer':
            report_data = self.env['havano.nssa.employer.report'].search([('payslip_run_id', '=', wizard.payslip_run_id.id)])
            report_title = "NSSA Report Employer"

        return {
            'doc_ids': docids,
            'doc_model': 'havano.zim.report.wizard',
            'docs': docs,
            'report_data': report_data,
            'report_title': report_title,
        }
