from odoo import models, fields, api

class HrVersion(models.Model):
    _inherit = 'hr.version'

    hao_allow_multi_payroll_currency = fields.Boolean(
        related='company_id.hao_allow_multi_payroll_currency',
        readonly=True
    )
    
    structure_id = fields.Many2one(
        'hr.payroll.structure', string="Salary Structure",
        compute='_compute_structure_id', store=True, readonly=False,
        domain="[('type_id', '=', structure_type_id)]",
        help="Salary structure that will be used to compute the payslip."
    )

    @api.depends('structure_type_id')
    def _compute_structure_id(self):
        for version in self:
            if not version.structure_id or (version.structure_id.type_id and version.structure_type_id and version.structure_id.type_id != version.structure_type_id):
                version.structure_id = version.structure_type_id.default_struct_id
    hao_medical_aid_currency_id = fields.Many2one(
        'res.currency', string="Medical Aid Currency",
        default=lambda self: self.env.company.currency_id, tracking=True
    )
    hao_medical_aid_amount = fields.Monetary(
        string="Medical Aid Amount",
        currency_field='hao_medical_aid_currency_id',
        tracking=True,
        help="Monthly Medical Aid deduction amount."
    )
    
    hao_funeral_policy_currency_id = fields.Many2one(
        'res.currency', string="Funeral Policy Currency",
        default=lambda self: self.env.company.currency_id, tracking=True
    )
    hao_funeral_policy_amount = fields.Monetary(
        string="Funeral Policy Amount",
        currency_field='hao_funeral_policy_currency_id',
        tracking=True,
        help="Monthly Funeral Policy deduction amount."
    )

    # ==================== FDS YTD Opening Balances ====================
    # Used for mid-year hires to carry forward data from a previous employer's P6 form.
    # These amounts are included in cumulative FDS calculations alongside payslips in Odoo.
    ytd_opening_taxable_income = fields.Float(
        string='YTD Opening Taxable Income',
        default=0.0,
        help='[FDS] Total taxable income earned at the PREVIOUS employer this tax year (Jan-Dec). '
             'Enter from the employee\'s P6 form. Leave 0 if this employee started the tax year with this company.'
    )
    ytd_opening_paye_paid = fields.Float(
        string='YTD Opening PAYE Paid',
        default=0.0,
        help='[FDS] Total PAYE already deducted by the PREVIOUS employer this tax year (Jan-Dec). '
             'Enter from the employee\'s P6 form. Leave 0 if this employee started the tax year with this company.'
    )
    ytd_opening_months_worked = fields.Integer(
        string='YTD Opening Months Worked',
        default=0,
        help='[FDS] Number of months worked at the PREVIOUS employer this tax year (Jan-Dec). '
             'Enter from the employee\'s P6 form. Leave 0 if this employee started the tax year with this company.'
    )

    hao_dual_currency_mode = fields.Selection([
        ('fixed', 'Fixed Amounts (Scenario 1)'),
        ('percentage', 'Pegged Percentage (Scenario 2)'),
        ('full_conversion', '100% Conversion (Scenario 3)')
    ], string='Dual Currency Mode', default='fixed',
       help='Scenario 1: Fixed USD and Fixed ZWG (uses Employee Secondary Wage).\n'
            'Scenario 2: Pegged in USD, paid partially in ZWG at exchange rate.\n'
            'Scenario 3: Pegged in USD, paid fully in ZWG at exchange rate.')
    
    hao_secondary_wage_percentage = fields.Float(
        string='Secondary Wage Percentage (%)',
        default=50.0,
        help='Percentage of the basic salary to be paid in the secondary currency (for Scenario 2).'
    )

    # ==================== Single vs Dual Currency & Split Pay ====================
    hao_currency_payment_setup = fields.Selection([
        ('single', 'Single Currency'),
        ('dual', 'Dual Currency'),
    ], string='Currency Payment Setup', default='single', tracking=True,
       help='Indicate whether this employee is paid in a single currency or dual currencies.')

    hao_dual_currency_method = fields.Selection([
        ('exact', 'Exact Amounts'),
        ('percentage', 'Percentages'),
    ], string='Dual Currency Allocation Method', default='exact', tracking=True,
       help='Choose whether dual currency pay is defined by exact amounts per currency or by percentages.')

    hao_primary_currency_id = fields.Many2one(
        'res.currency', string='Primary Currency',
        default=lambda self: self.env.company.currency_id, tracking=True
    )
    hao_primary_amount = fields.Monetary(
        string='Primary Currency Amount',
        currency_field='hao_primary_currency_id',
        tracking=True,
        help='Portion of basic salary paid in the primary currency.'
    )
    hao_primary_percentage = fields.Float(
        string='Primary Currency Percentage (%)',
        default=100.0,
        tracking=True,
        help='Percentage of basic salary paid in the primary currency.'
    )

    hao_secondary_currency_id = fields.Many2one(
        'res.currency', string='Secondary Currency',
        default=lambda self: self.env.company.hao_secondary_payroll_currency_id, tracking=True
    )
    hao_secondary_amount = fields.Monetary(
        string='Secondary Currency Amount',
        currency_field='hao_secondary_currency_id',
        tracking=True,
        help='Portion of basic salary paid in the secondary currency.'
    )
    hao_secondary_percentage = fields.Float(
        string='Secondary Currency Percentage (%)',
        default=0.0,
        tracking=True,
        help='Percentage of basic salary paid in the secondary currency.'
    )

    hao_enable_split_pay = fields.Boolean(
        string='Split Invoicing / Pay Enabled',
        default=False,
        tracking=True,
        help='If checked, the payroll system will split employee earnings between primary and secondary currencies.'
    )

    @api.onchange('hao_currency_payment_setup')
    def _onchange_hao_currency_payment_setup(self):
        for version in self:
            if version.hao_currency_payment_setup == 'single':
                version.hao_enable_split_pay = False
                version.hao_dual_currency_mode = 'fixed'
                version.hao_secondary_amount = 0.0
                version.hao_secondary_percentage = 0.0
                version.hao_primary_percentage = 100.0
                if hasattr(version, 'employee_id') and version.employee_id:
                    version.employee_id.hao_secondary_wage = 0.0
            elif version.hao_currency_payment_setup == 'dual':
                version.hao_enable_split_pay = True
                if not version.hao_dual_currency_method:
                    version.hao_dual_currency_method = 'exact'
                wage = version.contract_wage or 0.0
                rate = version.company_id.hao_exchange_rate or 1.0
                if version.hao_dual_currency_method == 'exact' and wage > 0:
                    if not version.hao_primary_amount:
                        version.hao_primary_amount = round(wage / 2.0, 2)
                    remaining = max(wage - version.hao_primary_amount, 0.0)
                    sec_amt = round(remaining * rate, 2)
                    version.hao_secondary_amount = sec_amt
                    if hasattr(version, 'employee_id') and version.employee_id:
                        version.employee_id.hao_secondary_wage = sec_amt
                    version.hao_primary_percentage = round((version.hao_primary_amount / wage) * 100.0, 2)
                    version.hao_secondary_percentage = round(100.0 - version.hao_primary_percentage, 2)

    @api.onchange('hao_dual_currency_method')
    def _onchange_hao_dual_currency_method(self):
        for version in self:
            wage = version.contract_wage or 0.0
            rate = version.company_id.hao_exchange_rate or 1.0
            if version.hao_dual_currency_method == 'exact':
                version.hao_dual_currency_mode = 'fixed'
                if wage > 0:
                    if not version.hao_primary_amount:
                        version.hao_primary_amount = round(wage / 2.0, 2)
                    remaining = max(wage - version.hao_primary_amount, 0.0)
                    sec_amt = round(remaining * rate, 2)
                    version.hao_secondary_amount = sec_amt
                    if hasattr(version, 'employee_id') and version.employee_id:
                        version.employee_id.hao_secondary_wage = sec_amt
                    version.hao_primary_percentage = round((version.hao_primary_amount / wage) * 100.0, 2)
                    version.hao_secondary_percentage = round(100.0 - version.hao_primary_percentage, 2)
            elif version.hao_dual_currency_method == 'percentage':
                version.hao_dual_currency_mode = 'percentage'
                if not version.hao_secondary_percentage:
                    version.hao_secondary_percentage = version.hao_secondary_wage_percentage or 50.0
                version.hao_primary_percentage = round(100.0 - version.hao_secondary_percentage, 2)
                if wage > 0:
                    version.hao_primary_amount = round(wage * (version.hao_primary_percentage / 100.0), 2)
                    sec_amt = round(wage * (version.hao_secondary_percentage / 100.0) * rate, 2)
                    version.hao_secondary_amount = sec_amt
                    if hasattr(version, 'employee_id') and version.employee_id:
                        version.employee_id.hao_secondary_wage = sec_amt

    @api.onchange('hao_primary_amount', 'contract_wage')
    def _onchange_hao_primary_amount(self):
        for version in self:
            if version.hao_currency_payment_setup == 'dual' and version.hao_dual_currency_method == 'exact':
                wage = version.contract_wage or 0.0
                rate = version.company_id.hao_exchange_rate or 1.0
                prim = version.hao_primary_amount or 0.0
                if wage > 0:
                    remaining = max(wage - prim, 0.0)
                    sec_amt = round(remaining * rate, 2)
                    version.hao_secondary_amount = sec_amt
                    if hasattr(version, 'employee_id') and version.employee_id:
                        version.employee_id.hao_secondary_wage = sec_amt
                    version.hao_primary_percentage = round((prim / wage) * 100.0, 2)
                    version.hao_secondary_percentage = round(100.0 - version.hao_primary_percentage, 2)

    @api.onchange('hao_secondary_amount')
    def _onchange_hao_secondary_amount(self):
        for version in self:
            if version.hao_currency_payment_setup == 'dual' and version.hao_dual_currency_method == 'exact':
                wage = version.contract_wage or 0.0
                rate = version.company_id.hao_exchange_rate or 1.0
                sec = version.hao_secondary_amount or 0.0
                if hasattr(version, 'employee_id') and version.employee_id:
                    version.employee_id.hao_secondary_wage = sec
                if wage > 0 and rate > 0:
                    sec_in_base = sec / rate
                    prim = max(round(wage - sec_in_base, 2), 0.0)
                    version.hao_primary_amount = prim
                    version.hao_primary_percentage = round((prim / wage) * 100.0, 2)
                    version.hao_secondary_percentage = round(100.0 - version.hao_primary_percentage, 2)

    @api.onchange('hao_primary_percentage', 'contract_wage')
    def _onchange_hao_primary_percentage(self):
        for version in self:
            if version.hao_currency_payment_setup == 'dual' and version.hao_dual_currency_method == 'percentage':
                wage = version.contract_wage or 0.0
                rate = version.company_id.hao_exchange_rate or 1.0
                if 0.0 <= version.hao_primary_percentage <= 100.0:
                    version.hao_secondary_percentage = round(100.0 - version.hao_primary_percentage, 2)
                    version.hao_secondary_wage_percentage = version.hao_secondary_percentage
                    if wage > 0:
                        prim = round(wage * (version.hao_primary_percentage / 100.0), 2)
                        sec = round(wage * (version.hao_secondary_percentage / 100.0) * rate, 2)
                        version.hao_primary_amount = prim
                        version.hao_secondary_amount = sec
                        if hasattr(version, 'employee_id') and version.employee_id:
                            version.employee_id.hao_secondary_wage = sec

    @api.onchange('hao_secondary_percentage', 'contract_wage')
    def _onchange_hao_secondary_percentage(self):
        for version in self:
            if version.hao_currency_payment_setup == 'dual' and version.hao_dual_currency_method == 'percentage':
                wage = version.contract_wage or 0.0
                rate = version.company_id.hao_exchange_rate or 1.0
                if 0.0 <= version.hao_secondary_percentage <= 100.0:
                    version.hao_primary_percentage = round(100.0 - version.hao_secondary_percentage, 2)
                    version.hao_secondary_wage_percentage = version.hao_secondary_percentage
                    if wage > 0:
                        prim = round(wage * (version.hao_primary_percentage / 100.0), 2)
                        sec = round(wage * (version.hao_secondary_percentage / 100.0) * rate, 2)
                        version.hao_primary_amount = prim
                        version.hao_secondary_amount = sec
                        if hasattr(version, 'employee_id') and version.employee_id:
                            version.employee_id.hao_secondary_wage = sec

    def write(self, vals):
        if vals.get('hao_currency_payment_setup') == 'dual':
            vals['hao_enable_split_pay'] = True
            method = vals.get('hao_dual_currency_method') or self.hao_dual_currency_method or 'exact'
            rate = self.company_id.hao_exchange_rate or 1.0
            wage = vals.get('contract_wage') or vals.get('wage') or self.contract_wage or 0.0
            if method == 'exact':
                vals['hao_dual_currency_mode'] = 'fixed'
                if 'hao_primary_amount' in vals and 'hao_secondary_amount' not in vals:
                    prim = vals['hao_primary_amount']
                    sec_amt = round(max(wage - prim, 0.0) * rate, 2)
                    vals['hao_secondary_amount'] = sec_amt
                    if wage > 0:
                        vals['hao_primary_percentage'] = round((prim / wage) * 100.0, 2)
                        vals['hao_secondary_percentage'] = round(100.0 - vals['hao_primary_percentage'], 2)
                elif 'hao_secondary_amount' in vals and 'hao_primary_amount' not in vals:
                    sec = vals['hao_secondary_amount']
                    prim = round(max(wage - (sec / rate if rate else 0.0), 0.0), 2)
                    vals['hao_primary_amount'] = prim
                    if wage > 0:
                        vals['hao_primary_percentage'] = round((prim / wage) * 100.0, 2)
                        vals['hao_secondary_percentage'] = round(100.0 - vals['hao_primary_percentage'], 2)
                
                sec_to_set = vals.get('hao_secondary_amount') or self.hao_secondary_amount
                if sec_to_set is not None:
                    for version in self:
                        if hasattr(version, 'employee_id') and version.employee_id:
                            version.employee_id.hao_secondary_wage = sec_to_set
            elif method == 'percentage':
                vals['hao_dual_currency_mode'] = 'percentage'
                if 'hao_secondary_percentage' in vals:
                    sec_pct = vals['hao_secondary_percentage']
                    vals['hao_secondary_wage_percentage'] = sec_pct
                    vals['hao_primary_percentage'] = round(100.0 - sec_pct, 2)
                elif 'hao_primary_percentage' in vals:
                    prim_pct = vals['hao_primary_percentage']
                    sec_pct = round(100.0 - prim_pct, 2)
                    vals['hao_secondary_percentage'] = sec_pct
                    vals['hao_secondary_wage_percentage'] = sec_pct
                else:
                    sec_pct = self.hao_secondary_percentage or 50.0

                if wage > 0:
                    vals['hao_primary_amount'] = round(wage * ((100.0 - sec_pct) / 100.0), 2)
                    sec_amt = round(wage * (sec_pct / 100.0) * rate, 2)
                    vals['hao_secondary_amount'] = sec_amt
                    for version in self:
                        if hasattr(version, 'employee_id') and version.employee_id:
                            version.employee_id.hao_secondary_wage = sec_amt
        elif vals.get('hao_currency_payment_setup') == 'single':
            vals['hao_enable_split_pay'] = False
            vals['hao_secondary_amount'] = 0.0
            vals['hao_secondary_percentage'] = 0.0
            vals['hao_primary_percentage'] = 100.0
            vals['hao_dual_currency_mode'] = 'fixed'
            for version in self:
                if hasattr(version, 'employee_id') and version.employee_id:
                    version.employee_id.hao_secondary_wage = 0.0
        return super().write(vals)


