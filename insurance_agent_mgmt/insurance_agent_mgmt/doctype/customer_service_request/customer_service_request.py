# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document


class CustomerServiceRequest(Document):
    """Tracks insurance service requests: nominee change, address change, contact updates, etc.
    
    - On submit: sets status to "In Progress"
    - On approval: if service_type is Nominee Change or Address Change, auto-applies the change
      to the linked Insurance Policy / Customer record
    - On cancel: sets status to "Cancelled"
    """

    def validate(self):
        self.validate_request()
        self.validate_auto_apply()
        self.populate_current_nominees()

    def validate_request(self):
        if self.request_status == "Completed" and not self.resolution_date:
            self.resolution_date = frappe.utils.today()

    def validate_auto_apply(self):
        """When status changes to Approved, auto-apply the change to the relevant doctype."""
        if self.has_value_changed("request_status") and self.request_status == "Approved":
            self._apply_service_change()

    def populate_current_nominees(self):
        """Pre-populate the proposed_nominees child table from the policy's current nominees.
        Only runs for new documents when service_type is Nominee Change.
        """
        if not self.is_new():
            return
        if self.service_type != "Nominee Change":
            return
        if not self.insurance_policy:
            return
        if self.proposed_nominees:
            return  # Already populated

        policy = frappe.get_doc("Insurance Policy", self.insurance_policy)
        if policy.policy_nominees:
            for nominee in policy.policy_nominees:
                self.append("proposed_nominees", {
                    "nominee_name": nominee.nominee_name,
                    "nominee_relation": nominee.nominee_relation,
                    "nominee_dob": nominee.nominee_dob,
                    "nominee_share": nominee.nominee_share,
                    "nominee_mobile": nominee.nominee_mobile,
                    "guardian_name": nominee.guardian_name,
                    "is_minor": nominee.is_minor,
                    "action": "Update" if nominee.nominee_name else "Add",
                })

    def _apply_service_change(self):
        """Apply the requested change to the policy or customer record."""
        if not self.insurance_policy:
            return

        if self.service_type == "Nominee Change":
            self._apply_nominee_change()
        elif self.service_type == "Address Change":
            self._apply_address_change()
        elif self.service_type == "Contact Update":
            self._apply_contact_update()
        elif self.service_type == "KYC Update":
            self._apply_kyc_update()

    def _apply_nominee_change(self):
        """Update the policy_nominees child table on the linked insurance policy
        based on the proposed_nominees data from this service request.
        
        Actions supported:
        - Add:     Appends a new nominee row
        - Update:  Updates matching nominee in the table
        - Remove:  Deletes the matching nominee row
        """
        if not self.proposed_nominees or not self.insurance_policy:
            return

        policy = frappe.get_doc("Insurance Policy", self.insurance_policy)
        old_nominees = [
            {"name": n.nominee_name, "relation": n.nominee_relation, "share": n.nominee_share}
            for n in (policy.policy_nominees or [])
        ]

        # Process each proposed nominee action
        for proposed in self.proposed_nominees:
            action = (proposed.action or "Add").strip()

            if action == "Remove":
                # Remove matching nominee by name
                policy.policy_nominees = [
                    n for n in (policy.policy_nominees or [])
                    if n.nominee_name != proposed.nominee_name
                ]

            elif action == "Update":
                # Update matching nominee by name
                for existing in (policy.policy_nominees or []):
                    if existing.nominee_name == proposed.nominee_name:
                        existing.nominee_relation = proposed.nominee_relation
                        existing.nominee_dob = proposed.nominee_dob
                        existing.nominee_share = proposed.nominee_share
                        existing.nominee_mobile = proposed.nominee_mobile
                        existing.guardian_name = proposed.guardian_name
                        existing.is_minor = proposed.is_minor
                        break

            else:  # "Add" (default)
                policy.append("policy_nominees", {
                    "nominee_name": proposed.nominee_name,
                    "nominee_relation": proposed.nominee_relation,
                    "nominee_dob": proposed.nominee_dob,
                    "nominee_share": proposed.nominee_share,
                    "nominee_mobile": proposed.nominee_mobile,
                    "guardian_name": proposed.guardian_name,
                    "is_minor": proposed.is_minor,
                })

        # Add remarks noting the change
        old_summary = "; ".join([f"{n['name']} ({n['relation']}, {n['share']}%)" for n in old_nominees]) or "None"
        new_remark = _("\nNominees updated via Service Request {0}. Previous nominees: {1}").format(
            self.name, old_summary
        )
        policy.remarks = (policy.remarks or "") + new_remark
        policy.flags.ignore_permissions = True
        policy.flags.ignore_validate = True
        policy.save()

    def _apply_address_change(self):
        """Update address on the linked customer record."""
        if self.requested_value and self.customer:
            frappe.db.set_value("Insurance Customer", self.customer, {
                "address": self.requested_value,
                "remarks": _("Address updated via Service Request {0}").format(self.name)
            })

    def _apply_contact_update(self):
        """Update contact info on the customer record."""
        if self.requested_value and self.customer:
            lines = self.requested_value.strip().split("\n")
            updates = {}
            for line in lines:
                if ":" in line:
                    key, val = line.split(":", 1)
                    key = key.strip().lower()
                    val = val.strip()
                    if "mobile" in key or "phone" in key:
                        updates["mobile_no"] = val
                    elif "email" in key:
                        updates["email_id"] = val
            if updates:
                frappe.db.set_value("Insurance Customer", self.customer, updates)

    def _apply_kyc_update(self):
        """Update KYC info on the customer record."""
        if self.customer:
            frappe.db.set_value("Insurance Customer", self.customer, {
                "kyc_status": "Submitted"
            })

    def on_submit(self):
        if self.request_status == "Open":
            self.db_set("request_status", "In Progress")

    def on_cancel(self):
        self.db_set("request_status", "Cancelled")
