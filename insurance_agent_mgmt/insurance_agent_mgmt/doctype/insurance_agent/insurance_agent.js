frappe.ui.form.on("Insurance Agent", {
    refresh(frm) {
        // Dashboard buttons
        frm.add_custom_button(__("View My Leads"), () => {
            frappe.set_route("List", "Insurance Lead", {
                assigned_agent: frm.doc.name,
            });
        }, __("Actions"));

        frm.add_custom_button(__("View Policies"), () => {
            frappe.set_route("List", "Insurance Policy", {
                agent: frm.doc.name,
            });
        }, __("Actions"));

        frm.add_custom_button(__("Commission Statement"), () => {
            frappe.set_route("query-report", "Commission Summary Report", {
                agent: frm.doc.name,
            });
        }, __("Reports"));

        // Performance indicator
        if (frm.doc.target_premium && frm.doc.achieved_premium) {
            const pct = ((frm.doc.achieved_premium / frm.doc.target_premium) * 100).toFixed(1);
            frm.dashboard.add_indicator(
                `Achievement: ${pct}%`,
                pct >= 100 ? "green" : pct >= 60 ? "orange" : "red"
            );
        }

        // License expiry warning
        if (frm.doc.license_expiry) {
            const expiry = frappe.datetime.str_to_obj(frm.doc.license_expiry);
            const today = new Date();
            const daysLeft = Math.ceil((expiry - today) / (1000 * 60 * 60 * 24));
            if (daysLeft < 30) {
                frm.dashboard.add_indicator(
                    `License expires in ${daysLeft} days`,
                    daysLeft < 0 ? "red" : "orange"
                );
            }
        }
    },
});
