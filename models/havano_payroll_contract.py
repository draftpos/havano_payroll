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
