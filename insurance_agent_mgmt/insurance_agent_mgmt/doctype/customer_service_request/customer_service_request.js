frappe.ui.form.on("Customer Service Request", {
    refresh(frm) {
        const statusColors = {
            "Open": "grey",
            "In Progress": "blue",
            "Pending Documents": "orange",
            "Approved": "green",
            "Rejected": "red",
            "Completed": "purple",
            "Cancelled": "darkgrey",
        };
        frm.dashboard.add_indicator(
            `Status: ${frm.doc.request_status}`,
            statusColors[frm.doc.request_status] || "grey"
        );

        // Add action buttons
        if (!frm.doc.__islocal && frm.doc.docstatus === 1 && frm.doc.request_status === "In Progress") {
            frm.add_custom_button(__("Mark Approved"), () => {
                frm.set_value("request_status", "Approved");
                frm.set_value("resolution_date", frappe.datetime.get_today());
                frm.save();
            }, __("Status"));

            frm.add_custom_button(__("Mark Completed"), () => {
                frm.set_value("request_status", "Completed");
                frm.set_value("resolution_date", frappe.datetime.get_today());
                frm.save();
            }, __("Status"));
        }
    },

    service_type(frm) {
        // Pre-populate current values based on service type
        const hasPolicy = frm.doc.insurance_policy;
        const hasCustomer = frm.doc.customer;

        if (frm.doc.service_type && hasPolicy && hasCustomer) {
            frappe.call({
                method: "frappe.client.get",
                args: {
                    doctype: "Insurance Policy",
                    name: frm.doc.insurance_policy,
                },
                callback(r) {
                    if (r.message) {
                        const policy = r.message;
                        if (frm.doc.service_type === "Nominee Change") {
                            // Build current nominee summary from policy_nominees child table
                            let nomineeSummary = "";
                            if (policy.policy_nominees && policy.policy_nominees.length > 0) {
                                nomineeSummary = policy.policy_nominees.map((n, i) =>
                                    `${i+1}. ${n.nominee_name} (${n.nominee_relation || "N/A"}, ${n.nominee_share || 100}%)`
                                ).join("\n");
                            } else {
                                // Fallback to legacy fields
                                nomineeSummary = `Current Nominee: ${policy.nominee_name || "Not set"}\n` +
                                    `Relation: ${policy.nominee_relation || "N/A"}\n` +
                                    `Share: ${policy.nominee_share || 100}%`;
                            }
                            frm.set_value("current_value", nomineeSummary);
                        } else if (frm.doc.service_type === "Address Change") {
                            frappe.call({
                                method: "frappe.client.get",
                                args: { doctype: "Insurance Customer", name: frm.doc.customer },
                                callback(rc) {
                                    if (rc.message) {
                                        frm.set_value("current_value",
                                            `Address: ${rc.message.address || "Not set"}\n` +
                                            `City: ${rc.message.city || ""}\n` +
                                            `State: ${rc.message.state || ""}\n` +
                                            `Pincode: ${rc.message.pincode || ""}`
                                        );
                                    }
                                }
                            });
                        } else if (frm.doc.service_type === "Contact Update") {
                            frappe.call({
                                method: "frappe.client.get",
                                args: { doctype: "Insurance Customer", name: frm.doc.customer },
                                callback(rc) {
                                    if (rc.message) {
                                        frm.set_value("current_value",
                                            `Mobile: ${rc.message.mobile_no || "Not set"}\n` +
                                            `Email: ${rc.message.email_id || "Not set"}`
                                        );
                                    }
                                }
                            });
                        }
                    }
                }
            });
        }

        // Show/hide relevant fields based on service type
        const isNomineeChange = frm.doc.service_type === "Nominee Change";

        frm.set_df_property("current_value", "label", isNomineeChange ? "Current Nominee Details" : "Current Value / Details");
        frm.set_df_property("nominee_change_section", "hidden", !isNomineeChange);
        frm.set_df_property("proposed_nominees", "hidden", !isNomineeChange);

        if (frm.doc.service_type === "Address Change") {
            frm.set_df_property("current_value", "label", "Current Address");
            frm.set_df_property("requested_value", "label", "New Address");
            frm.set_df_property("requested_value", "description",
                "Enter full new address");
        } else if (frm.doc.service_type === "Contact Update") {
            frm.set_df_property("current_value", "label", "Current Contact Info");
            frm.set_df_property("requested_value", "label", "New Contact Info");
            frm.set_df_property("requested_value", "description",
                "Format: Mobile: xxx, Email: xxx");
        } else if (!isNomineeChange) {
            frm.set_df_property("requested_value", "label", "Requested / New Value");
            frm.set_df_property("requested_value", "description", "");
        }
    },

    insurance_policy(frm) {
        if (frm.doc.insurance_policy && frm.doc.service_type === "Nominee Change" && frm.doc.__islocal) {
            // Reload the current nominee context
            frm.trigger("service_type");
        }
    },

    refresh(frm) {
        // On form refresh, ensure nominee section visibility is correct
        if (frm.doc.service_type === "Nominee Change") {
            frm.set_df_property("nominee_change_section", "hidden", false);
            frm.set_df_property("proposed_nominees", "hidden", false);
        }
    },

    customer(frm) {
        if (frm.doc.customer) {
            frappe.db.get_value("Insurance Customer", frm.doc.customer, "customer_name", (r) => {
                if (r) frm.set_value("customer_name", r.customer_name);
            });
        }
    },
});
