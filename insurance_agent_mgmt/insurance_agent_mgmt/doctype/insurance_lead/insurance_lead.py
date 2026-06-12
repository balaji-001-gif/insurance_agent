# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document


class InsuranceLead(Document):

    def validate(self):
        self.validate_duplicate_mobile()
        self.validate_converted_status()

    def validate_duplicate_mobile(self):
        if self.mobile_no:
            existing = frappe.db.get_value(
                "Insurance Lead",
                {"mobile_no": self.mobile_no, "name": ("!=", self.name)},
                "name",
            )
            if existing:
                frappe.throw(
                    _("Lead with mobile {0} already exists: {1}").format(self.mobile_no, existing)
                )

    def validate_converted_status(self):
        if self.status == "Converted":
            customer = frappe.db.exists(
                "Insurance Customer", {"lead": self.name}
            )
            if not customer:
                frappe.throw(
                    _(
                        "Cannot set status to Converted without creating a Customer. "
                        "Use the 'Convert to Customer' button."
                    )
                )

    def after_insert(self):
        # Auto assign to current agent if user is an agent
        if not self.assigned_agent:
            from insurance_agent_mgmt.utils import get_current_agent
            agent = get_current_agent()
            if agent:
                self.db_set("assigned_agent", agent)
