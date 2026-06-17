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
