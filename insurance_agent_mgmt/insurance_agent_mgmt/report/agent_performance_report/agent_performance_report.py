# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import frappe
from frappe import _


def execute(filters=None):
    columns = [
        {"label": _("Agent"), "fieldname": "agent", "fieldtype": "Link", "options": "Insurance Agent", "width": 180},
        {"label": _("Agent Name"), "fieldname": "agent_name", "fieldtype": "Data", "width": 150},
        {"label": _("Territory"), "fieldname": "territory", "fieldtype": "Data", "width": 120},
        {"label": _("Active Policies"), "fieldname": "active_policies", "fieldtype": "Int", "width": 120},
        {"label": _("Premium Collected"), "fieldname": "premium_collected", "fieldtype": "Currency", "width": 150},
        {"label": _("Target Premium"), "fieldname": "target_premium", "fieldtype": "Currency", "width": 150},
        {"label": _("Achievement %"), "fieldname": "achievement_pct", "fieldtype": "Percent", "width": 120},
        {"label": _("Commission Earned"), "fieldname": "commission_earned", "fieldtype": "Currency", "width": 150},
    ]

    conditions = ""
    if filters.get("agent"):
        conditions += f" AND ia.name = '{filters.get('agent')}'"

    data = frappe.db.sql(
        f"""
        SELECT
            ia.name as agent,
            ia.agent_name,
            ia.territory,
            ia.target_premium,
            COUNT(DISTINCT ip.name) as active_policies,
            COALESCE(SUM(pp.amount), 0) as premium_collected,
            COALESCE(SUM(ac.commission_amount), 0) as commission_earned
        FROM `tabInsurance Agent` ia
        LEFT JOIN `tabInsurance Policy` ip ON ip.agent = ia.name AND ip.policy_status = 'Active'
        LEFT JOIN `tabPremium Payment` pp ON pp.agent = ia.name AND pp.status = 'Paid'
        LEFT JOIN `tabAgent Commission` ac ON ac.agent = ia.name
        WHERE ia.status = 'Active'
        GROUP BY ia.name, ia.agent_name, ia.territory, ia.target_premium
        ORDER BY premium_collected DESC
        """,
        as_dict=True,
    )

    for row in data:
        row.achievement_pct = round(
            (row.premium_collected / row.target_premium * 100) if row.target_premium else 0, 1
        )

    chart = get_chart(data)
    return columns, data, None, chart, None


def get_chart(data):
    if not data:
        return None
    return {
        "data": {
            "labels": [d.agent_name for d in data[:10]],
            "datasets": [
                {"name": "Premium Collected", "values": [d.premium_collected for d in data[:10]]},
                {"name": "Target Premium", "values": [d.target_premium or 0 for d in data[:10]]},
            ],
        },
        "type": "bar",
        "title": "Agent Premium vs Target",
        "colors": ["#5e64ff", "#d1d8dd"],
    }
