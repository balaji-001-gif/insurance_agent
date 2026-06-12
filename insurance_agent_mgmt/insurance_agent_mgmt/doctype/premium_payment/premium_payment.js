frappe.ui.form.on("Premium Payment", {
    refresh(frm) {
        if (frm.doc.status) {
            const colors = { "Pending": "orange", "Paid": "green", "Failed": "red", "Refunded": "grey" };
            frm.dashboard.add_indicator(`Status: ${frm.doc.status}`, colors[frm.doc.status] || "grey");
        }
    },
});
