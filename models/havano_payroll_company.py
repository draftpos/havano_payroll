from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    hao_allow_multi_payroll_currency = fields.Boolean(
        string='Allow Multi Currency Payroll',
        help='Enable this to allow a secondary currency for payroll calculations.'
    )
    hao_secondary_payroll_currency_id = fields.Many2one(
        'res.currency',
        string='Secondary Payroll Currency',
        help='Select the secondary currency to be used for dual-currency payrolls.'
    )
    hao_exchange_rate = fields.Float(
        string='Exchange Rate (Secondary to Base)',
        default=1.0,
        help='Fixed global exchange rate to convert secondary currency amounts to the base currency (e.g. ZWG to USD). Example: 34.0'
    )
    payslip_format = fields.Selection([
        ('standard', 'Standard'),
        ('modern', 'Modern'),
        ('landscape_3_per_page', 'Landscape 3 Per Page (Bellina / Fresh Company)')
    ], string="Payslip Format", default='standard')

    # ==================== FDS TAX CALCULATION ====================
    tax_calculation_method = fields.Selection([
        ('non_fds', 'Non-FDS (Standard Period-by-Period)'),
        ('fds', 'FDS (Final Deduction System)'),
    ], string='PAYE Calculation Method',
       default='non_fds',
       help='Choose how PAYE is calculated:\n'
            '- Non-FDS: Calculates PAYE based on this period\'s income only (standard method).\n'
            '- FDS: Calculates PAYE cumulatively over the tax year (January-December), '
            'ensuring the correct total tax is withheld by year-end as required by ZIMRA.')

    fds_method = fields.Selection([
        ('averaging', 'Averaging Method'),
        ('forecasting', 'Forecasting Method'),
    ], string='FDS Method',
       default='averaging',
       help='Choose the FDS formula to use:\n'
            '- Averaging: Averages earnings to date, annualizes, calculates annual tax, then finds this period\'s share.\n'
            '- Forecasting: Projects current earnings to year-end, calculates annual tax on forecast, spreads remaining tax over remaining periods.')

    hao_zimdef_percentage = fields.Float(
        string='ZIMDEF Percentage (%)',
        default=1.0,
        help='Percentage of gross salary for ZIMDEF contribution.'
    )

    hao_wcif_percentage = fields.Float(
        string='WCIF Percentage (%)',
        default=1.25,
        help='Percentage of basic salary for WCIF contribution.'
    )

    hao_leave_balance_from_joining_date = fields.Boolean(
        string='Update Leave Balance from Joining Date',
        default=False,
        help='If enabled, employee annual leave balances (2.5 days/month) are automatically calculated and updated from their Joining Date (Contract Start Date), and auto-update whenever the joining date is edited.'
    )

    def write(self, vals):
        res = super().write(vals)
        if vals.get('hao_leave_balance_from_joining_date'):
            for company in self:
                if company.hao_leave_balance_from_joining_date:
                    employees = self.env['hr.employee'].sudo().search([
                        ('company_id', '=', company.id),
                        ('active', '=', True),
                    ])
                    employees._sync_leave_allocation_from_joining_date()
        return res
