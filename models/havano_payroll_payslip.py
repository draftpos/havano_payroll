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
    annual_leave_allocated = fields.Float(
        string='Annual Leave Allocated',
        compute='_compute_annual_leave_balance'
    )
    annual_leave_taken = fields.Float(
        string='Annual Leave Taken',
        compute='_compute_annual_leave_balance'
    )
    annual_leave_balance = fields.Float(
        string='Annual Leave Balance',
        compute='_compute_annual_leave_balance'
    )
    leave_allocation_id = fields.Many2one(
        'hr.leave.allocation',
        string='Leave Accrual Allocation',
        readonly=True,
        copy=False,
        help='The 2.5-day annual leave accrual allocation created upon confirmation of this payslip.'
    )

    def _compute_annual_leave_balance(self):
        leave_type = self.env.ref('havano_payroll.havano_annual_leave_type', raise_if_not_found=False)
        if not leave_type:
            leave_type = self.env['hr.leave.type'].sudo().search([('name', 'ilike', 'Annual Leave')], limit=1)
        for slip in self:
            allocated = 0.0
            taken = 0.0
            balance = 0.0
            if leave_type and slip.employee_id:
                allocations = self.env['hr.leave.allocation'].sudo().search([
                    ('employee_id', '=', slip.employee_id.id),
                    ('holiday_status_id', '=', leave_type.id),
                    ('state', '=', 'validate')
                ])
                allocated = sum(allocations.mapped('number_of_days'))
                leaves = self.env['hr.leave'].sudo().search([
                    ('employee_id', '=', slip.employee_id.id),
                    ('holiday_status_id', '=', leave_type.id),
                    ('state', '=', 'validate')
                ])
                taken = sum(leaves.mapped('number_of_days'))
                balance = allocated - taken
            slip.annual_leave_allocated = allocated
            slip.annual_leave_taken = taken
            slip.annual_leave_balance = balance

    def action_payslip_done(self):
        res = super().action_payslip_done()
        leave_type = self.env.ref('havano_payroll.havano_annual_leave_type', raise_if_not_found=False)
        if not leave_type:
            leave_type = self.env['hr.leave.type'].sudo().search([('name', 'ilike', 'Annual Leave')], limit=1)

        for slip in self:
            if not leave_type or not slip.employee_id:
                continue
            # Check if 2.5-day accrual allocation already exists for this payslip
            existing_alloc = slip.leave_allocation_id or self.env['hr.leave.allocation'].sudo().search([
                ('payslip_id', '=', slip.id),
            ], limit=1)
            
            if not existing_alloc:
                alloc = self.env['hr.leave.allocation'].sudo().create({
                    'name': f"Payroll Leave Accrual (2.5 days) - {slip.name}",
                    'employee_id': slip.employee_id.id,
                    'holiday_status_id': leave_type.id,
                    'number_of_days': 2.5,
                    'allocation_type': 'regular',
                    'date_from': slip.date_to or fields.Date.today(),
                    'payslip_id': slip.id,
                })
                try:
                    alloc._action_validate()
                except Exception:
                    try:
                        alloc.action_approve()
                    except Exception:
                        pass
                slip.leave_allocation_id = alloc.id
        return res

    def action_payslip_cancel(self):
        res = super().action_payslip_cancel()
        # Reverse the 2.5 days added for this payslip
        allocations = self.env['hr.leave.allocation'].sudo().search([
            '|',
            ('id', 'in', self.mapped('leave_allocation_id').ids),
            ('payslip_id', 'in', self.ids)
        ])
        if allocations:
            for alloc in allocations:
                try:
                    alloc.action_refuse()
                except Exception:
                    alloc.write({'state': 'refuse'})
            allocations.unlink()
        return res

    def action_payslip_draft(self):
        res = super().action_payslip_draft()
        # Cleanly remove the 2.5-day accrual if payslip is set back to draft
        allocations = self.env['hr.leave.allocation'].sudo().search([
            '|',
            ('id', 'in', self.mapped('leave_allocation_id').ids),
            ('payslip_id', 'in', self.ids)
        ])
        if allocations:
            for alloc in allocations:
                try:
                    alloc.action_refuse()
                except Exception:
                    alloc.write({'state': 'refuse'})
            allocations.unlink()
        return res

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

    def get_ytd_amount(self, code):
        """Return Year-To-Date total for a salary rule code for this employee.
        Includes all payslips from Jan 1 to the end of the current payslip period
        (including the current payslip itself, using its computed lines)."""
        self.ensure_one()
        if not self.date_to or not self.employee_id:
            return 0.0
        year_start = self.date_to.replace(month=1, day=1)

        # Sum from all CONFIRMED payslips this year EXCLUDING the current one
        lines = self.env['hr.payslip.line'].search([
            ('employee_id', '=', self.employee_id.id),
            ('slip_id.state', 'in', ['done', 'paid', 'validated']),
            ('slip_id.date_to', '>=', year_start),
            ('slip_id.date_to', '<=', self.date_to),
            ('slip_id', '!=', self.id),
            ('code', '=', code)
        ])
        ytd_historical = sum(lines.mapped('total'))

        # Add current payslip's computed value for this code
        current_line = self.line_ids.filtered(lambda l: l.code == code)
        current_val = sum(current_line.mapped('total')) if current_line else 0.0

        return ytd_historical + current_val

    # ==================== FDS HELPER METHODS ====================
    # These methods calculate cumulative Year-To-Date (YTD) totals required by the
    # FDS Averaging and Forecasting formulas. They sum:
    #   1. YTD Opening Balances from the employee's contract (for mid-year hires from a previous employer)
    #   2. All CONFIRMED payslips for this employee in the current calendar year, EXCLUDING the current payslip
    #      (so that the current slip can calculate what it still needs to deduct).

    def fds_get_ytd_taxable_income(self):
        """Return cumulative taxable income for the current employee in the current tax year,
        BEFORE the current payslip. Includes opening balance from previous employer (P6 data)."""
        self.ensure_one()
        if not self.date_to or not self.employee_id:
            return 0.0

        year_start = self.date_to.replace(month=1, day=1)

        # Sum GROSS - NSSA from all CONFIRMED previous payslips in this tax year
        prev_slips = self.env['hr.payslip'].search([
            ('employee_id', '=', self.employee_id.id),
            ('state', 'in', ['done', 'paid', 'validated']),
            ('date_to', '>=', year_start),
            ('date_to', '<', self.date_from),  # EXCLUDE current payslip period
            ('id', '!=', self.id),
        ])

        ytd_from_odoo = 0.0
        for slip in prev_slips:
            gross = sum(l.total for l in slip.line_ids if l.code == 'GROSS')
            nssa = sum(abs(l.total) for l in slip.line_ids if l.code == 'NSSA')
            ytd_from_odoo += max(gross - nssa, 0.0)

        # Add opening balance from previous employer (P6 form data on the contract)
        opening_balance = 0.0
        if self.version_id and hasattr(self.version_id, 'ytd_opening_taxable_income'):
            opening_balance = self.version_id.ytd_opening_taxable_income or 0.0

        return opening_balance + ytd_from_odoo

    def fds_get_ytd_paye_paid(self):
        """Return cumulative PAYE paid for the current employee in the current tax year,
        BEFORE the current payslip. Includes opening balance from previous employer (P6 data)."""
        self.ensure_one()
        if not self.date_to or not self.employee_id:
            return 0.0

        year_start = self.date_to.replace(month=1, day=1)

        prev_slips = self.env['hr.payslip'].search([
            ('employee_id', '=', self.employee_id.id),
            ('state', 'in', ['done', 'paid', 'validated']),
            ('date_to', '>=', year_start),
            ('date_to', '<', self.date_from),
            ('id', '!=', self.id),
        ])

        ytd_paye_from_odoo = sum(
            abs(l.total)
            for slip in prev_slips
            for l in slip.line_ids
            if l.code == 'PAYE'
        )

        opening_paye = 0.0
        if self.version_id and hasattr(self.version_id, 'ytd_opening_paye_paid'):
            opening_paye = self.version_id.ytd_opening_paye_paid or 0.0

        return opening_paye + ytd_paye_from_odoo

    def fds_get_months_worked_in_year(self):
        """Return total number of months worked in the current tax year UP TO AND INCLUDING
        the current payslip's month. Includes months from previous employer (P6 data)."""
        self.ensure_one()
        if not self.date_to or not self.employee_id:
            return 1

        year_start = self.date_to.replace(month=1, day=1)

        # Count distinct months from confirmed payslips in Odoo (including current month)
        all_slips_this_year = self.env['hr.payslip'].search([
            ('employee_id', '=', self.employee_id.id),
            ('state', 'in', ['done', 'paid', 'validated', 'verify', 'draft']),
            ('date_to', '>=', year_start),
            ('date_to', '<=', self.date_to),
        ])
        odoo_months = len(set(s.date_to.month for s in all_slips_this_year if s.date_to))
        # Ensure at least 1 for the current month
        odoo_months = max(odoo_months, 1)

        opening_months = 0
        if self.version_id and hasattr(self.version_id, 'ytd_opening_months_worked'):
            opening_months = self.version_id.ytd_opening_months_worked or 0

        return opening_months + odoo_months



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
            
            # Check single vs dual currency setting
            payment_setup = getattr(slip.version_id, 'hao_currency_payment_setup', False) or getattr(slip.employee_id, 'hao_currency_payment_setup', 'single')
            if payment_setup == 'single':
                # Employee is Single Currency: zero out secondary ledger
                for line in slip.line_ids:
                    line.hao_secondary_amount = 0.0
                    line.hao_secondary_total = 0.0
                    line.hao_is_manual_secondary = True
                continue

            rule_splits = {s.salary_rule_id.id: s for s in (slip.version_id.hao_rule_split_ids if slip.version_id else [])}

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
                    line.amount = 0.0
                    line.total = 0.0
                    
                if is_base_only and line.hao_secondary_total != 0.0:
                    line.hao_secondary_amount = 0.0
                    line.hao_secondary_total = 0.0
                    
                if not is_secondary_only and not is_base_only:
                    if line.salary_rule_id.code in ('GROSS', 'NET'):
                        continue

                    # 1. Custom Rule Split for this specific employee / allowance
                    if line.salary_rule_id.id in rule_splits:
                        rule_split = rule_splits[line.salary_rule_id.id]
                        tot = rule_split.total_amount or line.total or line.amount or 0.0
                        exchange_rate = slip.company_id.hao_exchange_rate or 1.0

                        if rule_split.split_method == 'exact':
                            prim = rule_split.primary_amount or 0.0
                            sec = rule_split.secondary_amount or round(max(tot - prim, 0.0) * exchange_rate, 2)
                        else:
                            prim_pct = (rule_split.primary_percentage or 80.0) / 100.0
                            sec_pct = (rule_split.secondary_percentage or 20.0) / 100.0
                            prim = round(tot * prim_pct, 2)
                            sec = round(tot * sec_pct * exchange_rate, 2)

                        line.amount = prim
                        line.total = prim
                        line.hao_secondary_amount = sec
                        line.hao_secondary_total = sec
                        line.hao_is_manual_secondary = True
                        continue

                    exchange_rate = slip.company_id.hao_exchange_rate or 1.0
                    total_wage = slip.version_id.contract_wage or slip.basic_wage or 0.0
                    prim_amt = getattr(slip.version_id, 'hao_primary_amount', 0.0) or getattr(slip.employee_id, 'hao_primary_amount', 0.0)
                    sec_amt = getattr(slip.version_id, 'hao_secondary_amount', 0.0) or getattr(slip.employee_id, 'hao_secondary_amount', 0.0) or getattr(slip.employee_id, 'hao_secondary_wage', 0.0)
                    alloc_method = getattr(slip.version_id, 'hao_dual_currency_method', False) or getattr(slip.employee_id, 'hao_dual_currency_method', 'exact')

                    if alloc_method == 'exact':
                        if total_wage > 0 and prim_amt > 0:
                            prim_pct = prim_amt / total_wage
                            sec_pct = max(1.0 - prim_pct, 0.0)
                            if not sec_amt and sec_pct > 0:
                                sec_amt = round((total_wage - prim_amt) * exchange_rate, 2)
                        elif total_wage > 0 and sec_amt > 0 and exchange_rate > 0:
                            sec_in_base = sec_amt / exchange_rate
                            prim_amt = max(total_wage - sec_in_base, 0.0)
                            prim_pct = prim_amt / total_wage
                            sec_pct = max(1.0 - prim_pct, 0.0)
                        else:
                            prim_pct = 0.5
                            sec_pct = 0.5
                            prim_amt = round(total_wage * 0.5, 2)
                            sec_amt = round(total_wage * 0.5 * exchange_rate, 2)
                    else:
                        sec_pct_val = getattr(slip.version_id, 'hao_secondary_percentage', 0.0) or getattr(slip.employee_id, 'hao_secondary_percentage', 0.0) or getattr(slip.version_id, 'hao_secondary_wage_percentage', 50.0)
                        sec_pct = sec_pct_val / 100.0
                        prim_pct = max(1.0 - sec_pct, 0.0)
                        prim_amt = round(total_wage * prim_pct, 2)
                        sec_amt = round(total_wage * sec_pct * exchange_rate, 2)

                    if line.salary_rule_id.code == 'BASIC':
                        line.amount = prim_amt
                        line.total = prim_amt
                        line.hao_secondary_amount = sec_amt
                        line.hao_secondary_total = sec_amt
                        line.hao_is_manual_secondary = True
                    else:
                        orig_tot = line.total
                        orig_amt = line.amount
                        line.amount = round(orig_amt * prim_pct, 2)
                        line.total = round(orig_tot * prim_pct, 2)
                        line.hao_secondary_amount = round(orig_amt * sec_pct * exchange_rate, 2)
                        line.hao_secondary_total = round(orig_tot * sec_pct * exchange_rate, 2)
                        line.hao_is_manual_secondary = True

            # Recalculate GROSS
            gross_line = slip.line_ids.filtered(lambda l: l.code == 'GROSS')
            if gross_line:
                gross_base = sum(l.total for l in slip.line_ids if l.category_id.code in ('BASIC', 'ALW') and l.code not in ('GROSS', 'NET'))
                gross_line.amount = gross_base
                gross_line.total = gross_base
                gross_sec = sum(l.hao_secondary_total for l in slip.line_ids if l.category_id.code in ('BASIC', 'ALW') and l.code not in ('GROSS', 'NET'))
                gross_line.hao_secondary_amount = gross_sec
                gross_line.hao_secondary_total = gross_sec
                gross_line.hao_is_manual_secondary = True

            # Recalculate NET
            net_line = slip.line_ids.filtered(lambda l: l.code == 'NET')
            if net_line:
                net_base = sum(l.total for l in slip.line_ids if l.category_id.code in ('BASIC', 'ALW', 'DED') and l.code != 'NET')
                net_line.amount = net_base
                net_line.total = net_base
                net_sec = sum(l.hao_secondary_total for l in slip.line_ids if l.category_id.code in ('BASIC', 'ALW', 'DED') and l.code != 'NET')
                net_line.hao_secondary_amount = net_sec
                net_line.hao_secondary_total = net_sec
                net_line.hao_is_manual_secondary = True

        return res

class HrPayrollEditPayslipLinesWizard(models.TransientModel):
    _inherit = 'hr.payroll.edit.payslip.lines.wizard'

    hao_allow_multi_payroll_currency = fields.Boolean(
        related='payslip_id.company_id.hao_allow_multi_payroll_currency'
    )

    def action_validate_edition(self):
        res = super().action_validate_edition()
        for wizard in self:
            if wizard.payslip_id:
                slip = wizard.payslip_id
                net_line = slip.line_ids.filtered(lambda l: l.code == 'NET')
                if net_line:
                    net_sec = sum(l.hao_secondary_total for l in slip.line_ids if l.category_id.code in ('BASIC', 'ALW', 'DED') and l.code != 'NET')
                    net_line.hao_secondary_amount = net_sec
                    net_line.hao_secondary_total = net_sec
        return res

class HrPayrollEditPayslipLine(models.TransientModel):
    _inherit = 'hr.payroll.edit.payslip.line'

    currency_id = fields.Many2one('res.currency', related='slip_id.company_id.currency_id')
    hao_secondary_amount = fields.Monetary(
        string='Amount (ZWG)',
        currency_field='hao_secondary_currency_id'
    )
    hao_secondary_total = fields.Monetary(
        string='Total (ZWG)',
        compute='_compute_hao_secondary_total',
        store=True,
        readonly=False,
        currency_field='hao_secondary_currency_id'
    )

    @api.depends('quantity', 'hao_secondary_amount', 'rate')
    def _compute_hao_secondary_total(self):
        for line in self:
            line.hao_secondary_total = float(line.quantity) * line.hao_secondary_amount * line.rate / 100
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

                    mode = getattr(version, 'hao_dual_currency_mode', 'fixed')
                    date = line.slip_id.date_to or fields.Date.today()
                    company_rate = line.slip_id.company_id.hao_exchange_rate or 0.0

                    def _conv(val):
                        if company_rate > 0:
                            return round(val * company_rate, 2)
                        return company_currency._convert(val, secondary_currency, line.slip_id.company_id, date) if (company_currency and secondary_currency) else val
                    
                    if mode == 'percentage':
                        pct = getattr(version, 'hao_secondary_wage_percentage', 50.0) / 100.0
                        converted_total = _conv(line.total)
                        converted_amount = _conv(line.amount)
                        line.hao_secondary_total = converted_total * pct
                        line.hao_secondary_amount = converted_amount * pct
                    elif mode == 'full_conversion':
                        line.hao_secondary_total = _conv(line.total)
                        line.hao_secondary_amount = _conv(line.amount)
                    else:
                        # Fixed mode (Scenario 1)
                        if hasattr(version, 'contract_wage') and version.contract_wage and employee.hao_secondary_wage:
                            effective_rate = employee.hao_secondary_wage / version.contract_wage
                            line.hao_secondary_total = line.total * effective_rate
                            line.hao_secondary_amount = line.amount * effective_rate
                        else:
                            line.hao_secondary_total = _conv(line.total)
                            line.hao_secondary_amount = _conv(line.amount)
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


class HrLeaveAllocation(models.Model):
    _inherit = 'hr.leave.allocation'

    payslip_id = fields.Many2one(
        'hr.payslip',
        string='Source Payslip',
        index=True,
        readonly=True,
        copy=False,
        ondelete='cascade',
        help='The payslip whose monthly payroll run generated this leave accrual.'
    )

