from odoo import models, fields, api

class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    hao_secondary_fixed_amount = fields.Float(
        string='Secondary Fixed Amount',
        digits='Payroll',
        help="Fixed amount in the secondary payroll currency."
    )

    hao_rule_percentage = fields.Float(
        string='Statutory Percentage (%)',
        default=0.0,
        help="Dynamic percentage used for rules like LAPF, UFAWUZ, etc."
    )

    def _get_currency_application_selection(self):
        company = self.env.company
        base = company.currency_id.name or 'USD'
        if not company.hao_allow_multi_payroll_currency:
            return [
                ('both', f'Base Currency ({base}) Only'),
                ('base_only', f'Base Currency ({base}) Only'),
                ('secondary_only', f'Base Currency ({base}) Only')
            ]
            
        secondary = company.hao_secondary_payroll_currency_id.name or 'ZWG'
        return [
            ('both', 'Apply to Both Currencies'),
            ('base_only', f'Base Currency ({base}) Only'),
            ('secondary_only', f'Secondary Currency ({secondary}) Only')
        ]

    hao_currency_application = fields.Selection(
        selection='_get_currency_application_selection',
        string='Currency Application',
        default='both',
        help="Determine which currencies this rule applies to."
    )




    hao_aids_levy_pct = fields.Float(
        string='AIDS Levy Percentage (%)',
        default=3.0,
        help="Percentage used for AIDS Levy computation."
    )

    hao_nec_pct = fields.Float(
        string='NEC Percentage (%)',
        default=1.5,
        help="Percentage used for NEC deduction."
    )

    hao_nssa_percentage = fields.Float(
        string='NSSA Percentage',
        default=4.5,
        help="Percentage used for NSSA computation."
    )

    hao_nssa_base_cap = fields.Monetary(
        string='NSSA Base Cap',
        default=700.0,
        currency_field='currency_id',
        help="Maximum cap for NSSA calculation in base currency."
    )

    hao_nssa_secondary_cap_label = fields.Char(compute='_compute_hao_nssa_secondary_cap_label')

    @api.depends('hao_secondary_payroll_currency_id')
    def _compute_hao_nssa_secondary_cap_label(self):
        for rule in self:
            if rule.hao_secondary_payroll_currency_id:
                rule.hao_nssa_secondary_cap_label = f"NSSA Cap ({rule.hao_secondary_payroll_currency_id.name})"
            else:
                rule.hao_nssa_secondary_cap_label = "NSSA Cap (Secondary)"

    hao_nssa_secondary_cap = fields.Monetary(
        string='NSSA Secondary Cap',
        currency_field='hao_secondary_payroll_currency_id',
        help="Maximum cap for NSSA calculation in secondary currency."
    )

    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    
    hao_allow_multi_payroll_currency = fields.Boolean(
        related='company_id.hao_allow_multi_payroll_currency'
    )
    
    hao_secondary_payroll_currency_id = fields.Many2one(
        'res.currency',
        related='company_id.hao_secondary_payroll_currency_id'
    )
    
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    hao_policy_payment_mode = fields.Selection([
        ('employee', 'Employee Pays Full Amount'),
        ('employer', 'Employer Pays Full Amount'),
        ('shared', 'Shared Cost')
    ], string='Policy Payment Mode', default='employee', help="Determines how the policy cost is split.")

    hao_policy_emp_pct = fields.Float(string='Employee Contribution (%)', default=50.0, help="Percentage paid by the employee if shared.")
    hao_policy_comp_pct = fields.Float(string='Employer Contribution (%)', default=50.0, help="Percentage paid by the employer if shared.")
    
    hao_apply_tax_credit = fields.Boolean(string='Apply Tax Credit (Medical Aid)', default=False, help="If checked, 50% of the employee's contribution will be calculated as a tax credit.")

    hao_tax_credit_elderly = fields.Float(string='Elderly Tax Credit (USD)', default=75.0, help="Fixed tax credit for elderly employees.")
    hao_tax_credit_blind = fields.Float(string='Blind Tax Credit (USD)', default=75.0, help="Fixed tax credit for blind employees.")
    hao_tax_credit_disabled = fields.Float(string='Disabled Tax Credit (USD)', default=75.0, help="Fixed tax credit for disabled employees.")
