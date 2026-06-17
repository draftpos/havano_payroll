from odoo import models, fields, api

class ReportSalaryRegistry(models.AbstractModel):
    _name = 'report.havano_payroll.report_salary_registry'
    _description = 'Salary Registry Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['havano.zim.report.wizard'].browse(docids)
        
        report_data = []
        for doc in docs:
            slips = self.env['hr.payslip'].search([('payslip_run_id', '=', doc.payslip_run_id.id), ('state', '!=', 'cancel')])
            
            # Collect unique salary rules that appear in any slip with non-zero total, excluding hidden rules
            rule_ids = set()
            for slip in slips:
                for line in slip.line_ids:
                    if line.total != 0.0 and line.salary_rule_id.appears_on_payslip:
                        rule_ids.add(line.salary_rule_id.id)
                        
            # Get ordered rules
            rules = self.env['hr.salary.rule'].browse(list(rule_ids)).sorted(key=lambda r: r.sequence)
            
            # Build lines per employee
            employee_lines = []
            for slip in slips:
                line_data = {
                    'employee': slip.employee_id.name,
                    'department': slip.employee_id.department_id.name or '',
                    'job': slip.employee_id.job_id.name or '',
                    'company': slip.company_id.name or '',
                    'amounts': {},
                    'sec_amounts': {}
                }
                for rule in rules:
                    slip_line = slip.line_ids.filtered(lambda l: l.salary_rule_id.id == rule.id)
                    line_data['amounts'][rule.id] = sum(slip_line.mapped('total')) if slip_line else 0.0
                    line_data['sec_amounts'][rule.id] = sum(slip_line.mapped('hao_secondary_total')) if slip_line else 0.0
                employee_lines.append(line_data)
                
            # Sort employees by name
            employee_lines = sorted(employee_lines, key=lambda x: x['employee'])
                
            # Column totals
            totals = {rule.id: sum(emp['amounts'][rule.id] for emp in employee_lines) for rule in rules}
            sec_totals = {rule.id: sum(emp['sec_amounts'][rule.id] for emp in employee_lines) for rule in rules}
            
            report_data.append({
                'run_name': doc.payslip_run_id.name,
                'rules': rules,
                'employee_lines': employee_lines,
                'totals': totals,
                'sec_totals': sec_totals
            })
            
        return {
            'doc_ids': docids,
            'doc_model': 'havano.zim.report.wizard',
            'docs': docs,
            'report_data': report_data,
        }
