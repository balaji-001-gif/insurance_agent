# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from frappe.model.document import Document
from frappe.utils import flt


class AgentCommission(Document):

    def validate(self):
        self.calculate_tds()

    def calculate_tds(self):
        if self.tds_rate and self.commission_amount:
            self.tds_amount = flt(self.commission_amount) * flt(self.tds_rate) / 100
            self.net_commission = flt(self.commission_amount) - flt(self.tds_amount)
        else:
            self.net_commission = flt(self.commission_amount)
