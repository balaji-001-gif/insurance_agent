# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import frappe
from frappe.model.document import Document


class InsuranceProduct(Document):
    def validate(self):
        self.validate_age_range()
        self.validate_sum_assured_range()
        self.validate_auto_calculation_settings()

    def validate_age_range(self):
        if self.min_age and self.max_age and self.min_age >= self.max_age:
            frappe.throw(frappe._("Min Age must be less than Max Age."))

    def validate_sum_assured_range(self):
        if self.min_sum_assured and self.max_sum_assured:
            if self.min_sum_assured >= self.max_sum_assured:
                frappe.throw(frappe._("Min Sum Assured must be less than Max Sum Assured."))

    def validate_auto_calculation_settings(self):
        if self.enable_auto_calculation:
            if self.min_sum_assured_auto and self.max_sum_assured_auto:
                if self.min_sum_assured_auto >= self.max_sum_assured_auto:
                    frappe.throw(frappe._("Min Auto Sum Assured must be less than Max Auto Sum Assured."))

    def calculate_sum_assured(self, customer_age):
        """Calculate the suggested sum assured based on customer age.
        
        Args:
            customer_age: Age of the customer in years.
        Returns:
            Calculated sum assured amount, or None if auto-calculation is disabled.
        """
        if not self.enable_auto_calculation or not customer_age:
            return None

        if self.calculation_formula == "Base + (Age × Multiplier)":
            base = self.base_sum_assured or 0
            multiplier = self.age_multiplier or 0
            calculated = base + (customer_age * multiplier)
        elif self.calculation_formula == "Base × Age":
            base = self.base_sum_assured or 0
            calculated = base * customer_age
        elif self.calculation_formula == "Fixed Amount":
            calculated = self.base_sum_assured or 0
        else:
            # Custom - just use base
            calculated = self.base_sum_assured or 0

        # Apply min/max limits
        if self.min_sum_assured_auto and calculated < self.min_sum_assured_auto:
            calculated = self.min_sum_assured_auto
        if self.max_sum_assured_auto and calculated > self.max_sum_assured_auto:
            calculated = self.max_sum_assured_auto

        if self.min_sum_assured and calculated < self.min_sum_assured:
            calculated = self.min_sum_assured

        return calculated
