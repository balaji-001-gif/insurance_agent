# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import frappe
from frappe.model.document import Document


class ProviderAPIIntegration(Document):
    """Stores API connection configuration for external insurance providers
    (e.g., LIC India, HDFC Life, ICICI Prudential).
    
    - API base URL, auth credentials
    - Sync configuration (what to auto-sync, interval)
    - Sync status tracking
    """

    def validate(self):
        self.validate_api_url()
        self.validate_headers_json()

    def validate_api_url(self):
        if self.api_base_url and not self.api_base_url.startswith(("http://", "https://")):
            frappe.throw(frappe._("API Base URL must start with http:// or https://"))

    def validate_headers_json(self):
        if self.additional_headers:
            import json
            try:
                parsed = json.loads(self.additional_headers)
                if not isinstance(parsed, dict):
                    frappe.throw(frappe._("Additional Headers must be a valid JSON object"))
            except json.JSONDecodeError:
                frappe.throw(frappe._("Additional Headers must be valid JSON"))

    def mark_sync_started(self):
        """Mark the integration as being synced."""
        self.db_set({
            "last_sync_start": frappe.utils.now_datetime(),
            "last_sync_status": "In Progress",
        })

    def mark_sync_completed(self, status="Success", message="", log=None):
        """Mark sync as completed with result details."""
        self.db_set({
            "last_sync_end": frappe.utils.now_datetime(),
            "last_sync_status": status,
            "last_sync_message": message[:140] if message else "",
            "last_sync_log": frappe.as_json(log or {}, indent=2),
        })

    def get_decrypted_credentials(self):
        """Return decrypted API credentials as a dict."""
        return {
            "api_key": self.get_password("api_key") if self.api_key else None,
            "api_secret": self.get_password("api_secret") if self.api_secret else None,
            "access_token": self.get_password("access_token") if self.access_token else None,
        }
