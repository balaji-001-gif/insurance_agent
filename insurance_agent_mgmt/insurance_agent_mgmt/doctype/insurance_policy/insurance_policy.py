# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, add_years, today, getdate, flt

from insurance_agent_mgmt.utils import FREQ_DAYS


class InsurancePolicy(Document):

    def validate(self):
        self.set_age_at_commencement()
        self.set_next_premium_date()
        self.set_maturity_date()
        self.validate_sum_assured()
        self.validate_auto_calculate_sum_assured()
        self.validate_nominee_shares()
        self.validate_health_dependencies()
        self.calculate_health_premium_loading()
        self.generate_premium_schedule()
        self.update_schedule_summary()
        self.sync_schedule_with_payments()

    def set_age_at_commencement(self):
        """Calculate and set the customer's age at policy commencement."""
        if self.commencement_date and self.customer:
            customer_dob = frappe.db.get_value("Insurance Customer", self.customer, "date_of_birth")
            if customer_dob:
                from frappe.utils import date_diff
                birth = getdate(customer_dob)
                comm = getdate(self.commencement_date)
                age = comm.year - birth.year - ((comm.month, comm.day) < (birth.month, birth.day))
                self.age_at_commencement = age

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

    def validate_auto_calculate_sum_assured(self):
        """Auto-calculate sum assured based on customer age and product formula.
        This runs when commencement_date, insurance_product, or customer changes.
        """
        if not self.insurance_product or not self.commencement_date or not self.customer:
            return

        product = frappe.get_cached_doc("Insurance Product", self.insurance_product)
        if not product.enable_auto_calculation:
            return

        # Ensure age_at_commencement is set
        if not self.age_at_commencement:
            self.set_age_at_commencement()

        if not self.age_at_commencement:
            return

        calculated = product.calculate_sum_assured(self.age_at_commencement)
        if calculated is not None:
            self.sum_assured = calculated

            # Also suggest premium amount if not already set
            if not self.premium_amount or self.has_value_changed("insurance_product"):
                # Suggest premium as ~5% of sum assured for life, ~2% for health
                product_type = product.product_type or ""
                rate = 0.05 if "Life" in product_type or "Term" in product_type else 0.02
                if "Vehicle" in product_type:
                    rate = 0.03
                elif "Property" in product_type:
                    rate = 0.01
                suggested_premium = calculated * rate
                if not self.premium_amount:
                    self.premium_amount = suggested_premium

    def validate_nominee_shares(self):
        """Validate that nominee shares total to 100% if nominees are set."""
        if self.policy_nominees:
            total_share = sum(
                flt(nominee.nominee_share or 0)
                for nominee in self.policy_nominees
            )
            if total_share <= 0:
                frappe.throw(_("Total nominee share must be greater than 0%%. Please set nominee shares."))
            if total_share > 100:
                frappe.throw(
                    _("Total nominee share {0}% exceeds 100%%. Please adjust nominee shares.")
                    .format(total_share)
                )

    def validate_health_dependencies(self):
        """Validate health dependencies section if present."""
        if self.health_dependencies:
            # Ensure the product is a health insurance product
            product = frappe.get_cached_doc("Insurance Product", self.insurance_product)
            if product.product_type != "Health Insurance":
                frappe.throw(
                    _("Health Dependencies can only be added for Health Insurance products.")
                )

    def calculate_health_premium_loading(self):
        """Calculate health premium loading from health_dependencies.

        Sums all additional_loading_pct from the health_dependencies child table,
        captures the base premium once, calculates the loading amount, and updates
        premium_amount to include the loading.

        When health deps are cleared or loading reaches 0%,
        premium_amount is reverted back to base_premium_amount.
        """
        if not self.health_dependencies:
            # Health deps removed — revert premium back to base
            if self.health_loading_total_pct or self.health_loading_amount:
                if self.base_premium_amount:
                    self.premium_amount = self.base_premium_amount
                self.health_loading_total_pct = 0
                self.health_loading_amount = 0
            return

        if not self.premium_amount:
            return

        # Sum all loading percentages from health dependencies
        total_loading_pct = sum(
            flt(dep.additional_loading_pct or 0)
            for dep in self.health_dependencies
        )

        # Clamp to a reasonable range (0% to 200%)
        total_loading_pct = max(0.0, min(total_loading_pct, 200.0))

        if total_loading_pct <= 0:
            # No loading to apply — revert to base
            if self.base_premium_amount:
                self.premium_amount = self.base_premium_amount
            self.health_loading_total_pct = 0
            self.health_loading_amount = 0
            return

        # Capture base premium once — never re-capture after it's set
        # This prevents compounding when health deps are modified
        if not self.base_premium_amount:
            self.base_premium_amount = self.premium_amount

        # Calculate loading amount on the original base
        base = flt(self.base_premium_amount)
        loading_amount = base * total_loading_pct / 100.0

        # Set the loaded premium
        self.health_loading_total_pct = total_loading_pct
        self.health_loading_amount = loading_amount
        self.premium_amount = base + loading_amount

    def generate_premium_schedule(self):
        """Auto-generate or regenerate the premium payment schedule.

        Creates a row for each installment from commencement_date to maturity_date
        based on the premium_frequency. Skips if schedule already exists and nothing changed.
        """
        if not self.commencement_date or not self.maturity_date or not self.premium_amount:
            return

        if not self.premium_frequency or self.premium_frequency == "Single":
            # Single premium — just one installment
            if self.premium_schedule and len(self.premium_schedule) == 1:
                return
            self.premium_schedule = []
            self.append("premium_schedule", {
                "installment_no": 1,
                "period_label": "Single Premium",
                "due_date": self.commencement_date,
                "amount": self.premium_amount,
                "status": "Pending",
            })
            return

        # Check if regeneration is needed
        needs_regeneration = (
            not self.premium_schedule
            or self.has_value_changed("premium_frequency")
            or self.has_value_changed("commencement_date")
            or self.has_value_changed("maturity_date")
            or self.has_value_changed("premium_amount")
            or self.has_value_changed("policy_term")
        )

        if not needs_regeneration:
            return

        # Calculate number of installments
        from frappe.utils import getdate, add_months, add_days, date_diff

        freq = self.premium_frequency
        freq_map = {"Monthly": 1, "Quarterly": 3, "Half-Yearly": 6, "Yearly": 12}
        months_between = freq_map.get(freq, 12)

        comm = getdate(self.commencement_date)
        mat = getdate(self.maturity_date)
        total_months = (mat.year - comm.year) * 12 + (mat.month - comm.month)

        if months_between <= 0:
            num_installments = 1
        else:
            num_installments = max(1, total_months // months_between)
            if total_months % months_between > 0:
                num_installments += 1

        # Build the schedule
        self.premium_schedule = []
        current_date = comm

        for i in range(num_installments):
            # Calculate period label
            years_in = i * months_between // 12
            remaining_months = i * months_between % 12
            period_label = self._get_period_label(freq, i + 1, years_in, remaining_months)

            # Due date: add months to commencement date
            due = add_months(comm, i * months_between) if i > 0 else comm

            # Don't go past maturity
            if due > mat:
                due = mat

            # Last installment should cover remaining period
            amt = flt(self.premium_amount)

            self.append("premium_schedule", {
                "installment_no": i + 1,
                "period_label": period_label,
                "due_date": due,
                "amount": amt,
                "status": "Pending",
            })

    def _get_period_label(self, freq, installment_no, years, months):
        """Generate a human-readable period label for a schedule installment."""
        if freq == "Yearly":
            return _("Year {0}").format(installment_no)
        elif freq == "Half-Yearly":
            return _("Half {0} - Yr {1}").format(1 if installment_no % 2 == 1 else 2, years + 1)
        elif freq == "Quarterly":
            qtr = ((installment_no - 1) % 4) + 1
            yr = (installment_no - 1) // 4 + 1
            return _("Q{0} Yr {1}").format(qtr, yr)
        elif freq == "Monthly":
            m = ((installment_no - 1) % 12) + 1
            yr = (installment_no - 1) // 12 + 1
            return _("Month {0} Yr {1}").format(m, yr)
        return _("Installment #{0}").format(installment_no)

    def update_schedule_summary(self):
        """Update the schedule summary fields on the policy."""
        total_scheduled = sum(flt(item.amount or 0) for item in (self.premium_schedule or []))
        paid_count = sum(1 for item in (self.premium_schedule or []) if item.status == "Paid")
        total_count = len(self.premium_schedule or [])
        paid_amount = sum(
            flt(item.amount or 0) for item in (self.premium_schedule or [])
            if item.status == "Paid"
        )

        self.total_scheduled_premium = total_scheduled
        self.total_pending_premium = total_scheduled - paid_amount
        self.paid_installments = paid_count
        self.total_installments = total_count

    def sync_schedule_with_payments(self):
        """Sync the premium schedule with actual Premium Payment records.

        Matches schedule items to submitted Premium Payment records by due_date.
        Updates status, paid_date, receipt_number, and payment_entry.
        """
        if not self.name or not self.premium_schedule:
            return

        # Get all submitted payments for this policy
        payments = frappe.db.get_all(
            "Premium Payment",
            filters={"policy": self.name, "docstatus": 1},
            fields=["name", "payment_date", "receipt_number", "cheque_number",
                    "amount", "due_date", "status"],
            order_by="payment_date ASC",
        )

        if not payments:
            return

        # Build a map of due_date -> payment for matching
        payment_by_due = {}
        for p in payments:
            due_key = str(p.due_date or p.payment_date)
            if due_key not in payment_by_due:
                payment_by_due[due_key] = []
            payment_by_due[due_key].append(p)

        # Update schedule items to match payments
        for item in self.premium_schedule:
            due_key = str(item.due_date)
            matching = payment_by_due.get(due_key, [])

            if matching and any(m.status == "Paid" for m in matching):
                paid = next(m for m in matching if m.status == "Paid")
                item.status = "Paid"
                item.paid_date = paid.payment_date
                item.receipt_number = paid.receipt_number
                item.payment_reference = paid.cheque_number
                item.payment_entry = paid.name
            elif matching:
                # Payment exists but not yet paid
                pass
            else:
                # No payment found — mark overdue if past due
                from frappe.utils import getdate
                if item.status != "Paid" and getdate(item.due_date) < getdate():
                    item.status = "Overdue"

    @frappe.whitelist()
    def regenerate_schedule(self):
        """Force-regenerate the premium schedule.
        Called from the Regenerate Schedule button on the form."""
        # Force clear and regenerate
        self.premium_schedule = []
        self.generate_premium_schedule()
        self.sync_schedule_with_payments()
        self.update_schedule_summary()
        return True

    def on_submit(self):
        if not self.policy_status or self.policy_status == "Proposal":
            self.db_set("policy_status", "Active")

    def on_cancel(self):
        self.db_set("policy_status", "Surrendered")
