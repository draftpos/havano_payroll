from odoo import models, fields, api

class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    active = fields.Boolean(string='Active', default=True)

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


class HrPayrollStructure(models.Model):
    _inherit = 'hr.payroll.structure'

    active = fields.Boolean(
        string='Active',
        default=True,
        help="If unchecked, it will allow you to hide the salary structure without deleting it or having it recreated on updates."
    )

    hao_rent_percentage = fields.Float(
        string='Rent Deduction (%)',
        default=5.0,
        prefetch=False,
        help="Percentage of Housing Allowance deducted for Rent."
    )

    def _register_hook(self):
        self.env.cr.execute("""
            ALTER TABLE hr_payroll_structure
            ADD COLUMN IF NOT EXISTS hao_rent_percentage double precision DEFAULT 5.0;
            UPDATE hr_payroll_structure
            SET hao_rent_percentage = 5.0
            WHERE hao_rent_percentage IS NULL;
        """)
        hou_rule = self.env['hr.salary.rule'].search([('code', '=', 'HOU')], limit=1)
        if hou_rule and 'hasattr' in (hou_rule.amount_python_compute or ''):
            hou_rule.amount_python_compute = """hou_amt = 0.0
version = payslip.version_id
if version:
    for split in version.hao_rule_split_ids:
        if split.salary_rule_id.code == 'HOU' or 'housing' in (split.salary_rule_id.name or '').lower():
            hou_amt += split.total_amount

if not hou_amt:
    for line in payslip.input_line_ids:
        c = (line.input_type_id.code or '').upper()
        n = (line.name or '').lower()
        tn = (line.input_type_id.name or '').lower()
        if c in ('HOU', 'HOUSING') or 'housing' in n or 'housing' in tn:
            hou_amt += line.amount

result = hou_amt"""

        rent_rule = self.env['hr.salary.rule'].search([('code', '=', 'RENT')], limit=1)
        if rent_rule and 'hasattr' in (rent_rule.amount_python_compute or ''):
            rent_rule.amount_python_compute = """struct = payslip.struct_id
rent_pct = struct.hao_rent_percentage if struct else 5.0

hou_amt = 0.0

if 'HOU' in result_rules:
    hou_amt = result_rules['HOU']['total']
elif 'HOUSING' in result_rules:
    hou_amt = result_rules['HOUSING']['total']
else:
    for r_code, r_val in result_rules.items():
        if 'HOU' in r_code.upper() and r_code.upper() not in ('RENT',):
            hou_amt = r_val['total']
            break

if not hou_amt:
    for line in payslip.line_ids:
        if line.category_id.code == 'ALW' and ('HOU' in line.code.upper() or 'HOUS' in (line.name or '').upper()):
            hou_amt = line.total
            break

if not hou_amt and payslip.version_id:
    for split in payslip.version_id.hao_rule_split_ids:
        if 'HOU' in (split.salary_rule_id.code or '').upper() or 'HOUS' in (split.salary_rule_id.name or '').upper():
            hou_amt = split.total_amount
            break

if not hou_amt:
    for inp in payslip.input_line_ids:
        code = (inp.input_type_id.code or '').upper()
        name = (inp.name or '').upper()
        type_name = (inp.input_type_id.name or '').upper()
        if 'HOU' in code or 'HOUS' in code or 'HOUS' in name or 'HOUS' in type_name:
            hou_amt = inp.amount
            break

if hou_amt and rent_pct:
    result = - abs(hou_amt * (rent_pct / 100.0))
else:
    result = 0.0"""
        return super()._register_hook()

    def _get_rules(self):
        """Ensure only active salary rules are evaluated during payslip/payrun calculations."""
        rules = super()._get_rules()
        return rules.filtered(lambda r: r.active)


