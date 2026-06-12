# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import frappe
from frappe import _


@frappe.whitelist()
def convert_lead_to_customer(lead_name):
    """Convert an Insurance Lead to an Insurance Customer."""
    lead = frappe.get_doc("Insurance Lead", lead_name)

    if frappe.db.exists("Insurance Customer", {"lead": lead_name}):
        frappe.throw(_("Customer already exists for this lead."))

    customer = frappe.get_doc({
        "doctype": "Insurance Customer",
        "customer_name": lead.lead_name,
        "mobile_no": lead.mobile_no,
        "email_id": lead.email_id,
        "date_of_birth": lead.date_of_birth,
        "gender": lead.gender,
        "occupation": lead.occupation,
        "annual_income": lead.annual_income,
        "assigned_agent": lead.assigned_agent,
        "lead": lead.name,
        "address": lead.address,
        "city": lead.city,
        "state": lead.state,
        "pincode": lead.pincode,
    })
    customer.flags.ignore_permissions = True
    customer.insert()

    lead.db_set("status", "Converted")

    return {"customer": customer.name}


@frappe.whitelist()
def get_lead_timeline(lead_name):
    """Return follow-up activities for a lead."""
    activities = frappe.db.get_all(
        "Follow Up Activity",
        filters={"lead": lead_name},
        fields=["activity_date", "activity_type", "subject", "outcome"],
        order_by="activity_date DESC",
    )
    return activities


@frappe.whitelist()
def get_policy_summary(customer_name):
    """Return all policies for a customer."""
    policies = frappe.db.get_all(
        "Insurance Policy",
        filters={"customer": customer_name},
        fields=["name", "insurance_product", "policy_status", "sum_assured",
                "premium_amount", "next_premium_date"],
        order_by="creation DESC",
    )
    return policies


@frappe.whitelist()
def get_monthly_trends():
    """Return monthly premium collection data for charts."""
    data = frappe.db.sql(
        """
        SELECT MONTH(payment_date) as month_num,
               MONTHNAME(payment_date) as month_name,
               SUM(amount) as total
        FROM `tabPremium Payment`
        WHERE status = 'Paid'
          AND YEAR(payment_date) = YEAR(CURDATE())
        GROUP BY MONTH(payment_date), MONTHNAME(payment_date)
        ORDER BY month_num
        """,
        as_dict=True,
    )
    return data


@frappe.whitelist()
def get_lead_funnel():
    """Return lead counts by status for funnel chart."""
    statuses = [
        "New", "Contacted", "Follow-up",
        "Qualified", "Proposal Sent", "Converted",
        "Not Interested", "Lost",
    ]
    result = []
    for status in statuses:
        count = frappe.db.count("Insurance Lead", filters={"status": status})
        result.append({"status": status, "count": count})
    return result


@frappe.whitelist()
def get_agent_leaderboard(period="monthly"):
    """Return agent ranking by premium collected."""
    data = frappe.db.sql(
        """
        SELECT ia.name as agent,
               ia.agent_name,
               COUNT(DISTINCT ip.name) as policies_count,
               COALESCE(SUM(pp.amount), 0) as total_premium,
               CASE WHEN ia.target_premium > 0
                    THEN ROUND(COALESCE(SUM(pp.amount), 0) / ia.target_premium * 100, 1)
                    ELSE 0
               END as achievement_pct
        FROM `tabInsurance Agent` ia
        LEFT JOIN `tabInsurance Policy` ip ON ip.agent = ia.name AND ip.policy_status = 'Active'
        LEFT JOIN `tabPremium Payment` pp ON pp.agent = ia.name AND pp.status = 'Paid'
        WHERE ia.status = 'Active'
        GROUP BY ia.name, ia.agent_name, ia.target_premium
        ORDER BY total_premium DESC
        LIMIT 10
        """,
        as_dict=True,
    )
    return data
