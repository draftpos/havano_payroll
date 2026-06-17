from odoo import models, fields, api

class HavanoZimReportWizard(models.TransientModel):
    _name = 'havano.zim.report.wizard'
    _description = 'Zimbabwe Reports Wizard'

    payslip_run_id = fields.Many2one('hr.payslip.run', string='Pay Run', required=True)
    company_id = fields.Many2one('res.company', related='payslip_run_id.company_id', string='Company')
    report_type = fields.Selection([
        ('nec', 'NEC Report'),
        ('nssa_p4', 'NSSA P4 Report'),
        ('nssa_employer', 'NSSA Report Employer'),
        ('summary', 'Payroll Summary Report'),
        ('registry', 'Salary Registry Report')
    ], string="Report Type", required=True)

    def action_generate_report(self):
        self.ensure_one()
        
        domain = [('payslip_run_id', '=', self.payslip_run_id.id)]
        
        if self.report_type == 'nec':
            action = self.env.ref('havano_payroll.action_havano_nec_report_tree_only').read()[0]
        elif self.report_type == 'nssa_p4':
            action = self.env.ref('havano_payroll.action_havano_nssa_p4_report_tree_only').read()[0]
        elif self.report_type == 'nssa_employer':
            action = self.env.ref('havano_payroll.action_havano_nssa_employer_report_tree_only').read()[0]
        elif self.report_type == 'summary':
            return {
                'name': f'Payroll Summary - {self.payslip_run_id.name}',
                'type': 'ir.actions.act_window',
                'res_model': 'hr.payslip.line',
                'view_mode': 'pivot,list',
                'domain': [
                    ('slip_id.payslip_run_id', '=', self.payslip_run_id.id), 
                    ('slip_id.state', '!=', 'cancel'), 
                    ('total', '!=', 0.0),
                    ('salary_rule_id.appears_on_payslip', '=', True)
                ],
                'context': {
                    'pivot_row_groupby': ['salary_rule_id'],
                    'pivot_measures': ['total', 'hao_secondary_total'],
                }
            }
        elif self.report_type == 'registry':
            return {
                'name': f'Salary Registry - {self.payslip_run_id.name}',
                'type': 'ir.actions.act_window',
                'res_model': 'hr.payslip.line',
                'view_mode': 'pivot,list',
                'domain': [
                    ('slip_id.payslip_run_id', '=', self.payslip_run_id.id), 
                    ('slip_id.state', '!=', 'cancel'), 
                    ('total', '!=', 0.0),
                    ('salary_rule_id.appears_on_payslip', '=', True)
                ],
                'context': {
                    'pivot_row_groupby': ['employee_id'],
                    'pivot_column_groupby': ['salary_rule_id'],
                    'pivot_measures': ['total', 'hao_secondary_total'],
                }
            }
            
        action['domain'] = domain
        action['context'] = {
            'default_payslip_run_id': self.payslip_run_id.id,
            'hao_allow_multi_payroll_currency': self.company_id.hao_allow_multi_payroll_currency
        }
        action['display_name'] = f"{dict(self._fields['report_type'].selection).get(self.report_type)} - {self.payslip_run_id.name}"
        action['target'] = 'main'
        return action

    def action_print_report(self):
        self.ensure_one()
        if self.report_type == 'summary':
            return self.env.ref('havano_payroll.action_report_payroll_summary').report_action(self)
        if self.report_type == 'registry':
            return self.env.ref('havano_payroll.action_report_salary_registry').report_action(self)
        return self.env.ref('havano_payroll.action_report_zim_statutory').report_action(self)
