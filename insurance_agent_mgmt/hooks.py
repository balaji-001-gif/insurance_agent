# -*- coding: utf-8 -*-
from __future__ import unicode_literals

app_name = "insurance_agent_mgmt"
app_title = "Insurance Agent Mgmt"
app_publisher = "Balaji"
app_description = "Insurance Agent Management for ERPNext V15+"
app_email = "admin@example.com"
app_license = "MIT"

# ---------------------------------------------
# DocType Class Overrides
# ---------------------------------------------
override_doctype_class = {}

# ---------------------------------------------
# Fixtures
# ---------------------------------------------
fixtures = [
    {"dt": "Workspace", "filters": [["module", "=", "Insurance Agent Mgmt"]]},
]

# ---------------------------------------------
# Document Events
# ---------------------------------------------
doc_events = {
    "Insurance Lead": {
        "validate": "insurance_agent_mgmt.ai_engine.score_lead",
    },
    "Premium Payment": {
        "on_submit": "insurance_agent_mgmt.api.create_agent_commission_on_payment",
        "on_cancel": "insurance_agent_mgmt.api.cancel_agent_commission_on_payment",
    },
}

# ---------------------------------------------
# Scheduled Tasks
# ---------------------------------------------
scheduler_events = {
    "daily": [
        "insurance_agent_mgmt.ai_engine.batch_score_leads",
    ],
    "hourly": [],
    "weekly": [],
    "monthly": [],
}

# ---------------------------------------------
# Permissions
# ---------------------------------------------
has_permission = {
    "Insurance Lead": "insurance_agent_mgmt.utils.has_permission",
    "Insurance Policy": "insurance_agent_mgmt.utils.has_permission",
    "Insurance Customer": "insurance_agent_mgmt.utils.has_permission",
    "Premium Payment": "insurance_agent_mgmt.utils.has_permission",
    "Agent Commission": "insurance_agent_mgmt.utils.has_permission",
}

# ---------------------------------------------
# Login
# ---------------------------------------------
on_login = "insurance_agent_mgmt.utils.set_agent_session"

# ---------------------------------------------
# Website Context
# ---------------------------------------------
website_context = {}

# ---------------------------------------------
# Jinja
# ---------------------------------------------
# jinja = {
#     "methods": [],
#     "filters": [],
# }
