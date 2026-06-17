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
