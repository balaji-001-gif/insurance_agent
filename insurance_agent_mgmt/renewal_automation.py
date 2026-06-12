# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import frappe
from frappe.utils import add_days, today, now_datetime


def auto_create_policy_renewals():
    """Daily scheduled task: create Policy Renewal records for policies
    whose next_premium_date falls within the upcoming renewal window (30 days)."""
    renewal_window = 30
    end_date = add_days(today(), renewal_window)

    # Find active policies with an upcoming premium date
    policies = frappe.db.sql(
        """
        SELECT ip.name, ip.customer, ip.agent,
               ip.next_premium_date, ip.premium_amount
        FROM `tabInsurance Policy` ip
        WHERE ip.policy_status = 'Active'
          AND ip.premium_frequency != 'Single'
          AND ip.next_premium_date IS NOT NULL
          AND ip.next_premium_date <= %(end_date)s
        ORDER BY ip.next_premium_date ASC
        """,
        {
            "end_date": end_date,
        },
        as_dict=True,
    )

    created = 0
    skipped = 0

    for policy in policies:
        # Skip if a renewal record already exists for this policy + due date
        existing = frappe.db.exists("Policy Renewal", {
            "policy": policy.name,
            "renewal_due_date": policy.next_premium_date,
            "docstatus": ("!=", 2),  # not cancelled
        })

        if existing:
            skipped += 1
            continue

        try:
            renewal = frappe.get_doc({
                "doctype": "Policy Renewal",
                "policy": policy.name,
                "customer": policy.customer,
                "agent": policy.agent,
                "renewal_due_date": policy.next_premium_date,
                "renewal_amount": policy.premium_amount,
                "status": "Due",
            })
            renewal.flags.ignore_permissions = True
            renewal.flags.ignore_validate = True  # priority will be set on next validate
            renewal.insert()
            created += 1
        except Exception as e:
            frappe.log_error(
                title="Policy Renewal Auto-Creation Failed",
                message=f"Policy {policy.name}: {e}"
            )

    frappe.db.commit()

    if created or skipped:
        frappe.log_error(
            title="Policy Renewal Auto-Creation Summary",
            message=f"Created: {created}, Skipped (already exists): {skipped}, Date: {now_datetime()}"
        )


def mark_lapsed_policies():
    """Daily scheduled task: mark Active policies as Lapsed when their
    next_premium_date has passed by more than the grace period (30 days)
    without a corresponding paid premium payment."""
    grace_period_days = 30
    cutoff_date = add_days(today(), -grace_period_days)

    # Find active policies that are past due beyond the grace period
    policies = frappe.db.sql(
        """
        SELECT ip.name, ip.customer, ip.agent,
               ip.next_premium_date, ip.premium_amount, ip.premium_frequency
        FROM `tabInsurance Policy` ip
        WHERE ip.policy_status = 'Active'
          AND ip.premium_frequency != 'Single'
          AND ip.next_premium_date IS NOT NULL
          AND ip.next_premium_date <= %(cutoff_date)s
        ORDER BY ip.next_premium_date ASC
        """,
        {"cutoff_date": cutoff_date},
        as_dict=True,
    )

    marked = 0
    skipped = 0

    for policy in policies:
        # Check if a paid payment exists after the due date for this policy
        paid = frappe.db.exists("Premium Payment", {
            "policy": policy.name,
            "status": "Paid",
            "payment_date": (">=", policy.next_premium_date),
            "docstatus": 1,
        })

        if paid:
            skipped += 1
            continue

        try:
            # Mark policy as Lapsed
            frappe.db.set_value("Insurance Policy", policy.name, "policy_status", "Lapsed")

            # Update related Policy Renewal records to Lapsed
            renewals = frappe.db.get_all("Policy Renewal", {
                "policy": policy.name,
                "status": ["in", ["Due", "Contacted", "Grace Period"]],
            }, pluck="name")
            for rn in renewals:
                frappe.db.set_value("Policy Renewal", rn, "status", "Lapsed", update_modified=False)

            marked += 1
        except Exception as e:
            frappe.log_error(
                title="Lapsed Policy Marking Failed",
                message=f"Policy {policy.name}: {e}"
            )

    frappe.db.commit()

    if marked or skipped:
        frappe.log_error(
            title="Lapsed Policy Marking Summary",
            message=f"Marked as Lapsed: {marked}, Skipped (paid): {skipped}, Date: {now_datetime()}"
        )
