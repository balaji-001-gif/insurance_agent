# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import frappe
from frappe.model.document import Document
from frappe.utils import add_days, today

FREQ_DAYS = {
    "Monthly": 30,
    "Quarterly": 90,
    "Half-Yearly": 180,
    "Yearly": 365,
}


class PremiumPayment(Document):

    def validate(self):
        if self.amount <= 0:
            frappe.throw(frappe._("Payment amount must be greater than zero."))

    def on_submit(self):
        self.db_set("status", "Paid")
        self.update_policy_on_payment()

    def on_cancel(self):
        self.db_set("status", "Refunded")
        self.reverse_policy_on_cancel()

    def update_policy_on_payment(self):
        """Update the parent Insurance Policy after a successful premium payment."""
        if not self.policy:
            return

        policy = frappe.get_doc("Insurance Policy", self.policy)

        # Increment total premium paid
        current_total = float(policy.total_premium_paid or 0)
        policy.db_set("total_premium_paid", current_total + float(self.amount))

        # Advance next premium date based on frequency
        if policy.premium_frequency and policy.premium_frequency != "Single":
            days = FREQ_DAYS.get(policy.premium_frequency, 365)
            from_date = policy.next_premium_date or policy.commencement_date or today()
            policy.db_set("next_premium_date", add_days(from_date, days))

    def reverse_policy_on_cancel(self):
        """Reverse the policy update when a premium payment is cancelled."""
        if not self.policy:
            return

        policy = frappe.get_doc("Insurance Policy", self.policy)

        # Decrement total premium paid (floor at 0)
        current_total = float(policy.total_premium_paid or 0)
        new_total = max(0, current_total - float(self.amount))
        policy.db_set("total_premium_paid", new_total)
