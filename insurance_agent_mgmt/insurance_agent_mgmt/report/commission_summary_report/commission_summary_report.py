# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import frappe
from frappe import _


def execute(filters=None):
    columns = [
        {"label": _("Agent"), "fieldname": "agent", "fieldtype": "Link", "options": "Insurance Agent", "width": 180},
        {"label": _("Agent Name"), "fieldname": "agent_name", "fieldtype": "Data", "width": 150},
        {"label": _("First Year"), "fieldname": "first_year", "fieldtype": "Currency", "width": 130},
        {"label": _("Renewal"), "fieldname": "renewal", "fieldtype": "Currency", "width": 130},
        {"label": _("Bonus"), "fieldname": "bonus", "fieldtype": "Currency", "width": 130},
        {"label": _("Total Commission"), "fieldname": "total_commission", "fieldtype": "Currency", "width": 150},
        {"label": _("TDS"), "fieldname": "total_tds", "fieldtype": "Currency", "width": 120},
        {"label": _("Net Payable"), "fieldname": "net_payable", "fieldtype": "Currency", "width": 150},
        {"label": _("Paid"), "fieldname": "paid", "fieldtype": "Currency", "width": 130},
        {"label": _("Pending"), "fieldname": "pending", "fieldtype": "Currency", "width": 130},
    ]

    conditions = ""
    if filters.get("agent"):
        conditions += f" AND ac.agent = '{filters.get('agent')}'"
    if filters.get("from_date"):
        conditions += f" AND ac.commission_date >= '{filters.get('from_date')}'"
    if filters.get("to_date"):
        conditions += f" AND ac.commission_date <= '{filters.get('to_date')}'"

    data = frappe.db.sql(
        f"""
        SELECT ac.agent, ia.agent_name,
            SUM(CASE WHEN ac.commission_type = 'First Year' THEN ac.commission_amount ELSE 0 END) as first_year,
            SUM(CASE WHEN ac.commission_type = 'Renewal' THEN ac.commission_amount ELSE 0 END) as renewal,
            SUM(CASE WHEN ac.commission_type = 'Bonus' THEN ac.commission_amount ELSE 0 END) as bonus,
            SUM(ac.commission_amount) as total_commission,
            SUM(COALESCE(ac.tds_amount, 0)) as total_tds,
            SUM(COALESCE(ac.net_commission, ac.commission_amount)) as net_payable,
            SUM(CASE WHEN ac.payment_status = 'Paid' THEN ac.commission_amount ELSE 0 END) as paid,
            SUM(CASE WHEN ac.payment_status = 'Pending' THEN ac.commission_amount ELSE 0 END) as pending
        FROM `tabAgent Commission` ac
        LEFT JOIN `tabInsurance Agent` ia ON ia.name = ac.agent
        WHERE 1=1 {conditions}
        GROUP BY ac.agent, ia.agent_name
        ORDER BY total_commission DESC
        """,
        as_dict=True,
    )

    summary = get_summary(data)
    return columns, data, None, None, summary


def get_summary(data):
    total = sum(float(d.total_commission or 0) for d in data)
    pending = sum(float(d.pending or 0) for d in data)
    return [
        {"label": "Total Commission", "value": total, "indicator": "blue", "datatype": "Currency"},
        {"label": "Pending Payout", "value": pending, "indicator": "orange", "datatype": "Currency"},
    ]
