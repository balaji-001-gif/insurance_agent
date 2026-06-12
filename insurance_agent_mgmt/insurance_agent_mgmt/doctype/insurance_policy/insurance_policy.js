frappe.ui.form.on("Insurance Policy", {
    refresh(frm) {
        const statusColors = {
            "Active": "green", "Lapsed": "red", "Surrendered": "orange",
            "Matured": "blue", "Claimed": "purple", "Proposal": "grey",
        };
        frm.dashboard.add_indicator(
            `Status: ${frm.doc.policy_status}`,
            statusColors[frm.doc.policy_status] || "grey"
        );

        if (!frm.doc.__islocal && frm.doc.docstatus === 1) {
            frm.add_custom_button(__("Record Premium Payment"), () => {
                frappe.new_doc("Premium Payment", {
                    policy: frm.doc.name,
                    customer: frm.doc.customer,
                    agent: frm.doc.agent,
                    amount: frm.doc.premium_amount,
                    due_date: frm.doc.next_premium_date,
                });
            }, __("Actions"));
        }
    },

    insurance_product(frm) {
        if (frm.doc.insurance_product) {
            frappe.db.get_value("Insurance Product", frm.doc.insurance_product,
                ["commission_rate", "premium_frequency", "min_policy_term"],
                (r) => {
                    if (r) {
                        if (!frm.doc.premium_frequency) frm.set_value("premium_frequency", r.premium_frequency);
                        if (!frm.doc.policy_term) frm.set_value("policy_term", r.min_policy_term);
                    }
                }
            );
        }
    },

    commencement_date(frm) {
        if (frm.doc.commencement_date && frm.doc.premium_frequency) {
            const freqDays = { Monthly: 30, Quarterly: 90, "Half-Yearly": 180, Yearly: 365 };
            const days = freqDays[frm.doc.premium_frequency];
            if (days) {
                frm.set_value("next_premium_date",
                    frappe.datetime.add_days(frm.doc.commencement_date, days));
            }
        }
    },
});
