"""
Ensure permissions for new doctypes (Customer Service Request)
are properly applied in the Frappe database.

Child tables (Policy Nominee, Health Dependency, Premium Schedule Item,
Service Request Nominee) are istable=1 and inherit permissions from
their parent doctypes, so they do not need explicit permission records.
"""
import frappe
from frappe.permissions import add_permission, update_permission_property


NEW_DOCTYPES = [
    "Customer Service Request",
]

ROLES = {
    "Insurance Admin": {
        "select": 1, "read": 1, "write": 1, "create": 1,
        "delete": 1, "submit": 1, "cancel": 1, "amend": 1,
        "email": 1, "print": 1, "export": 1, "report": 1, "share": 1,
    },
    "Insurance Manager": {
        "select": 1, "read": 1, "write": 1, "create": 1,
        "delete": 0, "submit": 1, "cancel": 1, "amend": 0,
        "email": 1, "print": 1, "export": 0, "report": 1, "share": 1,
    },
    "Insurance Agent": {
        "select": 1, "read": 1, "write": 1, "create": 1,
        "delete": 0, "submit": 1, "cancel": 0, "amend": 0,
        "email": 1, "print": 1, "export": 0, "report": 1, "share": 1,
    },
}


def execute():
    """Apply permissions for all new doctypes."""
    for doctype in NEW_DOCTYPES:
        _apply_doctype_permissions(doctype)

    frappe.db.commit()
    print(f"Permissions applied for: {', '.join(NEW_DOCTYPES)}")


def _apply_doctype_permissions(doctype):
    """Apply standard role permissions for a doctype."""
    for role, perms in ROLES.items():
        if not frappe.db.exists("Role", role):
            print(f"  Skipping '{role}' — role does not exist")
            continue

        # Add the permission record if it doesn't exist
        add_permission(doctype, role, permlevel=0)

        # Set each permission property
        for prop, value in perms.items():
            update_permission_property(doctype, role, 0, prop, value)

        print(f"  {role} permissions set for {doctype}")
