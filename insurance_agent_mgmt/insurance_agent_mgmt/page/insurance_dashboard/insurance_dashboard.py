# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import frappe


@frappe.whitelist()
def get_stats():
    from insurance_agent_mgmt.utils import get_dashboard_stats
    return get_dashboard_stats()
