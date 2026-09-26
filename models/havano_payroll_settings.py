from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # ==================== TAX CREDITS ====================
    hao_secondary_payroll_currency_id = fields.Many2one(
        related='company_id.hao_secondary_payroll_currency_id',
        readonly=False
    )
    hao_exchange_rate = fields.Float(
        related='company_id.hao_exchange_rate',
        readonly=False
    )
    payslip_format = fields.Selection(
        related='company_id.payslip_format',
        readonly=False
    )

    # ==================== FDS SETTINGS ====================
    tax_calculation_method = fields.Selection(
        related='company_id.tax_calculation_method',
        readonly=False
    )
    fds_method = fields.Selection(
        related='company_id.fds_method',
        readonly=False
    )

    # ==================== STATUTORY CONTRIBUTIONS ====================
    hao_zimdef_percentage = fields.Float(
        related='company_id.hao_zimdef_percentage',
        readonly=False
    )


    havano_tax_credit_blind = fields.Float(
        string='Blind Person Tax Credit Amount',
        config_parameter='havano_payroll.tax_credit_blind',
        default=75.00,
        help='Fixed tax credit for blind employees'
    )

    havano_tax_credit_elderly = fields.Float(
        string='Elderly (65+) Tax Credit Amount',
        config_parameter='havano_payroll.tax_credit_elderly',
        default=75.00,
        help='Fixed tax credit for employees 65 years and older'
    )

    havano_tax_credit_disabled = fields.Float(
        string='Disabled Person Tax Credit Amount',
        config_parameter='havano_payroll.tax_credit_disabled',
        default=75.00,
        help='Fixed tax credit for disabled employees'
    )
