from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ZimraTaxTable(models.Model):
    _name = 'zimra.tax.table'
    _description = 'ZIMRA Tax Table'
    _order = 'currency_id, frequency, min_income'

    name = fields.Char(
        string='Description',
        compute='_compute_name',
        store=True
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        help='Currency for this tax bracket (USD or ZWG)'
    )

    frequency = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('fortnightly', 'Fortnightly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ], string='Pay Frequency', required=True, default='monthly')

    min_income = fields.Monetary(
        string='Income From',
        required=True,
        currency_field='currency_id',
        help='Minimum taxable income for this bracket'
    )

    max_income = fields.Monetary(
        string='Income To',
        currency_field='currency_id',
        help='Maximum taxable income for this bracket. 0 = no upper limit'
    )

    rate = fields.Float(
        string='Tax Rate (%)',
        required=True,
        help='Tax rate percentage for this bracket (e.g., 25 for 25%)'
    )

    deduction = fields.Monetary(
        string='Deduction',
        currency_field='currency_id',
        default=0.0,
        help='Fixed deduction amount for this bracket'
    )

    effective_date = fields.Date(
        string='Effective Date',
        required=True,
        default=fields.Date.today,
        help='Date this tax bracket becomes effective'
    )

    active = fields.Boolean(
        string='Active',
        default=True
    )

    @api.depends('currency_id', 'frequency', 'min_income', 'max_income')
    def _compute_name(self):
        for record in self:
            currency = record.currency_id.name
            freq = dict(self._fields['frequency'].selection).get(record.frequency, '')
            if record.max_income > 0:
                record.name = f'{currency} {freq}: {record.min_income:,.2f} - {record.max_income:,.2f}'
            else:
                record.name = f'{currency} {freq}: {record.min_income:,.2f} and above'

    @api.constrains('min_income', 'max_income')
    def _check_brackets(self):
        for record in self:
            if record.max_income > 0 and record.min_income >= record.max_income:
                raise ValidationError('Minimum income must be less than maximum income!')

    @api.constrains('rate')
    def _check_rate(self):
        for record in self:
            if record.rate < 0 or record.rate > 100:
                raise ValidationError('Tax rate must be between 0 and 100!')

    def calculate_tax(self, income):
        """Calculate tax for a given income amount using this bracket"""
        self.ensure_one()
        if income <= 0:
            return 0.0
        tax = (income * self.rate / 100.0) - self.deduction
        return max(tax, 0.0)