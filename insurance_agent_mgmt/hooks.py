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
    "Insurance Policy": {
        "on_update": "insurance_agent_mgmt.provider_integration.push_policy_update_to_provider",
        "on_cancel": "insurance_agent_mgmt.provider_integration.push_policy_update_to_provider",
    },
    "Insurance Claim": {
        "on_submit": "insurance_agent_mgmt.provider_integration.push_claim_to_provider",
    },
}

# ---------------------------------------------
# Scheduled Tasks
# ---------------------------------------------
scheduler_events = {
    "daily": [
        "insurance_agent_mgmt.ai_engine.batch_score_leads",
        "insurance_agent_mgmt.renewal_automation.auto_create_policy_renewals",
        "insurance_agent_mgmt.renewal_automation.mark_lapsed_policies",
        "insurance_agent_mgmt.agent_digest.send_daily_agent_digest",
    ],
    "hourly": [
        "insurance_agent_mgmt.provider_integration.sync_all_providers",
    ],
    "weekly": [],
    "monthly": [],
}

# ---------------------------------------------
# Permissions
# ---------------------------------------------
has_permission = {
    "Insurance Lead":     "insurance_agent_mgmt.utils.has_permission",
    "Insurance Policy":   "insurance_agent_mgmt.utils.has_permission",
    "Insurance Customer": "insurance_agent_mgmt.utils.has_permission",
    "Premium Payment":    "insurance_agent_mgmt.utils.has_permission",
    "Agent Commission":   "insurance_agent_mgmt.utils.has_permission",
    "Insurance Claim":    "insurance_agent_mgmt.utils.has_permission",
}

# ---------------------------------------------
# Session
# ---------------------------------------------
on_session_creation = "insurance_agent_mgmt.utils.set_agent_session"

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
