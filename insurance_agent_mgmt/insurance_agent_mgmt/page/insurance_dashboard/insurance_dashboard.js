frappe.pages["insurance-dashboard"].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: "Insurance Dashboard",
        single_column: true,
    });

    $(wrapper).find(".page-content").html(
        frappe.render_template("insurance_dashboard", {})
    );

    loadDashboard();
};

function loadDashboard() {
    // Load KPIs
    frappe.call({
        method: "insurance_agent_mgmt.utils.get_dashboard_stats",
        callback(r) {
            if (!r.message) return;
            const d = r.message;
            renderKPI("card-leads-total", "Total Leads", d.leads_total, "blue", "users");
            renderKPI("card-conversion", "Conversion Rate", `${d.conversion_rate}%`, "green", "trending-up");
            renderKPI("card-active-policies", "Active Policies", d.policies_active, "purple", "shield");
            renderKPI("card-premium", "Premium This Month", `₹${frappe.format(d.premium_this_month, {fieldtype:"Currency"})}`, "teal", "dollar-sign");
            renderKPI("card-renewals", "Renewals Due (30d)", d.renewals_due, "orange", "refresh-cw");
            renderKPI("card-commission", "Pending Commission", `₹${frappe.format(d.commission_pending, {fieldtype:"Currency"})}`, "yellow", "credit-card");
            renderKPI("card-new-leads", "New Leads", d.leads_new, "blue", "user-plus");
            renderKPI("card-rate", "Converted", d.leads_converted, "green", "check-circle");
        },
    });

    // Monthly Chart
    frappe.call({
        method: "insurance_agent_mgmt.api.get_monthly_trends",
        callback(r) {
            if (!r.message) return;
            const labels = r.message.map(d => d.month_name);
            const values = r.message.map(d => d.total);
            new frappe.Chart("#chart-monthly", {
                type: "line",
                data: {
                    labels,
                    datasets: [{ name: "Premium", values, chartType: "line" }],
                },
                colors: ["#5e64ff"],
                height: 280,
            });
        },
    });

    // Lead Funnel
    frappe.call({
        method: "insurance_agent_mgmt.api.get_lead_funnel",
        callback(r) {
            if (!r.message) return;
            const labels = r.message.map(d => d.status);
            const values = r.message.map(d => d.count);
            new frappe.Chart("#chart-funnel", {
                type: "pie",
                data: { labels, datasets: [{ values }] },
                colors: ["#5e64ff","#36a2eb","#ffce56","#4bc0c0","#28a745","#ff6384","#6c757d","#dc3545"],
                height: 280,
            });
        },
    });

    // Leaderboard
    frappe.call({
        method: "insurance_agent_mgmt.api.get_agent_leaderboard",
        args: { period: "monthly" },
        callback(r) {
            if (!r.message) return;
            let html = `<table class="table table-sm table-hover">
                <thead class="thead-light"><tr>
                    <th>#</th><th>Agent</th><th>Policies</th>
                    <th>Premium Collected</th><th>Achievement</th>
                </tr></thead><tbody>`;
            r.message.forEach((a, i) => {
                const pct = a.achievement_pct || 0;
                const color = pct >= 100 ? "success" : pct >= 60 ? "warning" : "danger";
                html += `<tr>
                    <td><b>${i + 1}</b></td>
                    <td><a href="/app/insurance-agent/${a.agent}">${a.agent_name}</a></td>
                    <td>${a.policies_count}</td>
                    <td>₹${frappe.format(a.total_premium, {fieldtype:"Currency"})}</td>
                    <td>
                        <div class="progress" style="height:18px;">
                            <div class="progress-bar bg-${color}" style="width:${Math.min(pct,100)}%">
                                ${pct}%
                            </div>
                        </div>
                    </td>
                </tr>`;
            });
            html += "</tbody></table>";
            $("#leaderboard-table").html(html);
        },
    });
}

function renderKPI(id, label, value, color, icon) {
    const colorMap = {
        blue: "#5e64ff", green: "#28a745", purple: "#6f42c1",
        teal: "#20c997", orange: "#fd7e14", yellow: "#ffc107",
    };
    const bg = colorMap[color] || "#5e64ff";
    $(`#${id}`).html(`
        <div class="card shadow-sm border-0" style="border-left: 4px solid ${bg} !important;">
            <div class="card-body py-3">
                <div class="text-muted small">${label}</div>
                <div class="h4 mb-0 font-weight-bold" style="color:${bg}">${value}</div>
            </div>
        </div>
    `);
}
