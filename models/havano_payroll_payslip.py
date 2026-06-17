from odoo import models, fields, api

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    hao_allow_multi_payroll_currency = fields.Boolean(
        related='company_id.hao_allow_multi_payroll_currency'
    )
    hao_secondary_payroll_currency_id = fields.Many2one(
        'res.currency',
        related='company_id.hao_secondary_payroll_currency_id'
    )
    hao_has_secondary_wage = fields.Boolean(
        compute='_compute_hao_has_secondary_wage'
    )

    @api.depends('version_id')
    def _compute_struct_id(self):
        super()._compute_struct_id()
        for slip in self:
            # Force Odoo to respect the explicit Salary Structure chosen on the contract/employee
            if slip.version_id and hasattr(slip.version_id, 'structure_id') and slip.version_id.structure_id:
                slip.struct_id = slip.version_id.structure_id
            elif slip.employee_id and hasattr(slip.employee_id, 'hao_contract_structure_id') and slip.employee_id.hao_contract_structure_id:
                slip.struct_id = slip.employee_id.hao_contract_structure_id
    hao_secondary_employer_cost = fields.Monetary(
        string='Employer Cost (Secondary)',
        compute='_compute_hao_secondary_wages',
        currency_field='hao_secondary_payroll_currency_id'
    )
    hao_secondary_basic_wage = fields.Monetary(
        string='Basic Wage (Secondary)',
        compute='_compute_hao_secondary_wages',
        currency_field='hao_secondary_payroll_currency_id'
    )
    hao_secondary_gross_wage = fields.Monetary(
        string='Gross Wage (Secondary)',
        compute='_compute_hao_secondary_wages',
        currency_field='hao_secondary_payroll_currency_id'
    )
    hao_secondary_net_wage = fields.Monetary(
        string='Net Wage (Secondary)',
        compute='_compute_hao_secondary_wages',
        currency_field='hao_secondary_payroll_currency_id'
    )
    annual_leave_balance = fields.Float(
        string='Annual Leave Balance',
        compute='_compute_annual_leave_balance'
    )

    def _compute_annual_leave_balance(self):
        leave_type = self.env.ref('havano_payroll.havano_annual_leave_type', raise_if_not_found=False)
        for slip in self:
            balance = 0.0
            if leave_type and slip.employee_id:
                allocations = self.env['hr.leave.allocation'].search([
                    ('employee_id', '=', slip.employee_id.id),
                    ('holiday_status_id', '=', leave_type.id),
                    ('state', '=', 'validate')
                ])
                allocated = sum(allocations.mapped('number_of_days'))
                leaves = self.env['hr.leave'].search([
                    ('employee_id', '=', slip.employee_id.id),
                    ('holiday_status_id', '=', leave_type.id),
                    ('state', '=', 'validate')
                ])
                taken = sum(leaves.mapped('number_of_days'))
                balance = allocated - taken
            slip.annual_leave_balance = balance

    @api.depends('line_ids.hao_secondary_total', 'line_ids.salary_rule_id.appears_on_employee_cost_dashboard')
    def _compute_hao_secondary_wages(self):
        for slip in self:
            slip.hao_secondary_employer_cost = sum(
                line.hao_secondary_total 
                for line in slip.line_ids 
                if getattr(line.salary_rule_id, 'appears_on_employee_cost_dashboard', False)
            )
            
            def _get_sec_line_value(code):
                lines = slip.line_ids.filtered(lambda l: l.code == code)
                return sum(lines.mapped('hao_secondary_total'))
                
            slip.hao_secondary_basic_wage = _get_sec_line_value('BASIC')
            slip.hao_secondary_gross_wage = _get_sec_line_value('GROSS')
            slip.hao_secondary_net_wage = _get_sec_line_value('NET')

    @api.depends('employee_id.hao_secondary_wage')
    def _compute_hao_has_secondary_wage(self):
        for slip in self:
            slip.hao_has_secondary_wage = bool(slip.employee_id and slip.employee_id.hao_secondary_wage > 0)

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        res = super().get_view(view_id, view_type, **options)
        
        # Only rewrite headers if we're in a form view or list view
        if view_type in ('form', 'list', 'tree') and 'arch' in res:
            company = self.env.company
            if company.hao_allow_multi_payroll_currency:
                base_curr = company.currency_id.name or 'USD'
                sec_curr = company.hao_secondary_payroll_currency_id.name or 'Secondary'
                
                import xml.etree.ElementTree as ET
                try:
                    # Parse the string arch into an ElementTree
                    root = ET.fromstring(res['arch'])
                    modified = False
                    
                    # Find all fields named 'amount'
                    for node in root.findall(".//field[@name='amount']"):
                        if node.get('string') == 'Amount (USD)':
                            node.set('string', f'Amount ({base_curr})')
                            modified = True
                            
                    # Find all fields named 'total'
                    for node in root.findall(".//field[@name='total']"):
                        if node.get('string') == 'Total (USD)':
                            node.set('string', f'Total ({base_curr})')
                            modified = True
                            
                    # Find all secondary amount fields
                    for node in root.findall(".//field[@name='hao_secondary_amount']"):
                        if node.get('string') == 'Amount (ZWG)':
                            node.set('string', f'Amount ({sec_curr})')
                            modified = True
                            
                    # Find all secondary total fields
                    for node in root.findall(".//field[@name='hao_secondary_total']"):
                        if node.get('string') == 'Total (ZWG)':
                            node.set('string', f'Total ({sec_curr})')
                            modified = True
                            
                    # Find list view secondary wages
                    for node in root.findall(".//field[@name='hao_secondary_employer_cost']"):
                        if node.get('string') == 'Employer Cost (ZWG)':
                            node.set('string', f'Employer Cost ({sec_curr})')
                            modified = True
                    for node in root.findall(".//field[@name='hao_secondary_basic_wage']"):
                        if node.get('string') == 'Basic Wage (ZWG)':
                            node.set('string', f'Basic Wage ({sec_curr})')
                            modified = True
                    for node in root.findall(".//field[@name='hao_secondary_gross_wage']"):
                        if node.get('string') == 'Gross Wage (ZWG)':
                            node.set('string', f'Gross Wage ({sec_curr})')
                            modified = True
                    for node in root.findall(".//field[@name='hao_secondary_net_wage']"):
                        if node.get('string') == 'Net Wage (ZWG)':
                            node.set('string', f'Net Wage ({sec_curr})')
                            modified = True

                    if modified:
                        res['arch'] = ET.tostring(root, encoding='unicode')
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning("Failed to parse view arch: %s", e)
            else:
                import xml.etree.ElementTree as ET
                try:
                    root = ET.fromstring(res['arch'])
                    modified = False
                    # Physically remove secondary fields entirely if multi-currency is off
                    fields_to_remove = {'hao_secondary_employer_cost', 'hao_secondary_basic_wage', 'hao_secondary_gross_wage', 'hao_secondary_net_wage', 'hao_secondary_amount', 'hao_secondary_total'}
                    for parent in root.iter():
                        for child in list(parent):
                            if child.tag == 'field' and child.get('name') in fields_to_remove:
                                parent.remove(child)
                                modified = True
                    if modified:
                        res['arch'] = ET.tostring(root, encoding='unicode')
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning("Failed to parse view arch: %s", e)
                    
        return res

    def compute_sheet(self):
        res = super(HrPayslip, self).compute_sheet()
        for slip in self:
            company_currency = slip.company_id.currency_id
            secondary_currency = slip.company_id.hao_secondary_payroll_currency_id
            allow_multi = slip.company_id.hao_allow_multi_payroll_currency
            
            for line in slip.line_ids:
                if not allow_multi:
                    # If multi currency is off, everything computes normally on the USD base ledger!
                    continue

                is_secondary_only = getattr(line.salary_rule_id, 'hao_currency_application', 'both') == 'secondary_only'
                is_base_only = getattr(line.salary_rule_id, 'hao_currency_application', 'both') == 'base_only'
                
                if line.salary_rule_id.code in ('FUNERAL', 'FUNERAL_COMP'):
                    policy_currency = getattr(slip.version_id, 'hao_funeral_policy_currency_id', False)
                    if policy_currency == secondary_currency:
                        is_secondary_only = True
                    elif policy_currency == company_currency:
                        is_base_only = True

                if line.salary_rule_id.code in ('MEDAID', 'MEDAID_COMP'):
                    policy_currency = getattr(slip.version_id, 'hao_medical_aid_currency_id', False)
                    if policy_currency == secondary_currency:
                        is_secondary_only = True
                    elif policy_currency == company_currency:
                        is_base_only = True

                if is_secondary_only and line.total != 0.0:
                    # By writing 0.0, we explicitly erase the USD total from the ledger.
                    # _compute_hao_secondary_total will see this and intentionally preserve its pre-calculated ZWG amount.
                    line.amount = 0.0
                    line.total = 0.0
                    
                if is_base_only and line.hao_secondary_total != 0.0:
                    line.hao_secondary_amount = 0.0
                    line.hao_secondary_total = 0.0

            # Third pass: recalculate NET
            net_line = slip.line_ids.filtered(lambda l: l.code == 'NET')
            if net_line:
                # Base NET
                net_base = sum(l.total for l in slip.line_ids if l.category_id.code in ('BASIC', 'ALW', 'DED') and l.code != 'NET')
                net_line.amount = net_base
                net_line.total = net_base
                
                # Secondary NET
                net_sec = sum(l.hao_secondary_total for l in slip.line_ids if l.category_id.code in ('BASIC', 'ALW', 'DED') and l.code != 'NET')
                net_line.hao_secondary_amount = net_sec
                net_line.hao_secondary_total = net_sec

        return res

class HrPayrollEditPayslipLinesWizard(models.TransientModel):
    _inherit = 'hr.payroll.edit.payslip.lines.wizard'

    hao_allow_multi_payroll_currency = fields.Boolean(
        related='payslip_id.company_id.hao_allow_multi_payroll_currency'
    )

class HrPayrollEditPayslipLine(models.TransientModel):
    _inherit = 'hr.payroll.edit.payslip.line'

    currency_id = fields.Many2one('res.currency', related='slip_id.company_id.currency_id')
    hao_secondary_amount = fields.Monetary(
        string='Amount (ZWG)',
        currency_field='hao_secondary_currency_id'
    )
    hao_secondary_total = fields.Monetary(
        string='Total (ZWG)',
        currency_field='hao_secondary_currency_id'
    )
    hao_is_manual_secondary = fields.Boolean()
    hao_secondary_currency_id = fields.Many2one(
        'res.currency',
        related='slip_id.company_id.hao_secondary_payroll_currency_id'
    )
    hao_allow_multi_payroll_currency = fields.Boolean(
        related='slip_id.company_id.hao_allow_multi_payroll_currency'
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'hao_secondary_amount' not in vals and 'slip_id' in vals and 'salary_rule_id' in vals:
                payslip_line = self.env['hr.payslip.line'].search([
                    ('slip_id', '=', vals['slip_id']),
                    ('salary_rule_id', '=', vals['salary_rule_id'])
                ], limit=1)
                if payslip_line:
                    vals['hao_secondary_amount'] = payslip_line.hao_secondary_amount
                    vals['hao_secondary_total'] = payslip_line.hao_secondary_total
                    vals['hao_is_manual_secondary'] = payslip_line.hao_is_manual_secondary
        return super().create(vals_list)

    def _export_to_payslip_line(self):
        res = super()._export_to_payslip_line()
        for i, line in enumerate(self):
            res[i]['hao_secondary_amount'] = line.hao_secondary_amount
            res[i]['hao_secondary_total'] = line.hao_secondary_total
            res[i]['hao_is_manual_secondary'] = True
        return res

class HrPayslipLine(models.Model):
    _inherit = 'hr.payslip.line'

    hao_is_manual_secondary = fields.Boolean()
    hao_secondary_amount = fields.Monetary(
        string='Amount (Secondary)',
        compute='_compute_hao_secondary_total',
        store=True,
        readonly=False,
        currency_field='hao_secondary_currency_id'
    )
    hao_secondary_total = fields.Monetary(
        string='Total (Secondary)',
        compute='_compute_hao_secondary_total',
        store=True,
        readonly=False,
        currency_field='hao_secondary_currency_id'
    )
    hao_secondary_currency_id = fields.Many2one(
        'res.currency',
        related='slip_id.company_id.hao_secondary_payroll_currency_id'
    )
    
    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super().fields_get(allfields, attributes)
        company = self.env.company
        if company.hao_allow_multi_payroll_currency:
            base_curr = company.currency_id.name or 'USD'
            sec_curr = company.hao_secondary_payroll_currency_id.name or 'Secondary'
            if 'total' in res:
                res['total']['string'] = f'Total ({base_curr})'
            if 'hao_secondary_total' in res:
                res['hao_secondary_total']['string'] = f'Total ({sec_curr})'
        return res
    hao_allow_multi_payroll_currency = fields.Boolean(
        related='slip_id.company_id.hao_allow_multi_payroll_currency'
    )

    @api.depends('total', 'amount', 'salary_rule_id.hao_secondary_fixed_amount', 'salary_rule_id.amount_select', 'slip_id.company_id.hao_allow_multi_payroll_currency')
    def _compute_hao_secondary_total(self):
        for line in self:
            if line.hao_is_manual_secondary:
                continue
            if not line.hao_allow_multi_payroll_currency or not line.hao_secondary_currency_id:
                line.hao_secondary_total = 0.0
                line.hao_secondary_amount = 0.0
                continue
                
            # If it's a fixed amount rule, use the explicit secondary amount
            if line.salary_rule_id.amount_select == 'fix' and line.salary_rule_id.hao_secondary_fixed_amount:
                # Also apply quantity and rate if applicable
                line.hao_secondary_total = line.salary_rule_id.hao_secondary_fixed_amount * line.quantity * (line.rate / 100.0)
                line.hao_secondary_amount = line.salary_rule_id.hao_secondary_fixed_amount
            else:
                # Automatic conversion based on live exchange rate
                company_currency = line.slip_id.company_id.currency_id
                secondary_currency = line.hao_secondary_currency_id
                
                if company_currency and secondary_currency and company_currency != secondary_currency:
                    is_secondary_only = getattr(line.salary_rule_id, 'hao_currency_application', 'both') == 'secondary_only'
                    is_base_only = getattr(line.salary_rule_id, 'hao_currency_application', 'both') == 'base_only'

                    if line.salary_rule_id.code in ('FUNERAL', 'FUNERAL_COMP'):
                        policy_currency = getattr(line.slip_id.version_id, 'hao_funeral_policy_currency_id', False)
                        if policy_currency == secondary_currency:
                            is_secondary_only = True
                        elif policy_currency == company_currency:
                            is_base_only = True
                            
                    if line.salary_rule_id.code in ('MEDAID', 'MEDAID_COMP'):
                        policy_currency = getattr(line.slip_id.version_id, 'hao_medical_aid_currency_id', False)
                        if policy_currency == secondary_currency:
                            is_secondary_only = True
                        elif policy_currency == company_currency:
                            is_base_only = True

                    if is_base_only:
                        line.hao_secondary_amount = 0.0
                        line.hao_secondary_total = 0.0
                        continue

                    if is_secondary_only and line.total == 0.0 and line.hao_secondary_total != 0.0:
                        # compute_sheet zeroes out the base total for secondary_only rules.
                        # Preserve the already calculated secondary total!
                        continue

                    # Independent NET Calculation is handled in compute_sheet override!
                    if line.salary_rule_id.code == 'NET':
                        continue

                    # Calculate effective rate based on employee's explicit secondary wage if set
                    version = line.slip_id.version_id
                    employee = line.slip_id.employee_id
                    rule = line.salary_rule_id
                    secondary_currency = line.hao_secondary_currency_id
                    if rule.code in ('FUNERAL', 'FUNERAL_COMP') and hasattr(version, 'hao_funeral_policy_amount') and version.hao_funeral_policy_amount:
                        if hasattr(version, 'hao_funeral_policy_currency_id') and version.hao_funeral_policy_currency_id == secondary_currency:
                            base_zwg = version.hao_funeral_policy_amount
                            is_comp = (rule.code == 'FUNERAL_COMP')
                            base_rule = line.slip_id.env['hr.salary.rule'].search([('code', '=', 'FUNERAL')], limit=1) if is_comp else rule
                            mode = base_rule.hao_policy_payment_mode if base_rule else 'employee'
                            
                            if is_comp:
                                amt = base_zwg if mode == 'employer' else (base_zwg * (base_rule.hao_policy_comp_pct / 100.0) if mode == 'shared' else 0.0)
                            else:
                                amt = base_zwg if mode == 'employee' else (base_zwg * (base_rule.hao_policy_emp_pct / 100.0) if mode == 'shared' else 0.0)
                            
                            line.hao_secondary_amount = amt
                            line.hao_secondary_total = -amt if rule.category_id.code == 'DED' else amt
                            continue
                        
                    if rule.code in ('MEDAID', 'MEDAID_COMP') and hasattr(version, 'hao_medical_aid_amount') and version.hao_medical_aid_amount:
                        if hasattr(version, 'hao_medical_aid_currency_id') and version.hao_medical_aid_currency_id == secondary_currency:
                            base_zwg = version.hao_medical_aid_amount
                            is_comp = (rule.code == 'MEDAID_COMP')
                            base_rule = line.slip_id.env['hr.salary.rule'].search([('code', '=', 'MEDAID')], limit=1) if is_comp else rule
                            mode = base_rule.hao_policy_payment_mode if base_rule else 'employee'
                            
                            if is_comp:
                                amt = base_zwg if mode == 'employer' else (base_zwg * (base_rule.hao_policy_comp_pct / 100.0) if mode == 'shared' else 0.0)
                            else:
                                amt = base_zwg if mode == 'employee' else (base_zwg * (base_rule.hao_policy_emp_pct / 100.0) if mode == 'shared' else 0.0)
                            
                            line.hao_secondary_amount = amt
                            line.hao_secondary_total = -amt if rule.category_id.code == 'DED' else amt
                            continue

                    if hasattr(version, 'contract_wage') and version.contract_wage and employee.hao_secondary_wage:
                        effective_rate = employee.hao_secondary_wage / version.contract_wage
                        line.hao_secondary_total = line.total * effective_rate
                        line.hao_secondary_amount = line.amount * effective_rate
                    else:
                        # Use today's rate (or payslip date if you prefer)
                        date = line.slip_id.date_to or fields.Date.today()
                        line.hao_secondary_total = company_currency._convert(
                            line.total,
                            secondary_currency,
                            line.slip_id.company_id,
                            date
                        )
                        line.hao_secondary_amount = company_currency._convert(
                            line.amount,
                            secondary_currency,
                            line.slip_id.company_id,
                            date
                        )
                else:
                    line.hao_secondary_total = line.total
                    line.hao_secondary_amount = line.amount

class HrPayslipWorkedDays(models.Model):
    _inherit = 'hr.payslip.worked_days'

    hao_is_manual_secondary = fields.Boolean()
    hao_secondary_amount = fields.Monetary(
        string='Amount (Secondary)',
        compute='_compute_hao_secondary_amount',
        store=True,
        readonly=False,
        currency_field='hao_secondary_currency_id'
    )
    hao_secondary_currency_id = fields.Many2one(
        'res.currency',
        related='payslip_id.company_id.hao_secondary_payroll_currency_id'
    )
    hao_allow_multi_payroll_currency = fields.Boolean(
        related='payslip_id.company_id.hao_allow_multi_payroll_currency'
    )

    @api.depends('amount', 'payslip_id.company_id.hao_allow_multi_payroll_currency')
    def _compute_hao_secondary_amount(self):
        for line in self:
            if line.hao_is_manual_secondary:
                continue
            if not line.hao_allow_multi_payroll_currency or not line.hao_secondary_currency_id:
                line.hao_secondary_amount = 0.0
                continue
                
            company_currency = line.payslip_id.company_id.currency_id
            secondary_currency = line.hao_secondary_currency_id
            
            if company_currency and secondary_currency and company_currency != secondary_currency:
                version = line.payslip_id.version_id
                employee = line.payslip_id.employee_id
                if hasattr(version, 'contract_wage') and version.contract_wage and employee.hao_secondary_wage:
                    effective_rate = employee.hao_secondary_wage / version.contract_wage
                    line.hao_secondary_amount = line.amount * effective_rate
                else:
                    date = line.payslip_id.date_to or fields.Date.today()
                    line.hao_secondary_amount = company_currency._convert(
                        line.amount,
                        secondary_currency,
                        line.payslip_id.company_id,
                        date
                    )
            else:
                line.hao_secondary_amount = line.amount

class HrPayrollEditPayslipWorkedDaysLine(models.TransientModel):
    _inherit = 'hr.payroll.edit.payslip.worked.days.line'

    currency_id = fields.Many2one('res.currency', related='slip_id.company_id.currency_id')
    hao_secondary_amount = fields.Monetary(
        string='Amount (ZWG)',
        currency_field='hao_secondary_currency_id'
    )
    hao_is_manual_secondary = fields.Boolean()
    hao_secondary_currency_id = fields.Many2one(
        'res.currency',
        related='slip_id.company_id.hao_secondary_payroll_currency_id'
    )
    hao_allow_multi_payroll_currency = fields.Boolean(
        related='slip_id.company_id.hao_allow_multi_payroll_currency'
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'hao_secondary_amount' not in vals and 'slip_id' in vals and 'code' in vals:
                wd_line = self.env['hr.payslip.worked_days'].search([
                    ('payslip_id', '=', vals['slip_id']),
                    ('code', '=', vals['code'])
                ], limit=1)
                if wd_line:
                    vals['hao_secondary_amount'] = wd_line.hao_secondary_amount
                    vals['hao_is_manual_secondary'] = wd_line.hao_is_manual_secondary
        return super().create(vals_list)

    def _export_to_worked_days_line(self):
        res = super()._export_to_worked_days_line()
        for i, line in enumerate(self):
            res[i]['hao_secondary_amount'] = line.hao_secondary_amount
            res[i]['hao_is_manual_secondary'] = True
        return res
