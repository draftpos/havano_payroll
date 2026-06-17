from odoo import models, fields, api


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

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