# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from collections import defaultdict

import frappe
from frappe import _


def execute(filters=None):
    columns = [
        {"label": _("Policy"), "fieldname": "policy", "fieldtype": "Link", "options": "Insurance Policy", "width": 180},
        {"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link", "options": "Insurance Customer", "width": 150},
        {"label": _("Agent"), "fieldname": "agent", "fieldtype": "Link", "options": "Insurance Agent", "width": 150},
        {"label": _("Payment Date"), "fieldname": "payment_date", "fieldtype": "Date", "width": 120},
        {"label": _("Amount"), "fieldname": "amount", "fieldtype": "Currency", "width": 130},
        {"label": _("Mode"), "fieldname": "payment_mode", "fieldtype": "Data", "width": 120},
        {"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 100},
    ]

    conditions = ""
    if filters.get("from_date"):
        conditions += f" AND pp.payment_date >= '{filters.get('from_date')}'"
    if filters.get("to_date"):
        conditions += f" AND pp.payment_date <= '{filters.get('to_date')}'"
    if filters.get("agent"):
        conditions += f" AND pp.agent = '{filters.get('agent')}'"

    data = frappe.db.sql(
        f"""
        SELECT pp.name, pp.policy, pp.customer, pp.agent,
               pp.payment_date, pp.amount, pp.payment_mode, pp.status
        FROM `tabPremium Payment` pp
        WHERE 1=1 {conditions}
        ORDER BY pp.payment_date DESC
        """,
        as_dict=True,
    )

    chart = get_chart(data)
    summary = get_summary(data)

    return columns, data, None, chart, summary


def get_chart(data):
    if not data:
        return None
    monthly = defaultdict(float)
    for row in data:
        if row.payment_date:
            key = str(row.payment_date)[:7]
            monthly[key] += float(row.amount or 0)
    months = sorted(monthly.keys())
    return {
        "data": {
            "labels": months,
            "datasets": [{"name": "Collection", "values": [monthly[m] for m in months]}],
        },
        "type": "line",
        "title": "Monthly Premium Collection",
        "colors": ["#28a745"],
    }


def get_summary(data):
    total = sum(float(d.amount or 0) for d in data if d.status == "Paid")
    return [
        {"label": "Total Collected", "value": total, "indicator": "green", "datatype": "Currency"},
        {"label": "Transactions", "value": len(data), "indicator": "blue", "datatype": "Int"},
    ]
