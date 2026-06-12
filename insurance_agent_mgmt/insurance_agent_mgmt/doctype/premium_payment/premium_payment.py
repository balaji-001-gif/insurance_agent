# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import frappe
from frappe.model.document import Document


class PremiumPayment(Document):

    def validate(self):
        if self.amount <= 0:
            frappe.throw(frappe._("Payment amount must be greater than zero."))

    def on_submit(self):
        self.db_set("status", "Paid")
