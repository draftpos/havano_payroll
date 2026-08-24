from odoo import models, fields, tools, api
from odoo.exceptions import UserError

class HavanoNecReport(models.Model):
    _name = 'havano.nec.report'
    _description = 'NEC Report'
    _auto = False

    employee_id = fields.Many2one('hr.employee', string='Employee', readonly=True)
    payslip_run_id = fields.Many2one('hr.payslip.run', string='Pay Run', readonly=True)
    surname = fields.Char(string='Surname', readonly=True)
    first_names = fields.Char(string='First Names', readonly=True)
    date_from = fields.Date(string='Start Date', readonly=True)
    date_to = fields.Date(string='End Date', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    hao_allow_multi_payroll_currency = fields.Boolean(related='company_id.hao_allow_multi_payroll_currency')
    hao_secondary_payroll_currency_id = fields.Many2one('res.currency', related='company_id.hao_secondary_payroll_currency_id')
    
    nec_earnings = fields.Float(string='NEC Earnings (USD)', readonly=True)
    employee_contribution = fields.Float(string='Employee Contribution (USD)', readonly=True)
    employer_contribution = fields.Float(string='Employer Contribution (USD)', readonly=True)
    total_nec = fields.Float(string='Total NEC (USD)', readonly=True)
    
    sec_nec_earnings = fields.Float(string='NEC Earnings (Sec)', readonly=True)
    sec_employee_contribution = fields.Float(string='Employee Contribution (Sec)', readonly=True)
    sec_employer_contribution = fields.Float(string='Employer Contribution (Sec)', readonly=True)
    sec_total_nec = fields.Float(string='Total NEC (Sec)', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    p.id AS id,
                    p.employee_id AS employee_id,
                    p.payslip_run_id AS payslip_run_id,
                    COALESCE(SUBSTRING(e.name FROM '^(.+)\\s+[^ ]+$'), e.name) AS first_names,
                    COALESCE(SUBSTRING(e.name FROM '\\s+([^ ]+)$'), '') AS surname,
                    p.date_from AS date_from,
                    p.date_to AS date_to,
                    p.company_id AS company_id,
                    COALESCE(MAX(CASE WHEN l.code = 'BASIC' THEN l.total ELSE 0 END), 0.0) AS nec_earnings,
                    COALESCE(MAX(CASE WHEN l.code = 'NEC' THEN ABS(l.total) ELSE 0 END), 0.0) AS employee_contribution,
                    COALESCE(MAX(CASE WHEN l.code = 'NEC_COMP' THEN ABS(l.total) ELSE 0 END), 0.0) AS employer_contribution,
                    COALESCE(MAX(CASE WHEN l.code = 'NEC' THEN ABS(l.total) ELSE 0 END), 0.0) +
                    COALESCE(MAX(CASE WHEN l.code = 'NEC_COMP' THEN ABS(l.total) ELSE 0 END), 0.0) AS total_nec,
                    COALESCE(MAX(CASE WHEN l.code = 'BASIC' THEN l.hao_secondary_total ELSE 0 END), 0.0) AS sec_nec_earnings,
                    COALESCE(MAX(CASE WHEN l.code = 'NEC' THEN ABS(l.hao_secondary_total) ELSE 0 END), 0.0) AS sec_employee_contribution,
                    COALESCE(MAX(CASE WHEN l.code = 'NEC_COMP' THEN ABS(l.hao_secondary_total) ELSE 0 END), 0.0) AS sec_employer_contribution,
                    COALESCE(MAX(CASE WHEN l.code = 'NEC' THEN ABS(l.hao_secondary_total) ELSE 0 END), 0.0) +
                    COALESCE(MAX(CASE WHEN l.code = 'NEC_COMP' THEN ABS(l.hao_secondary_total) ELSE 0 END), 0.0) AS sec_total_nec
                FROM hr_payslip p
                JOIN hr_employee e ON p.employee_id = e.id
                LEFT JOIN hr_payslip_line l ON l.slip_id = p.id
                WHERE p.state IN ('draft', 'done', 'validated', 'paid')
                GROUP BY
                    p.id, p.employee_id, p.payslip_run_id, e.name, p.date_from, p.date_to, p.company_id
            )
        """ % (self._table,))

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        res = super().get_view(view_id=view_id, view_type=view_type, **options)
        if view_type in ('list', 'tree'):
            company = self.env.company
            sec_curr = company.hao_secondary_payroll_currency_id.name or 'Sec'
            base_curr = company.currency_id.name or 'USD'
            
            if '(Sec)' in res['arch']:
                res['arch'] = res['arch'].replace('(Sec)', f'({sec_curr})')
            if '(USD)' in res['arch']:
                res['arch'] = res['arch'].replace('(USD)', f'({base_curr})')
        return res

    def action_print_report(self):
        run_id = self.env.context.get('default_payslip_run_id')
        if not run_id and self:
            run_id = self[0].payslip_run_id.id
        if not run_id:
            domain = self.env.context.get('active_domain', [])
            if domain:
                for leaf in domain:
                    if isinstance(leaf, (list, tuple)) and leaf[0] == 'payslip_run_id' and leaf[1] == '=':
                        run_id = leaf[2]
                        break
        if not run_id:
            raise UserError("Please select at least one row using the checkboxes on the left before clicking Print PDF.")
        wizard = self.env['havano.zim.report.wizard'].create({
            'payslip_run_id': run_id,
            'report_type': 'nec'
        })
        return wizard.action_print_report()


class HavanoNssaP4Report(models.Model):
    _name = 'havano.nssa.p4.report'
    _description = 'NSSA P4 Report'
    _auto = False

    employee_id = fields.Many2one('hr.employee', string='Employee', readonly=True)
    payslip_run_id = fields.Many2one('hr.payslip.run', string='Pay Run', readonly=True)
    surname = fields.Char(string='Surname', readonly=True)
    first_names = fields.Char(string='First Names', readonly=True)
    date_from = fields.Date(string='Start Date', readonly=True)
    date_to = fields.Date(string='End Date', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    hao_allow_multi_payroll_currency = fields.Boolean(related='company_id.hao_allow_multi_payroll_currency')
    hao_secondary_payroll_currency_id = fields.Many2one('res.currency', related='company_id.hao_secondary_payroll_currency_id')
    
    insurable_earnings = fields.Float(string='Total Insurable Earnings (USD)', readonly=True)
    current_contributions = fields.Float(string='Current Contributions (USD)', readonly=True)
    arrears = fields.Float(string='Arrears (USD)', readonly=True)
    prepayments = fields.Float(string='Prepayments (USD)', readonly=True)
    surcharge = fields.Float(string='Surcharge (USD)', readonly=True)
    total_payment = fields.Float(string='Total Payment (USD)', readonly=True)
    employer_payment = fields.Float(string='Employer Payment (USD)', readonly=True)
    
    sec_insurable_earnings = fields.Float(string='Insurable Earnings (Sec)', readonly=True)
    sec_current_contributions = fields.Float(string='Current Contributions (Sec)', readonly=True)
    sec_total_payment = fields.Float(string='Total Payment (Sec)', readonly=True)
    sec_employer_payment = fields.Float(string='Employer Payment (Sec)', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    p.id AS id,
                    p.employee_id AS employee_id,
                    p.payslip_run_id AS payslip_run_id,
                    COALESCE(SUBSTRING(e.name FROM '^(.+)\\s+[^ ]+$'), e.name) AS first_names,
                    COALESCE(SUBSTRING(e.name FROM '\\s+([^ ]+)$'), '') AS surname,
                    p.date_from AS date_from,
                    p.date_to AS date_to,
                    p.company_id AS company_id,
                    COALESCE(MAX(CASE WHEN l.code = 'BASIC' THEN l.total ELSE 0 END), 0.0) AS insurable_earnings,
                    COALESCE(MAX(CASE WHEN l.code = 'NSSA' THEN ABS(l.total) ELSE 0 END), 0.0) AS current_contributions,
                    0.0 AS arrears,
                    0.0 AS prepayments,
                    0.0 AS surcharge,
                    COALESCE(MAX(CASE WHEN l.code = 'NSSA' THEN ABS(l.total) ELSE 0 END), 0.0) AS total_payment,
                    COALESCE(MAX(CASE WHEN l.code = 'NSSA_COMP' THEN ABS(l.total) ELSE 0 END), 0.0) AS employer_payment,
                    COALESCE(MAX(CASE WHEN l.code = 'BASIC' THEN l.hao_secondary_total ELSE 0 END), 0.0) AS sec_insurable_earnings,
                    COALESCE(MAX(CASE WHEN l.code = 'NSSA' THEN ABS(l.hao_secondary_total) ELSE 0 END), 0.0) AS sec_current_contributions,
                    COALESCE(MAX(CASE WHEN l.code = 'NSSA' THEN ABS(l.hao_secondary_total) ELSE 0 END), 0.0) AS sec_total_payment,
                    COALESCE(MAX(CASE WHEN l.code = 'NSSA_COMP' THEN ABS(l.hao_secondary_total) ELSE 0 END), 0.0) AS sec_employer_payment
                FROM hr_payslip p
                JOIN hr_employee e ON p.employee_id = e.id
                LEFT JOIN hr_payslip_line l ON l.slip_id = p.id
                WHERE p.state IN ('draft', 'done', 'validated', 'paid')
                GROUP BY
                    p.id, p.employee_id, p.payslip_run_id, e.name, p.date_from, p.date_to, p.company_id
            )
        """ % (self._table,))

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        res = super().get_view(view_id=view_id, view_type=view_type, **options)
        if view_type in ('list', 'tree'):
            company = self.env.company
            sec_curr = company.hao_secondary_payroll_currency_id.name or 'Sec'
            base_curr = company.currency_id.name or 'USD'
            
            if '(Sec)' in res['arch']:
                res['arch'] = res['arch'].replace('(Sec)', f'({sec_curr})')
            if '(USD)' in res['arch']:
                res['arch'] = res['arch'].replace('(USD)', f'({base_curr})')
        return res

    def action_print_report(self):
        run_id = self.env.context.get('default_payslip_run_id')
        if not run_id and self:
            run_id = self[0].payslip_run_id.id
        if not run_id:
            domain = self.env.context.get('active_domain', [])
            if domain:
                for leaf in domain:
                    if isinstance(leaf, (list, tuple)) and leaf[0] == 'payslip_run_id' and leaf[1] == '=':
                        run_id = leaf[2]
                        break
        if not run_id:
            raise UserError("Please select at least one row using the checkboxes on the left before clicking Print PDF.")
        wizard = self.env['havano.zim.report.wizard'].create({
            'payslip_run_id': run_id,
            'report_type': 'nssa_p4'
        })
        return wizard.action_print_report()


class HavanoNssaEmployerReport(models.Model):
    _name = 'havano.nssa.employer.report'
    _description = 'NSSA Report Employer'
    _auto = False

    employee_id = fields.Many2one('hr.employee', string='Employee', readonly=True)
    payslip_run_id = fields.Many2one('hr.payslip.run', string='Pay Run', readonly=True)
    first_name = fields.Char(string='First Name', readonly=True)
    surname = fields.Char(string='Surname', readonly=True)
    period = fields.Char(string='Payroll Period', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    hao_allow_multi_payroll_currency = fields.Boolean(related='company_id.hao_allow_multi_payroll_currency')
    hao_secondary_payroll_currency_id = fields.Many2one('res.currency', related='company_id.hao_secondary_payroll_currency_id')
    
    nssa_zig_employee = fields.Float(string='NSSA (Sec) Employee', readonly=True)
    nssa_zig_employer = fields.Float(string='NSSA (Sec) Employer', readonly=True)
    nssa_usd_employee = fields.Float(string='NSSA (Base) Employee', readonly=True)
    nssa_usd_employer = fields.Float(string='NSSA (Base) Employer', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    p.id AS id,
                    p.employee_id AS employee_id,
                    p.payslip_run_id AS payslip_run_id,
                    COALESCE(SUBSTRING(e.name FROM '^(.+)\\s+[^ ]+$'), e.name) AS first_name,
                    COALESCE(SUBSTRING(e.name FROM '\\s+([^ ]+)$'), '') AS surname,
                    TO_CHAR(p.date_from, 'YYYY-MM-DD') || ' to ' || TO_CHAR(p.date_to, 'YYYY-MM-DD') AS period,
                    p.company_id AS company_id,
                    COALESCE(MAX(CASE WHEN l.code = 'NSSA' THEN ABS(l.hao_secondary_total) ELSE 0 END), 0.0) AS nssa_zig_employee,
                    COALESCE(MAX(CASE WHEN l.code = 'NSSA_COMP' THEN ABS(l.hao_secondary_total) ELSE 0 END), 0.0) AS nssa_zig_employer,
                    COALESCE(MAX(CASE WHEN l.code = 'NSSA' THEN ABS(l.total) ELSE 0 END), 0.0) AS nssa_usd_employee,
                    COALESCE(MAX(CASE WHEN l.code = 'NSSA_COMP' THEN ABS(l.total) ELSE 0 END), 0.0) AS nssa_usd_employer
                FROM hr_payslip p
                JOIN hr_employee e ON p.employee_id = e.id
                LEFT JOIN hr_payslip_line l ON l.slip_id = p.id
                WHERE p.state IN ('draft', 'done', 'validated', 'paid')
                GROUP BY
                    p.id, p.employee_id, p.payslip_run_id, e.name, p.date_from, p.date_to, p.company_id
            )
        """ % (self._table,))

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        res = super().get_view(view_id=view_id, view_type=view_type, **options)
        if view_type in ('list', 'tree'):
            company = self.env.company
            sec_curr = company.hao_secondary_payroll_currency_id.name or 'Sec'
            base_curr = company.currency_id.name or 'USD'
            
            if '(Sec)' in res['arch']:
                res['arch'] = res['arch'].replace('(Sec)', f'({sec_curr})')
            if '(USD)' in res['arch']:
                res['arch'] = res['arch'].replace('(USD)', f'({base_curr})')
        return res

    def action_print_report(self):
        run_id = self.env.context.get('default_payslip_run_id')
        if not run_id and self:
            run_id = self[0].payslip_run_id.id
        if not run_id:
            domain = self.env.context.get('active_domain', [])
            if domain:
                for leaf in domain:
                    if isinstance(leaf, (list, tuple)) and leaf[0] == 'payslip_run_id' and leaf[1] == '=':
                        run_id = leaf[2]
                        break
        if not run_id:
            raise UserError("Please select at least one row using the checkboxes on the left before clicking Print PDF.")
        wizard = self.env['havano.zim.report.wizard'].create({
            'payslip_run_id': run_id,
            'report_type': 'nssa_employer'
        })
        return wizard.action_print_report()

class ReportPayrollSummary(models.AbstractModel):
    _name = 'report.havano_payroll.report_payroll_summary'
    _description = 'Payroll Summary Report'

    def _get_report_values(self, docids, data=None):
        wizard = self.env['havano.zim.report.wizard'].browse(docids)
        run_id = wizard.payslip_run_id

        domain = [('slip_id.payslip_run_id', '=', run_id.id), ('slip_id.state', 'in', ('draft', 'done', 'validated', 'paid'))]
        lines = self.env['hr.payslip.line'].search(domain)

        exclude_categories = ('NET', 'GROSS', 'TAXABLE', 'COMP')
        
        earnings = {}
        deductions = {}
        
        medical_deductions = 0.0
        sec_medical_deductions = 0.0
        tax_credit = 0.0
        sec_tax_credit = 0.0

        for line in lines:
            cat = line.category_id.code
            rule_name = line.salary_rule_id.name
            val = abs(line.total)
            sec_val = abs(line.hao_secondary_total)
            
            if val == 0 and sec_val == 0:
                continue
                
            if cat in exclude_categories:
                continue
                
            if cat == 'MED_AID' or 'medical' in rule_name.lower():
                medical_deductions += val
                sec_medical_deductions += sec_val
            
            if cat == 'TAX_CREDIT' or 'tax credit' in rule_name.lower():
                tax_credit += val
                sec_tax_credit += sec_val
                continue
                
            is_deduction = False
            current_cat = line.category_id
            while current_cat:
                if current_cat.code == 'DED' or 'deduction' in current_cat.name.lower():
                    is_deduction = True
                    break
                current_cat = current_cat.parent_id
            
            if is_deduction:
                if rule_name not in deductions:
                    deductions[rule_name] = {'amount': 0.0, 'sec_amount': 0.0}
                deductions[rule_name]['amount'] += val
                deductions[rule_name]['sec_amount'] += sec_val
            else:
                if rule_name not in earnings:
                    earnings[rule_name] = {'amount': 0.0, 'sec_amount': 0.0}
                earnings[rule_name]['amount'] += val
                earnings[rule_name]['sec_amount'] += sec_val

        earn_list = [{'name': k, 'amount': v['amount'], 'sec_amount': v['sec_amount']} for k, v in earnings.items() if v['amount'] > 0 or v['sec_amount'] > 0]
        ded_list = [{'name': k, 'amount': v['amount'], 'sec_amount': v['sec_amount']} for k, v in deductions.items() if v['amount'] > 0 or v['sec_amount'] > 0]
        
        earn_list.sort(key=lambda x: x['amount'], reverse=True)
        ded_list.sort(key=lambda x: x['amount'], reverse=True)

        return {
            'doc_ids': docids,
            'doc_model': 'havano.zim.report.wizard',
            'docs': wizard,
            'company': wizard.company_id,
            'earnings': earn_list,
            'deductions': ded_list,
            'total_earnings': sum(e['amount'] for e in earn_list),
            'total_deductions': sum(d['amount'] for d in ded_list),
            'sec_total_earnings': sum(e['sec_amount'] for e in earn_list),
            'sec_total_deductions': sum(d['sec_amount'] for d in ded_list),
            'medical_deductions': medical_deductions,
            'sec_medical_deductions': sec_medical_deductions,
            'tax_credit': tax_credit,
            'sec_tax_credit': sec_tax_credit,
        }

class ReportZimraP2(models.AbstractModel):
    _name = 'report.havano_payroll.report_zimra_p2'
    _description = 'ZIMRA P2 Report'

    def _get_report_values(self, docids, data=None):
        wizard = self.env['havano.zim.report.wizard'].browse(docids)
        run_id = wizard.payslip_run_id

        domain = [('slip_id.payslip_run_id', '=', run_id.id), ('slip_id.state', 'in', ('draft', 'done', 'validated', 'paid'))]
        lines = self.env['hr.payslip.line'].search(domain)

        total_remuneration = 0.0
        gross_paye = 0.0
        aids_levy = 0.0

        for line in lines:
            if line.code == 'GROSS':
                total_remuneration += line.total
            elif line.code == 'PAYE':
                gross_paye += abs(line.total)
            elif line.code == 'AIDS':
                aids_levy += abs(line.total)

        employee_ids = self.env['hr.payslip'].search([
            ('payslip_run_id', '=', run_id.id),
            ('state', 'in', ('draft', 'done', 'validated', 'paid'))
        ]).mapped('employee_id')
        
        number_of_employees = len(employee_ids)
        total_tax_due = gross_paye + aids_levy

        return {
            'doc_ids': docids,
            'doc_model': 'havano.zim.report.wizard',
            'docs': wizard,
            'company': wizard.company_id,
            'total_remuneration': total_remuneration,
            'number_of_employees': number_of_employees,
            'gross_paye': gross_paye,
            'aids_levy': aids_levy,
            'total_tax_due': total_tax_due,
            'tax_period': f"{run_id.date_start.strftime('%B %Y')}",
            'due_date': "10th of the following month",
        }

