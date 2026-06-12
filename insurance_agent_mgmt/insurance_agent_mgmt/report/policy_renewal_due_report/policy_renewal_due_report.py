# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import add_days, today


def execute(filters=None):
    columns = [
        {"label": _("Policy"), "fieldname": "policy", "fieldtype": "Link", "options": "Insurance Policy", "width": 180},
        {"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link", "options": "Insurance Customer", "width": 150},
        {"label": _("Agent"), "fieldname": "agent", "fieldtype": "Link", "options": "Insurance Agent", "width": 150},
        {"label": _("Due Date"), "fieldname": "renewal_due_date", "fieldtype": "Date", "width": 120},
        {"label": _("Amount"), "fieldname": "renewal_amount", "fieldtype": "Currency", "width": 130},
        {"label": _("Priority"), "fieldname": "priority", "fieldtype": "Data", "width": 100},
        {"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 100},
        {"label": _("Days Left"), "fieldname": "days_left", "fieldtype": "Int", "width": 90},
    ]

    days_ahead = int(filters.get("days_ahead") or 30)
    end_date = add_days(today(), days_ahead)

    conditions = f"WHERE pr.status IN ('Due','Contacted','Grace Period') AND pr.renewal_due_date <= '{end_date}'"
    if filters.get("agent"):
        conditions += f" AND pr.agent = '{filters.get('agent')}'"
    if filters.get("priority"):
        conditions += f" AND pr.priority = '{filters.get('priority')}'"

    data = frappe.db.sql(
        f"""
        SELECT pr.name, pr.policy, pr.customer, pr.agent,
               pr.renewal_due_date, pr.renewal_amount, pr.priority,
               pr.status, pr.contact_date,
               DATEDIFF(pr.renewal_due_date, CURDATE()) as days_left
        FROM `tabPolicy Renewal` pr
        {conditions}
        ORDER BY pr.renewal_due_date ASC
        """,
        as_dict=True,
    )
    return columns, data
