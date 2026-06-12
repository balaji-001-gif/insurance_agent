frappe.ui.form.on("Follow Up Activity", {
    refresh(frm) {
        const statusColors = {
            "Planned": "blue", "Completed": "green",
            "Cancelled": "red", "Rescheduled": "orange",
        };
        if (frm.doc.status) {
            frm.dashboard.add_indicator(`Status: ${frm.doc.status}`, statusColors[frm.doc.status] || "grey");
        }
    },
});
