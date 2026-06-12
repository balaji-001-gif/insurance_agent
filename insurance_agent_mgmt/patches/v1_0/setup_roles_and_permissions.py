"""
Create Insurance-specific roles if they don't exist.
"""
import frappe


def execute():
    roles = [
        {"role_name": "Insurance Admin", "desk_access": 1},
        {"role_name": "Insurance Manager", "desk_access": 1},
        {"role_name": "Insurance Agent", "desk_access": 1},
    ]

    for r in roles:
        if not frappe.db.exists("Role", r["role_name"]):
            doc = frappe.get_doc({"doctype": "Role", **r})
            doc.insert(ignore_permissions=True)

    frappe.db.commit()
