# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import flt


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


def create_agent_commission_on_payment(doc, method):
    """Auto-create Agent Commission when a Premium Payment is submitted."""
    if doc.docstatus != 1:
        return

    # Determine the agent: from payment or from the linked policy
    agent = doc.agent
    if not agent and doc.policy:
        policy = frappe.get_doc("Insurance Policy", doc.policy)
        agent = policy.agent

    if not agent:
        return

    # Check if any paid payments already exist for this policy
    existing_payments = frappe.db.count("Premium Payment", {
        "policy": doc.policy,
        "status": "Paid",
        "name": ("!=", doc.name),
    })
    commission_type = "First Year" if existing_payments == 0 else "Renewal"

    # Get commission rate from product, then fall back to agent default
    commission_rate = 0
    policy = frappe.get_doc("Insurance Policy", doc.policy) if doc.policy else None
    if policy and policy.insurance_product:
        product = frappe.get_doc("Insurance Product", policy.insurance_product)
        if commission_type == "First Year":
            commission_rate = flt(product.commission_rate or 0)
        else:
            commission_rate = flt(product.renewal_commission_rate or 0)

    # Fallback to agent's default commission rate
    if not commission_rate:
        agent_doc = frappe.get_cached_doc("Insurance Agent", agent)
        commission_rate = flt(agent_doc.commission_rate or 0)

    premium_amount = flt(doc.amount or 0)
    commission_amount = premium_amount * commission_rate / 100.0

    commission = frappe.get_doc({
        "doctype": "Agent Commission",
        "agent": agent,
        "policy": doc.policy,
        "customer": doc.customer,
        "commission_type": commission_type,
        "commission_date": doc.payment_date,
        "payment_status": "Pending",
        "premium_amount": premium_amount,
        "commission_rate": commission_rate,
        "commission_amount": commission_amount,
        "remarks": f"Auto-created from Premium Payment: {doc.name}",
    })
    commission.flags.ignore_permissions = True
    commission.insert()


def cancel_agent_commission_on_payment(doc, method):
    """Remove the auto-created Agent Commission when a Premium Payment is cancelled."""
    if doc.docstatus != 2:
        return

    commission_name = frappe.db.get_value("Agent Commission", {
        "policy": doc.policy,
        "agent": doc.agent,
        "commission_date": doc.payment_date,
        "remarks": ("like", f"%{doc.name}%"),
    })

    if commission_name:
        frappe.delete_doc("Agent Commission", commission_name, ignore_permissions=True)


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


def create_agent_commission_on_payment(doc, method):
    """Auto-create Agent Commission when a Premium Payment is submitted."""
    if doc.docstatus != 1:
        return

    # Determine the agent: from payment or from the linked policy
    agent = doc.agent
    if not agent and doc.policy:
        policy = frappe.get_doc("Insurance Policy", doc.policy)
        agent = policy.agent

    if not agent:
        return

    # Check if any paid payments already exist for this policy
    existing_payments = frappe.db.count("Premium Payment", {
        "policy": doc.policy,
        "status": "Paid",
        "name": ("!=", doc.name),
    })
    commission_type = "First Year" if existing_payments == 0 else "Renewal"

    # Get commission rate from product, then fall back to agent default
    commission_rate = 0
    policy = frappe.get_doc("Insurance Policy", doc.policy) if doc.policy else None
    if policy and policy.insurance_product:
        product = frappe.get_doc("Insurance Product", policy.insurance_product)
        if commission_type == "First Year":
            commission_rate = flt(product.commission_rate or 0)
        else:
            commission_rate = flt(product.renewal_commission_rate or 0)

    # Fallback to agent's default commission rate
    if not commission_rate:
        agent_doc = frappe.get_cached_doc("Insurance Agent", agent)
        commission_rate = flt(agent_doc.commission_rate or 0)

    premium_amount = flt(doc.amount or 0)
    commission_amount = premium_amount * commission_rate / 100.0

    commission = frappe.get_doc({
        "doctype": "Agent Commission",
        "agent": agent,
        "policy": doc.policy,
        "customer": doc.customer,
        "commission_type": commission_type,
        "commission_date": doc.payment_date,
        "payment_status": "Pending",
        "premium_amount": premium_amount,
        "commission_rate": commission_rate,
        "commission_amount": commission_amount,
        "remarks": f"Auto-created from Premium Payment: {doc.name}",
    })
    commission.flags.ignore_permissions = True
    commission.insert()


def cancel_agent_commission_on_payment(doc, method):
    """Remove the auto-created Agent Commission when a Premium Payment is cancelled."""
    if doc.docstatus != 2:
        return

    commission_name = frappe.db.get_value("Agent Commission", {
        "policy": doc.policy,
        "agent": doc.agent,
        "commission_date": doc.payment_date,
        "remarks": ("like", f"%{doc.name}%"),
    })

    if commission_name:
        frappe.delete_doc("Agent Commission", commission_name, ignore_permissions=True)
