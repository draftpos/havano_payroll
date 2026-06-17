odoo.define('havano_payroll.salary_tables', function (require) {
    "use strict";
    
    var core = require('web.core');
    var ListRenderer = require('web.ListRenderer');
    
    var _t = core._t;
    
    ListRenderer.include({
        _renderBody: function () {
            var $result = this._super.apply(this, arguments);
            
            // Add real-time total calculation
            if (this.state.model === 'hr.employee') {
                this._updateTotals();
            }
            
            return $result;
        },
        
        _updateTotals: function () {
            var self = this;
            var earningsTotal = 0;
            var deductionsTotal = 0;
            
            this.$('.o_list_table tbody tr').each(function () {
                var $row = $(this);
                var amount = parseFloat($row.find('[data-field="amount"] input').val() || 0);
                var type = $row.find('[data-field="component_type"]').text();
                
                if (type === 'earning') {
                    earningsTotal += amount;
                } else if (type === 'deduction') {
                    deductionsTotal += amount;
                }
            });
            
            // Update totals display
            this.$('.total-earnings').text(earningsTotal.toFixed(2));
            this.$('.total-deductions').text(deductionsTotal.toFixed(2));
            this.$('.net-salary').text((earningsTotal - deductionsTotal).toFixed(2));
        },
        
        _onFieldChanged: function (ev) {
            this._super.apply(this, arguments);
            if (ev.target.name === 'amount') {
                this._updateTotals();
            }
        },
    });
    
});