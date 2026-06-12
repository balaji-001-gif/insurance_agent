frappe.ui.form.on("Insurance Customer", {
    refresh(frm) {
        if (!frm.doc.__islocal) {
            frm.add_custom_button(__("New Policy"), () => {
                frappe.new_doc("Insurance Policy", {
                    customer: frm.doc.name,
                    agent: frm.doc.assigned_agent,
                });
            }, __("Actions"));

            frm.add_custom_button(__("Policy Summary"), () => {
                frappe.call({
                    method: "insurance_agent_mgmt.api.get_policy_summary",
                    args: { customer_name: frm.doc.name },
                    callback(r) {
                        if (!r.message || !r.message.length) {
                            frappe.msgprint(__("No policies found for this customer."));
                            return;
                        }
                        let html = `<table class="table table-sm table-bordered">
                            <thead><tr>
                                <th>Policy No</th><th>Product</th><th>Status</th>
                                <th>Sum Assured</th><th>Premium</th><th>Next Due</th>
                            </tr></thead><tbody>`;
                        r.message.forEach(p => {
                            const statusColor = p.policy_status === "Active" ? "green" :
                                p.policy_status === "Lapsed" ? "red" : "orange";
                            html += `<tr>
                                <td><a href="/app/insurance-policy/${p.name}">${p.name}</a></td>
                                <td>${p.insurance_product || ""}</td>
                                <td><span class="indicator-pill ${statusColor}">${p.policy_status}</span></td>
                                <td>₹${frappe.format(p.sum_assured, {fieldtype:"Currency"})}</td>
                                <td>₹${frappe.format(p.premium_amount, {fieldtype:"Currency"})}</td>
                                <td>${p.next_premium_date || "—"}</td>
                            </tr>`;
                        });
                        html += "</tbody></table>";
                        frappe.msgprint({ title: __("Policy Summary"), message: html, wide: true });
                    },
                });
            });

            // KYC indicator
            const kycColors = {
                "Pending": "orange", "Submitted": "blue",
                "Verified": "green", "Rejected": "red",
            };
            frm.dashboard.add_indicator(
                `KYC: ${frm.doc.kyc_status}`,
                kycColors[frm.doc.kyc_status] || "grey"
            );
        }
    },
});
