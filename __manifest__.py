{
    'name': 'Havano Payroll - Zimbabwe Localisation',
    'version': '1.6',
    'category': 'Payroll',
    'summary': 'Zimbabwe PAYE, NSSA, AIDS Levy, ZIMRA Tax Tables for Odoo Payroll',
    'description': """Havano Payroll - Comprehensive Zimbabwe Payroll Localisation for Odoo

The Havano Payroll module is a fully automated, multi-currency compliant payroll solution natively built for Zimbabwe. It seamlessly integrates into Odoo's core HR capabilities to handle the intricacies of ZIMRA tax brackets, statutory deductions, and multi-currency payslips.

Core Features & Automations:
- Advanced Multi-Currency: Dynamically compute and display primary (e.g. USD) and secondary (e.g. ZWG) currencies side-by-side using live exchange rates.
- Statutory Deductions: Automated calculation for NSSA, NEC, ZIMDEF, and LAPF including employer vs employee splits.
- ZIMRA Tax Tables: Pre-seeded and fully configurable daily, weekly, fortnightly, and monthly tax brackets.
- Intelligent PAYE & AIDS Levy: Automatically applies tax credits (Medical Aid, Blind, Elderly, Disabled) before calculating final PAYE, then accurately deduces the 3% AIDS Levy.
- Reporting Engine: Includes beautifully formatted, print-ready PDF reports and interactive pivot views for:
  * Salary Registry
  * Payroll Summary
  * NSSA P4 & NSSA Employer Reports
  * NEC Reports
- Employee Settings: Easily toggle tax credit eligibility (Disabled, Blind, 65+) directly on the employee profile.

This module eliminates the need for external spreadsheets, keeping your business 100% compliant with Zimbabwean labour laws right inside Odoo.""",
    'author': 'Havano',
    'website': 'https://www.havano.com',
    'depends': ['hr_payroll', 'hr', 'hr_holidays'],
    'data': [
        'data/report_paperformat_data.xml',
        'reports/report_payslip_templates.xml',
        'reports/report_payslip.xml',
        'security/ir.model.access.csv',
        'data/hr_leave_data.xml',
        'data/res_currency_data.xml',
        'data/salary_rule_categories.xml',
        'data/salary_rules.xml',
        'data/zimra_tax_table_data.xml',
        'views/payroll_settings_views.xml',
        'views/zimra_tax_table_views.xml',
        'views/res_company_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_contract_views.xml',
        'views/havano_ytd_views.xml',
        'views/hr_salary_rule_views.xml',
        'views/hr_payslip_views.xml',
        'wizard/havano_zim_report_wizard_views.xml',
        'reports/hr_payroll_zim_reports_views.xml',
        'reports/report_zim_statutory_views.xml',
        'reports/report_salary_registry_views.xml',
        'reports/report_zimra_p2.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}