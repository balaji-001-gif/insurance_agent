# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import frappe
from frappe.model.document import Document
from frappe.utils import add_days, today

from insurance_agent_mgmt.utils import FREQ_DAYS


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

        # Reactivate if policy was lapsed
        if policy.policy_status == "Lapsed":
            policy.db_set("policy_status", "Active")

        # Increment total premium paid
        current_total = float(policy.total_premium_paid or 0)
        policy.db_set("total_premium_paid", current_total + float(self.amount))

        # Advance next premium date based on frequency
        if policy.premium_frequency and policy.premium_frequency != "Single":
            days = FREQ_DAYS.get(policy.premium_frequency, 365)
            from_date = policy.next_premium_date or policy.commencement_date or today()
            policy.db_set("next_premium_date", add_days(from_date, days))

        # Sync with the premium schedule on the policy
        self._sync_schedule_item(policy)

    def _sync_schedule_item(self, policy):
        """Find and update the matching premium schedule item on the policy."""
        if not policy.premium_schedule:
            return

        due_key = str(self.due_date or self.payment_date)
        updated = False

        for item in policy.premium_schedule:
            if str(item.due_date) == due_key and item.status != "Paid":
                item.status = "Paid"
                item.paid_date = self.payment_date
                item.receipt_number = self.receipt_number
                item.payment_reference = self.cheque_number
                item.payment_entry = self.name
                updated = True
                break

        if updated:
            # Update summary fields before saving (since we use ignore_validate)
            self._update_policy_summary(policy)
            policy.flags.ignore_permissions = True
            policy.flags.ignore_validate = True
            policy.save()

    def _update_policy_summary(self, policy):
        """Recompute schedule summary fields on the policy doc."""
        if not hasattr(policy, "premium_schedule") or not policy.premium_schedule:
            return
        from frappe.utils import flt
        total_scheduled = sum(flt(item.amount or 0) for item in policy.premium_schedule)
        paid_count = sum(1 for item in policy.premium_schedule if item.status == "Paid")
        paid_amount = sum(
            flt(item.amount or 0) for item in policy.premium_schedule
            if item.status == "Paid"
        )
        policy.total_scheduled_premium = total_scheduled
        policy.total_pending_premium = total_scheduled - paid_amount
        policy.paid_installments = paid_count
        policy.total_installments = len(policy.premium_schedule)

    def _unsync_schedule_item(self, policy):
        """Revert the matching schedule item back to Pending when a payment is cancelled."""
        if not policy.premium_schedule:
            return

        reverted = False
        for item in policy.premium_schedule:
            if item.payment_entry == self.name:
                item.status = "Pending"
                item.paid_date = None
                item.receipt_number = None
                item.payment_reference = None
                item.payment_entry = None
                reverted = True
                break

        if reverted:
            # Update summary fields before saving (since we use ignore_validate)
            self._update_policy_summary(policy)
            policy.flags.ignore_permissions = True
            policy.flags.ignore_validate = True
            policy.save()

    def reverse_policy_on_cancel(self):
        """Reverse the policy update when a premium payment is cancelled."""
        if not self.policy:
            return

        policy = frappe.get_doc("Insurance Policy", self.policy)

        # Decrement total premium paid (floor at 0)
        current_total = float(policy.total_premium_paid or 0)
        new_total = max(0, current_total - float(self.amount))
        policy.db_set("total_premium_paid", new_total)

        # Revert the schedule item
        self._unsync_schedule_item(policy)
