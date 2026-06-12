frappe.ui.form.on("Policy Renewal", {
    refresh(frm) {
        const statusColors = {
            "Due": "red", "Contacted": "orange",
            "Renewed": "green", "Lapsed": "grey", "Grace Period": "yellow",
        };
        if (frm.doc.status) {
            frm.dashboard.add_indicator(`Status: ${frm.doc.status}`, statusColors[frm.doc.status] || "grey");
        }
    },
});
