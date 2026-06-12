# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import frappe
from frappe.model.document import Document
from frappe.utils import date_diff, today


class PolicyRenewal(Document):

    def validate(self):
        self.auto_set_priority()

    def auto_set_priority(self):
        if self.renewal_due_date:
            days_left = date_diff(self.renewal_due_date, today())
            if days_left <= 7:
                self.priority = "Critical"
            elif days_left <= 15:
                self.priority = "High"
            elif days_left <= 30:
                self.priority = "Medium"
            else:
                self.priority = "Low"
