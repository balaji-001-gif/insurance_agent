# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import frappe
from frappe import _


def execute(filters=None):
    columns = [
        {"label": _("Agent"), "fieldname": "agent", "fieldtype": "Link", "options": "Insurance Agent", "width": 180},
        {"label": _("Agent Name"), "fieldname": "agent_name", "fieldtype": "Data", "width": 150},
        {"label": _("Total Leads"), "fieldname": "total_leads", "fieldtype": "Int", "width": 100},
        {"label": _("Converted"), "fieldname": "converted", "fieldtype": "Int", "width": 100},
        {"label": _("Qualified"), "fieldname": "qualified", "fieldtype": "Int", "width": 100},
        {"label": _("Lost"), "fieldname": "lost", "fieldtype": "Int", "width": 100},
        {"label": _("Conversion Rate"), "fieldname": "conversion_rate", "fieldtype": "Percent", "width": 120},
    ]

    conditions = ""
    if filters.get("agent"):
        conditions += f" AND il.assigned_agent = '{filters.get('agent')}'"
    if filters.get("from_date"):
        conditions += f" AND il.lead_date >= '{filters.get('from_date')}'"
    if filters.get("to_date"):
        conditions += f" AND il.lead_date <= '{filters.get('to_date')}'"

    data = frappe.db.sql(
        f"""
        SELECT
            il.assigned_agent as agent,
            ia.agent_name,
            COUNT(il.name) as total_leads,
            SUM(CASE WHEN il.status = 'Converted' THEN 1 ELSE 0 END) as converted,
            SUM(CASE WHEN il.status = 'Qualified' THEN 1 ELSE 0 END) as qualified,
            SUM(CASE WHEN il.status IN ('Lost', 'Not Interested') THEN 1 ELSE 0 END) as lost
        FROM `tabInsurance Lead` il
        LEFT JOIN `tabInsurance Agent` ia ON ia.name = il.assigned_agent
        WHERE il.assigned_agent IS NOT NULL {conditions}
        GROUP BY il.assigned_agent, ia.agent_name
        ORDER BY total_leads DESC
        """,
        as_dict=True,
    )

    for row in data:
        row.conversion_rate = round(
            (row.converted / row.total_leads * 100) if row.total_leads else 0, 1
        )

    charts = get_chart(data)
    summary = get_summary(data)

    return columns, data, None, charts, summary


def get_chart(data):
    if not data:
        return None
    return {
        "data": {
            "labels": [d.agent_name or d.agent for d in data],
            "datasets": [
                {"name": "Converted", "values": [d.converted for d in data]},
                {"name": "Qualified", "values": [d.qualified for d in data]},
                {"name": "Lost", "values": [d.lost for d in data]},
            ],
        },
        "type": "bar",
        "title": "Lead Funnel by Agent",
        "colors": ["#28a745", "#ffc107", "#dc3545"],
    }


def get_summary(data):
    if not data:
        return []
    total_leads = sum(d.total_leads for d in data)
    total_converted = sum(d.converted for d in data)
    overall_rate = round(total_converted / total_leads * 100, 1) if total_leads else 0
    return [
        {"label": "Total Leads", "value": total_leads, "indicator": "blue", "datatype": "Int"},
        {"label": "Converted", "value": total_converted, "indicator": "green", "datatype": "Int"},
        {"label": "Conversion Rate", "value": f"{overall_rate}%", "indicator": "green", "datatype": "Data"},
    ]
