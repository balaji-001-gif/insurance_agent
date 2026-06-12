# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import frappe
from frappe.model.document import Document


class InsuranceAgent(Document):

    def validate(self):
        self.validate_user_link()

    def validate_user_link(self):
        if self.user:
            existing = frappe.db.get_value(
                "Insurance Agent",
                {"user": self.user, "name": ("!=", self.name)},
                "name",
            )
            if existing:
                frappe.throw(
                    frappe._(
                        "User {0} is already linked to agent {1}"
                    ).format(self.user, existing)
                )

    def on_update(self):
        self.update_user_roles()

    def update_user_roles(self):
        if self.user:
            user = frappe.get_doc("User", self.user)
            roles = [r.role for r in user.roles]
            if "Insurance Agent" not in roles:
                user.add_roles("Insurance Agent")
