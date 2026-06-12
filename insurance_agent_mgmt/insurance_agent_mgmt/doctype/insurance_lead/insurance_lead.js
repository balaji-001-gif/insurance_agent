frappe.ui.form.on("Insurance Lead", {
    refresh(frm) {
        // AI Score color indicator
        if (frm.doc.ai_score !== undefined) {
            const score = frm.doc.ai_score;
            const color = score >= 70 ? "green" : score >= 40 ? "orange" : "red";
            const label = score >= 70 ? "High Priority" : score >= 40 ? "Medium" : "Low Priority";
            frm.dashboard.add_indicator(`AI Score: ${score} — ${label}`, color);
        }

        // Convert to Customer button
        if (frm.doc.status !== "Converted" && !frm.doc.__islocal) {
            frm.add_custom_button(__("Convert to Customer"), () => {
                frappe.confirm(
                    __(`Convert <b>${frm.doc.lead_name}</b> to a Customer?`),
                    () => {
                        frappe.call({
                            method: "insurance_agent_mgmt.api.convert_lead_to_customer",
                            args: { lead_name: frm.doc.name },
                            callback(r) {
                                if (r.message) {
                                    frappe.show_alert({
                                        message: __(`Customer ${r.message.customer} created!`),
                                        indicator: "green",
                                    });
                                    frm.reload_doc();
                                }
                            },
                        });
                    }
                );
            }, __("Actions"));
        }

        // Log Follow Up
        frm.add_custom_button(__("Log Follow Up"), () => {
            const d = new frappe.ui.Dialog({
                title: __("Log Follow Up Activity"),
                fields: [
                    { fieldtype: "Select", fieldname: "activity_type", label: "Activity Type",
                      options: "Call\nMeeting\nEmail\nWhatsApp\nVisit", reqd: 1 },
                    { fieldtype: "Data", fieldname: "subject", label: "Subject", reqd: 1 },
                    { fieldtype: "Small Text", fieldname: "outcome", label: "Outcome" },
                    { fieldtype: "Date", fieldname: "next_follow_up_date", label: "Next Follow Up Date" },
                ],
                primary_action_label: __("Save"),
                primary_action(values) {
                    frappe.db.insert({
                        doctype: "Follow Up Activity",
                        lead: frm.doc.name,
                        agent: frm.doc.assigned_agent,
                        activity_date: frappe.datetime.now_date(),
                        activity_type: values.activity_type,
                        subject: values.subject,
                        outcome: values.outcome,
                        next_follow_up_date: values.next_follow_up_date,
                        status: "Completed",
                    }).then(() => {
                        frappe.show_alert({ message: __("Activity logged!"), indicator: "green" });
                        if (values.next_follow_up_date) {
                            frappe.db.set_value("Insurance Lead", frm.doc.name,
                                "next_follow_up_date", values.next_follow_up_date);
                        }
                        frm.reload_doc();
                        d.hide();
                    });
                },
            });
            d.show();
        }, __("Actions"));

        // Timeline button
        frm.add_custom_button(__("Activity Timeline"), () => {
            frappe.call({
                method: "insurance_agent_mgmt.api.get_lead_timeline",
                args: { lead_name: frm.doc.name },
                callback(r) {
                    if (!r.message || !r.message.length) {
                        frappe.msgprint(__("No activities recorded yet."));
                        return;
                    }
                    let html = `<table class="table table-bordered table-sm">
                        <thead><tr>
                            <th>Date</th><th>Type</th><th>Subject</th><th>Outcome</th>
                        </tr></thead><tbody>`;
                    r.message.forEach(a => {
                        html += `<tr>
                            <td>${a.activity_date}</td>
                            <td>${a.activity_type}</td>
                            <td>${a.subject || ""}</td>
                            <td>${a.outcome || ""}</td>
                        </tr>`;
                    });
                    html += "</tbody></table>";
                    frappe.msgprint({ title: __("Activity Timeline"), message: html, wide: true });
                },
            });
        });
    },

    annual_income(frm) {
        // Re-trigger AI scoring hint
        if (frm.doc.annual_income > 0) {
            frm.dashboard.add_indicator("AI score will update on save", "blue");
        }
    },

    status(frm) {
        if (frm.doc.status === "Converted") {
            frappe.msgprint(__("Use the 'Convert to Customer' button to convert this lead."), "Warning");
            frm.set_value("status", frm.doc.__unsaved ? "Qualified" : frm.doc.status);
        }
    },
});
