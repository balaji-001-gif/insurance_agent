# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import frappe
from frappe.model.document import Document


class InsuranceProduct(Document):
    def validate(self):
        if self.min_age and self.max_age and self.min_age >= self.max_age:
            frappe.throw(frappe._("Min Age must be less than Max Age."))
        if self.min_sum_assured and self.max_sum_assured:
            if self.min_sum_assured >= self.max_sum_assured:
                frappe.throw(frappe._("Min Sum Assured must be less than Max Sum Assured."))
