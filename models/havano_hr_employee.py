from odoo import models, fields, api
from datetime import date


class HavanoNecGrade(models.Model):
    _name = 'havano.nec.grade'
    _description = 'NEC Grade'

    name = fields.Char('Grade Name', required=True)
    description = fields.Text('Description')


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    ssn_number = fields.Char('SSN Number', help='Employee NEC/SSN Number')
    nec_grade_id = fields.Many2one('havano.nec.grade', string='NEC Grade')

    is_blind = fields.Boolean(
        string='Blind',
        default=False,
        help='Check if the employee is blind (entitled to ZIMRA tax credit)'
    )

    hao_contract_structure_id = fields.Many2one(
        'hr.payroll.structure',
        related='version_id.structure_id',
        readonly=False,
        string="Active Pay Structure",
        groups="hr_payroll.group_hr_payroll_user"
    )

    hao_contract_structure_type_id = fields.Many2one(
        'hr.payroll.structure.type',
        related='version_id.structure_type_id',
        readonly=False,
        string="Active Salary Structure",
        groups="hr_payroll.group_hr_payroll_user"
    )

    hao_medical_aid_currency_id = fields.Many2one(
        'res.currency',
        related='version_id.hao_medical_aid_currency_id',
        inherited=True,
        readonly=False,
        groups="hr.group_hr_manager"
    )

    hao_medical_aid_amount = fields.Monetary(
        related='version_id.hao_medical_aid_amount',
        currency_field='hao_medical_aid_currency_id',
        inherited=True,
        readonly=False,
        groups="hr.group_hr_manager"
    )

    hao_funeral_policy_currency_id = fields.Many2one(
        'res.currency',
        related='version_id.hao_funeral_policy_currency_id',
        inherited=True,
        readonly=False,
        groups="hr.group_hr_manager"
    )

    hao_funeral_policy_amount = fields.Monetary(
        related='version_id.hao_funeral_policy_amount',
        currency_field='hao_funeral_policy_currency_id',
        inherited=True,
        readonly=False,
        groups="hr.group_hr_manager"
    )

    is_disabled = fields.Boolean(
        string='Disabled',
        default=False,
        help='Check if the employee is disabled (entitled to ZIMRA tax credit)'
    )

    is_elderly = fields.Boolean(
        string='Elderly',
        default=False,
        help='Check if the employee is elderly (65+, entitled to ZIMRA tax credit)'
    )

    @api.depends('birthday')
    def _compute_is_over_65(self):
        """Compute if employee is over 65 years old"""
        for emp in self:
            emp.is_over_65 = False
            if emp.birthday:
                today = fields.Date.today()
                age = today.year - emp.birthday.year
                if (today.month, today.day) < (emp.birthday.month, emp.birthday.day):
                    age -= 1
                emp.is_over_65 = age >= 65

    is_over_65 = fields.Boolean(
        string='Over 65',
        compute='_compute_is_over_65',
        store=True,
        help='Computed: True if employee is 65 years or older (entitled to ZIMRA tax credit)'
    )

    hao_allow_multi_payroll_currency = fields.Boolean(
        related='company_id.hao_allow_multi_payroll_currency'
    )
    hao_secondary_payroll_currency_id = fields.Many2one(
        'res.currency',
        related='company_id.hao_secondary_payroll_currency_id'
    )
    hao_secondary_wage = fields.Monetary(
        string='Secondary Wage',
        currency_field='hao_secondary_payroll_currency_id',
        tracking=True,
        help="Employee's secondary currency wage."
    )

    # ==================== SMART BUTTON FIELDS ====================
    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        readonly=True
    )

    hao_basic_salary = fields.Monetary(
        string='Basic Salary',
        compute='_compute_hao_basic_salary',
        currency_field='currency_id',
        groups="hr_payroll.group_hr_payroll_user"
    )

    hao_annual_leave_balance = fields.Float(
        string='Annual Leave Balance (Days)',
        compute='_compute_hao_annual_leave_balance',
        groups="hr_payroll.group_hr_payroll_user"
    )

    @api.depends('version_id', 'version_id.contract_wage')
    def _compute_hao_basic_salary(self):
        for emp in self:
            emp.hao_basic_salary = emp.version_id.contract_wage if emp.version_id else 0.0

    def _compute_hao_annual_leave_balance(self):
        leave_type = self.env.ref('havano_payroll.havano_annual_leave_type', raise_if_not_found=False)
        for emp in self:
            balance = 0.0
            if leave_type and emp.id:
                allocations = self.env['hr.leave.allocation'].search([
                    ('employee_id', '=', emp.id),
                    ('holiday_status_id', '=', leave_type.id),
                    ('state', '=', 'validate'),
                ])
                allocated = sum(allocations.mapped('number_of_days'))
                leaves = self.env['hr.leave'].search([
                    ('employee_id', '=', emp.id),
                    ('holiday_status_id', '=', leave_type.id),
                    ('state', '=', 'validate'),
                ])
                taken = sum(leaves.mapped('number_of_days'))
                balance = allocated - taken
            emp.hao_annual_leave_balance = balance

    # ==================== Leave Allocation & Currency Setup ====================
    hao_max_annual_leave_days = fields.Float(
        string='Max Annual Leave Days',
        default=30.0,
        help='Initial annual leave allocation in days granted upon employee creation.'
    )

    hao_currency_payment_setup = fields.Selection(
        related='version_id.hao_currency_payment_setup',
        inherited=True,
        readonly=False,
        string='Currency Payment Setup'
    )
    hao_dual_currency_method = fields.Selection(
        related='version_id.hao_dual_currency_method',
        inherited=True,
        readonly=False,
        string='Dual Currency Allocation Method'
    )
    hao_primary_currency_id = fields.Many2one(
        'res.currency',
        related='version_id.hao_primary_currency_id',
        inherited=True,
        readonly=False,
        string='Primary Currency'
    )
    hao_primary_amount = fields.Monetary(
        related='version_id.hao_primary_amount',
        currency_field='hao_primary_currency_id',
        inherited=True,
        readonly=False,
        string='Primary Currency Amount'
    )
    hao_primary_percentage = fields.Float(
        related='version_id.hao_primary_percentage',
        inherited=True,
        readonly=False,
        string='Primary Currency Percentage (%)'
    )
    hao_secondary_currency_id = fields.Many2one(
        'res.currency',
        related='version_id.hao_secondary_currency_id',
        inherited=True,
        readonly=False,
        string='Secondary Currency'
    )
    hao_secondary_amount = fields.Monetary(
        related='version_id.hao_secondary_amount',
        currency_field='hao_secondary_currency_id',
        inherited=True,
        readonly=False,
        string='Secondary Currency Amount'
    )
    hao_secondary_percentage = fields.Float(
        related='version_id.hao_secondary_percentage',
        inherited=True,
        readonly=False,
        string='Secondary Currency Percentage (%)'
    )
    hao_enable_split_pay = fields.Boolean(
        related='version_id.hao_enable_split_pay',
        inherited=True,
        readonly=False,
        string='Split Invoicing / Pay Enabled'
    )
    hao_rule_split_ids = fields.One2many(
        related='version_id.hao_rule_split_ids',
        readonly=False,
        string='Allowance & Rule Currency Splits'
    )

    @api.onchange('hao_currency_payment_setup')
    def _onchange_hao_currency_payment_setup(self):
        for emp in self:
            if emp.hao_currency_payment_setup == 'single':
                emp.hao_enable_split_pay = False
                emp.hao_secondary_wage = 0.0
                emp.hao_secondary_amount = 0.0
                emp.hao_secondary_percentage = 0.0
                emp.hao_primary_percentage = 100.0
                if emp.version_id:
                    emp.version_id.hao_dual_currency_mode = 'fixed'
            elif emp.hao_currency_payment_setup == 'dual':
                emp.hao_enable_split_pay = True
                if not emp.hao_dual_currency_method:
                    emp.hao_dual_currency_method = 'exact'

    @api.onchange('hao_dual_currency_method')
    def _onchange_hao_dual_currency_method(self):
        for emp in self:
            if emp.hao_dual_currency_method == 'exact':
                if emp.version_id:
                    emp.version_id.hao_dual_currency_mode = 'fixed'
            elif emp.hao_dual_currency_method == 'percentage':
                if emp.version_id:
                    emp.version_id.hao_dual_currency_mode = 'percentage'
                if not emp.hao_secondary_percentage and emp.version_id and emp.version_id.hao_secondary_wage_percentage:
                    emp.hao_secondary_percentage = emp.version_id.hao_secondary_wage_percentage
                if emp.hao_secondary_percentage:
                    emp.hao_primary_percentage = round(100.0 - emp.hao_secondary_percentage, 2)

    @api.onchange('hao_primary_amount', 'wage', 'hao_currency_payment_setup', 'hao_dual_currency_method')
    def _onchange_hao_primary_amount(self):
        for emp in self:
            if emp.hao_currency_payment_setup == 'dual' and emp.hao_dual_currency_method == 'exact':
                wage = emp.wage or (emp.version_id.contract_wage if emp.version_id else 0.0) or 0.0
                rate = emp.company_id.hao_exchange_rate or 1.0
                prim = emp.hao_primary_amount or 0.0
                if wage > 0:
                    remaining = max(wage - prim, 0.0)
                    sec_amt = round(remaining * rate, 2)
                    emp.hao_secondary_amount = sec_amt
                    emp.hao_secondary_wage = sec_amt
                    emp.hao_primary_percentage = round((prim / wage) * 100.0, 2)
                    emp.hao_secondary_percentage = round(100.0 - emp.hao_primary_percentage, 2)

    @api.onchange('hao_secondary_amount')
    def _onchange_hao_secondary_amount(self):
        for emp in self:
            if emp.hao_currency_payment_setup == 'dual' and emp.hao_dual_currency_method == 'exact':
                emp.hao_secondary_wage = emp.hao_secondary_amount
                wage = emp.wage or (emp.version_id.contract_wage if emp.version_id else 0.0) or 0.0
                rate = emp.company_id.hao_exchange_rate or 1.0
                sec = emp.hao_secondary_amount or 0.0
                if wage > 0 and rate > 0:
                    sec_in_base = sec / rate
                    prim = max(round(wage - sec_in_base, 2), 0.0)
                    emp.hao_primary_amount = prim
                    emp.hao_primary_percentage = round((prim / wage) * 100.0, 2)
                    emp.hao_secondary_percentage = round(100.0 - emp.hao_primary_percentage, 2)

    @api.onchange('hao_primary_percentage', 'wage')
    def _onchange_hao_primary_percentage(self):
        for emp in self:
            if emp.hao_currency_payment_setup == 'dual' and emp.hao_dual_currency_method == 'percentage':
                wage = emp.wage or (emp.version_id.contract_wage if emp.version_id else 0.0) or 0.0
                rate = emp.company_id.hao_exchange_rate or 1.0
                if 0.0 <= emp.hao_primary_percentage <= 100.0:
                    emp.hao_secondary_percentage = round(100.0 - emp.hao_primary_percentage, 2)
                    if emp.version_id:
                        emp.version_id.hao_secondary_wage_percentage = emp.hao_secondary_percentage
                    if wage > 0:
                        prim = round(wage * (emp.hao_primary_percentage / 100.0), 2)
                        sec = round(wage * (emp.hao_secondary_percentage / 100.0) * rate, 2)
                        emp.hao_primary_amount = prim
                        emp.hao_secondary_amount = sec
                        emp.hao_secondary_wage = sec

    @api.onchange('hao_secondary_percentage', 'wage')
    def _onchange_hao_secondary_percentage(self):
        for emp in self:
            if emp.hao_currency_payment_setup == 'dual' and emp.hao_dual_currency_method == 'percentage':
                wage = emp.wage or (emp.version_id.contract_wage if emp.version_id else 0.0) or 0.0
                rate = emp.company_id.hao_exchange_rate or 1.0
                if 0.0 <= emp.hao_secondary_percentage <= 100.0:
                    emp.hao_primary_percentage = round(100.0 - emp.hao_secondary_percentage, 2)
                    if emp.version_id:
                        emp.version_id.hao_secondary_wage_percentage = emp.hao_secondary_percentage
                    if wage > 0:
                        prim = round(wage * (emp.hao_primary_percentage / 100.0), 2)
                        sec = round(wage * (emp.hao_secondary_percentage / 100.0) * rate, 2)
                        emp.hao_primary_amount = prim
                        emp.hao_secondary_amount = sec
                        emp.hao_secondary_wage = sec

    @api.model_create_multi
    def create(self, vals_list):
        employees = super().create(vals_list)
        leave_type = self.env.ref('havano_payroll.havano_annual_leave_type', raise_if_not_found=False)
        if not leave_type:
            leave_type = self.env['hr.leave.type'].sudo().search([('name', 'ilike', 'Annual Leave')], limit=1)

        for emp in employees:
            # Sync secondary wage if dual currency with exact amounts was specified
            if emp.hao_currency_payment_setup == 'dual':
                if emp.hao_dual_currency_method == 'exact' and emp.hao_secondary_amount and not emp.hao_secondary_wage:
                    emp.hao_secondary_wage = emp.hao_secondary_amount
                elif emp.hao_dual_currency_method == 'percentage' and emp.version_id and emp.hao_secondary_percentage:
                    emp.version_id.hao_secondary_wage_percentage = emp.hao_secondary_percentage

            # 1. Automatically allocate max Annual Leave Days when an employee is added
            if leave_type:
                existing_alloc = self.env['hr.leave.allocation'].sudo().search([
                    ('employee_id', '=', emp.id),
                    ('holiday_status_id', '=', leave_type.id),
                ], limit=1)
                if not existing_alloc:
                    max_days = emp.hao_max_annual_leave_days if emp.hao_max_annual_leave_days > 0 else 30.0
                    start_date = getattr(emp, 'first_contract_date', False) or getattr(emp, 'contract_date_start', False) or (emp.version_id and getattr(emp.version_id, 'date_start', False)) or fields.Date.today()
                    alloc = self.env['hr.leave.allocation'].sudo().create({
                        'name': f"Initial Annual Leave Allocation - {emp.name}",
                        'employee_id': emp.id,
                        'holiday_status_id': leave_type.id,
                        'number_of_days': max_days,
                        'allocation_type': 'regular',
                        'date_from': start_date,
                    })
                    try:
                        alloc._action_validate()
                    except Exception:
                        try:
                            alloc.action_approve()
                        except Exception:
                            pass
        return employees

    def write(self, vals):
        if vals.get('hao_currency_payment_setup') == 'dual':
            vals['hao_enable_split_pay'] = True
            method = vals.get('hao_dual_currency_method') or self.hao_dual_currency_method or 'exact'
            if method == 'exact':
                if 'hao_secondary_amount' in vals:
                    vals['hao_secondary_wage'] = vals['hao_secondary_amount']
            elif method == 'percentage':
                for emp in self:
                    if emp.version_id:
                        if 'hao_secondary_percentage' in vals:
                            emp.version_id.hao_secondary_wage_percentage = vals['hao_secondary_percentage']
                        elif 'hao_primary_percentage' in vals:
                            emp.version_id.hao_secondary_wage_percentage = round(100.0 - vals['hao_primary_percentage'], 2)
        elif vals.get('hao_currency_payment_setup') == 'single':
            vals['hao_enable_split_pay'] = False
            vals['hao_secondary_wage'] = 0.0
            vals['hao_secondary_amount'] = 0.0
            vals['hao_secondary_percentage'] = 0.0
            vals['hao_primary_percentage'] = 100.0
        return super().write(vals)

    def action_open_payslips(self):
        return {
            'name': 'Payslips',
            'type': 'ir.actions.act_window',
            'res_model': 'hr.payslip',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }

    def action_open_leave_allocations(self):
        return {
            'name': 'Leaves',
            'type': 'ir.actions.act_window',
            'res_model': 'hr.leave',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }

# ==================== YTD BALANCE MODEL ====================
class HavanoEmployeeYTD(models.Model):
    """
    Stores Year-To-Date opening balances per employee for FDS calculations.
    One record per employee per tax year — used for mid-year hires or
    employees transferring from another employer.
    """
    _name = 'havano.employee.ytd'
    _description = 'Employee YTD FDS Opening Balances'
    _order = 'employee_id'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        ondelete='cascade',
        index=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
    )
    tax_year = fields.Integer(
        string='Tax Year',
        default=lambda self: date.today().year,
        required=True,
        help='The ZIMRA tax year (calendar year) these balances apply to.'
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        readonly=True
    )
    ytd_opening_taxable_income = fields.Monetary(
        string='YTD Taxable Income',
        default=0.0,
        currency_field='currency_id',
        help='Total taxable income earned at a PREVIOUS employer this tax year (from P6 form).'
    )
    ytd_opening_paye_paid = fields.Monetary(
        string='YTD PAYE Paid',
        default=0.0,
        currency_field='currency_id',
        help='Total PAYE already deducted by a PREVIOUS employer this tax year (from P6 form).'
    )
    ytd_opening_months_worked = fields.Integer(
        string='Months Worked (Prev. Employer)',
        default=0,
        help='Number of months worked at a PREVIOUS employer this tax year (from P6 form).'
    )
    ytd_basic_salary = fields.Monetary(
        string='YTD Basic Salary',
        default=0.0,
        currency_field='currency_id',
        help='Total basic salary earned this tax year (from previous employer, P6 form).'
    )
    department_id = fields.Many2one(
        related='employee_id.department_id',
        string='Department',
        store=True,
        readonly=True
    )
    job_id = fields.Many2one(
        related='employee_id.job_id',
        string='Job Position',
        store=True,
        readonly=True
    )
    notes = fields.Char(
        string='Notes',
        help='e.g. transferred from XYZ Company mid-year'
    )

    _sql_constraints = [
        ('unique_employee_year', 'unique(employee_id, tax_year, company_id)',
         'A YTD balance record already exists for this employee and tax year.'),
    ]

    @api.model
    def _ensure_all_employees_have_ytd(self):
        """Create YTD records for all active employees for the current year
        if they don't already have one. Idempotent — safe to call repeatedly."""
        current_year = date.today().year
        company = self.env.company
        employees = self.env['hr.employee'].search([
            ('company_id', '=', company.id),
            ('active', '=', True),
        ])
        existing_emp_ids = self.search([
            ('tax_year', '=', current_year),
            ('company_id', '=', company.id),
        ]).mapped('employee_id').ids
        to_create = [
            {'employee_id': emp.id, 'tax_year': current_year, 'company_id': company.id}
            for emp in employees if emp.id not in existing_emp_ids
        ]
        if to_create:
            self.create(to_create)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None, **read_kwargs):
        """Auto-populate YTD rows for all active employees before listing."""
        self._ensure_all_employees_have_ytd()
        return super().search_read(domain=domain, fields=fields, offset=offset,
                                   limit=limit, order=order, **read_kwargs)

    @api.model
    def action_open_ytd_balances(self):
        self._ensure_all_employees_have_ytd()
        return {
            'name': 'FDS YTD Balances',
            'type': 'ir.actions.act_window',
            'res_model': 'havano.employee.ytd',
            'view_mode': 'list,form',
            'context': {'default_tax_year': date.today().year},
        }
