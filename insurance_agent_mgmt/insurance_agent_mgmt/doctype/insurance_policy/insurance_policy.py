# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, add_years

from insurance_agent_mgmt.utils import FREQ_DAYS


class InsurancePolicy(Document):

    def validate(self):
        self.set_next_premium_date()
        self.set_maturity_date()
        self.validate_sum_assured()

    def set_next_premium_date(self):
        if not self.next_premium_date and self.commencement_date and self.premium_frequency != "Single":
            days = FREQ_DAYS.get(self.premium_frequency, 365)
            self.next_premium_date = add_days(self.commencement_date, days)

    def set_maturity_date(self):
        if not self.maturity_date and self.commencement_date and self.policy_term:
            self.maturity_date = add_years(self.commencement_date, int(self.policy_term))

    def validate_sum_assured(self):
        product = frappe.get_doc("Insurance Product", self.insurance_product)
        if product.min_sum_assured and self.sum_assured < product.min_sum_assured:
            frappe.throw(
                _(
                    "Sum Assured ₹{0} is below minimum ₹{1} for product {2}."
                ).format(self.sum_assured, product.min_sum_assured, self.insurance_product)
            )

    def on_submit(self):
        if not self.policy_status or self.policy_status == "Proposal":
            self.db_set("policy_status", "Active")

    def on_cancel(self):
        self.db_set("policy_status", "Surrendered")
