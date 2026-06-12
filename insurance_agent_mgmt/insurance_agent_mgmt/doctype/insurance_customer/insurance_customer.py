# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import frappe
from frappe.model.document import Document


class InsuranceCustomer(Document):

    def autoname(self):
        from frappe.model.naming import make_autoname
        self.name = make_autoname("INS-CUST-.YYYY.-.#####")
        self.customer_code = self.name

    def validate(self):
        self.validate_pan()
        self.validate_aadhar()

    def validate_pan(self):
        import re
        if self.pan_number:
            if not re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$", self.pan_number.upper()):
                frappe.throw(frappe._("Invalid PAN number format. Expected: ABCDE1234F"))
            self.pan_number = self.pan_number.upper()

    def validate_aadhar(self):
        if self.aadhar_number:
            if len(str(self.aadhar_number).replace(" ", "")) != 12:
                frappe.throw(frappe._("Aadhaar number must be 12 digits."))
