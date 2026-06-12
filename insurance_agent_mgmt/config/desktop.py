# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from frappe import _


def get_data():
    return [
        {
            "module_name": "Insurance Agent Mgmt",
            "category": "Modules",
            "label": _("Insurance Management"),
            "color": "#5e64ff",
            "icon": "octicon octicon-shield",
            "type": "module",
            "description": "Manage insurance leads, customers, policies, and agents.",
        }
    ]
