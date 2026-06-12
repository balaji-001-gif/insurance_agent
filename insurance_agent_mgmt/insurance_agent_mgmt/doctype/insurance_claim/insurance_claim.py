# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document


class InsuranceClaim(Document):
    """Insurance Claim record linked to an Insurance Policy and Customer.
    
    - On submit: sets status to "Under Review"
    - On cancel: sets status to "Closed"
    - The provider push hook (push_claim_to_provider) is registered in hooks.py
    """

    def validate(self):
        self.validate_amounts()

    def validate_amounts(self):
        if self.claim_amount and self.claim_amount <= 0:
            frappe.throw(_("Claimed Amount must be greater than zero."))
        if self.approved_amount and self.approved_amount > self.claim_amount:
            frappe.throw(
                _("Approved Amount ({0}) cannot exceed Claimed Amount ({1}).")
                .format(self.approved_amount, self.claim_amount)
            )

    def on_submit(self):
        self.db_set("claim_status", "Submitted")

    def on_cancel(self):
        self.db_set("claim_status", "Closed")
