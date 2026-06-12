# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import frappe
from frappe import _


def get_current_agent():
    """Return the Insurance Agent doc name linked to the current Frappe user."""
    user = frappe.session.user
    if user == "Administrator":
        return None
    agent = frappe.db.get_value(
        "Insurance Agent", {"user": user}, "name"
    )
    return agent


def is_insurance_admin_or_manager():
    """Check if current user has Admin or Manager role."""
    roles = frappe.get_roles()
    return "Insurance Admin" in roles or "Insurance Manager" in roles


def has_permission(doc, ptype, user):
    """Permission filter: Agents can only see their own records."""
    if not doc:
        return True
    if user == "Administrator":
        return True
    roles = frappe.get_roles(user)
    if "Insurance Admin" in roles or "Insurance Manager" in roles:
        return True
    if "Insurance Agent" in roles:
        agent = frappe.db.get_value("Insurance Agent", {"user": user}, "name")
        if not agent:
            return False
        # Check if the document has an agent/assigned_agent field
        if hasattr(doc, "assigned_agent") and doc.assigned_agent:
            return doc.assigned_agent == agent
        if hasattr(doc, "agent") and doc.agent:
            return doc.agent == agent
    return False


def set_agent_session():
    """Set session data for agent on login."""
    agent = get_current_agent()
    if agent:
        frappe.session.data["insurance_agent"] = agent


@frappe.whitelist()
def get_dashboard_stats():
    """Return KPI values for the dashboard."""
    user = frappe.session.user
    is_admin = is_insurance_admin_or_manager()
    agent = get_current_agent()

    # Base filters for agent-scoped views
    lead_filter = {}
    policy_filter = {}
    if not is_admin and agent:
        lead_filter["assigned_agent"] = agent
        policy_filter["agent"] = agent

    leads_total = frappe.db.count("Insurance Lead", filters=lead_filter)
    leads_new = frappe.db.count(
        "Insurance Lead", filters={**lead_filter, "status": "New"}
    )
    leads_converted = frappe.db.count(
        "Insurance Lead", filters={**lead_filter, "status": "Converted"}
    )

    policies_active = frappe.db.count(
        "Insurance Policy", filters={**policy_filter, "policy_status": "Active"}
    )

    renewals_due = frappe.db.sql(
        """
        SELECT COUNT(*) as total
        FROM `tabPolicy Renewal`
        WHERE status IN ('Due', 'Contacted', 'Grace Period')
        """
        + (" AND agent = %(agent)s" if not is_admin and agent else ""),
        {"agent": agent} if not is_admin and agent else {},
        as_dict=True,
    )

    premium_this_month = frappe.db.sql(
        """
        SELECT COALESCE(SUM(amount), 0) as total
        FROM `tabPremium Payment`
        WHERE status = 'Paid'
          AND MONTH(payment_date) = MONTH(CURDATE())
          AND YEAR(payment_date) = YEAR(CURDATE())
        """
        + (" AND agent = %(agent)s" if not is_admin and agent else ""),
        {"agent": agent} if not is_admin and agent else {},
        as_dict=True,
    )

    commission_pending = frappe.db.sql(
        """
        SELECT COALESCE(SUM(commission_amount), 0) as total
        FROM `tabAgent Commission`
        WHERE payment_status = 'Pending'
        """
        + (" AND agent = %(agent)s" if not is_admin and agent else ""),
        {"agent": agent} if not is_admin and agent else {},
        as_dict=True,
    )

    return {
        "leads_total": leads_total,
        "leads_new": leads_new,
        "leads_converted": leads_converted,
        "conversion_rate": round(
            (leads_converted / leads_total * 100) if leads_total else 0, 1
        ),
        "policies_active": policies_active,
        "renewals_due": renewals_due[0]["total"] if renewals_due else 0,
        "premium_this_month": premium_this_month[0]["total"] if premium_this_month else 0,
        "commission_pending": commission_pending[0]["total"] if commission_pending else 0,
    }
