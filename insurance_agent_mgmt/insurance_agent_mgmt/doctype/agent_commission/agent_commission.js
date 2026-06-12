frappe.ui.form.on("Agent Commission", {
    refresh(frm) {
        const statusColors = { "Pending": "orange", "Paid": "green", "Held": "red" };
        if (frm.doc.payment_status) {
            frm.dashboard.add_indicator(`Status: ${frm.doc.payment_status}`, statusColors[frm.doc.payment_status] || "grey");
        }
    },

    commission_amount(frm) {
        if (frm.doc.tds_rate && frm.doc.commission_amount) {
            const tds = frm.doc.commission_amount * frm.doc.tds_rate / 100;
            frm.set_value("tds_amount", tds);
            frm.set_value("net_commission", frm.doc.commission_amount - tds);
        }
    },

    tds_rate(frm) {
        if (frm.doc.commission_amount && frm.doc.tds_rate) {
            const tds = frm.doc.commission_amount * frm.doc.tds_rate / 100;
            frm.set_value("tds_amount", tds);
            frm.set_value("net_commission", frm.doc.commission_amount - tds);
        }
    },
});
