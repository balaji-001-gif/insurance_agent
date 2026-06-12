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

    // Renewals Due This Week
    frappe.call({
        method: "insurance_agent_mgmt.api.get_renewals_this_week",
        callback(r) {
            if (!r.message || !r.message.length) {
                $("#renewals-week-table").html(`<p class="text-muted text-center py-3">✅ No renewals due this week</p>`);
                return;
            }
            let html = `<table class="table table-sm table-hover">
                <thead class="thead-light"><tr>
                    <th>Policy</th><th>Customer</th><th>Due Date</th>
                    <th>Amount</th><th>Days Left</th><th>Priority</th>
                </tr></thead><tbody>`;
            r.message.forEach(rn => {
                const days = rn.days_left;
                const color = days <= 0 ? "danger" : days <= 3 ? "warning" : "success";
                const priorityColors = {
                    "Critical": "red", "High": "orange",
                    "Medium": "blue", "Low": "grey",
                };
                const pColor = priorityColors[rn.priority] || "grey";
                html += `<tr>
                    <td><a href="/app/policy-renewal/${rn.name}">${rn.policy}</a></td>
                    <td>${rn.customer}</td>
                    <td>${rn.renewal_due_date}</td>
                    <td>₹${frappe.format(rn.renewal_amount || 0, {fieldtype:"Currency"})}</td>
                    <td><span class="indicator-pill ${color}">${days > 0 ? days + "d" : "Overdue"}</span></td>
                    <td><span class="indicator-pill ${pColor}">${rn.priority}</span></td>
                </tr>`;
            });
            html += "</tbody></table>";
            $("#renewals-week-table").html(html);
        },
    });

    // At-Risk Policies
    frappe.call({
        method: "insurance_agent_mgmt.api.get_at_risk_policies",
        callback(r) {
            if (!r.message || !r.message.length) {
                $("#at-risk-policies-table").html(`<p class="text-muted text-center py-3">✅ All policies are up to date on premiums</p>`);
                return;
            }

            // KPI header showing count and max severity
            const urgent = r.message.filter(p => p.days_overdue > 15).length;
            const warning = r.message.filter(p => p.days_overdue > 7 && p.days_overdue <= 15).length;
            const moderate = r.message.filter(p => p.days_overdue <= 7).length;
            let kpiHtml = `<div class="row mb-3">
                <div class="col-4 text-center">
                    <div class="text-muted small">Critical (>15d)</div>
                    <div class="h4 mb-0 font-weight-bold text-danger">${urgent}</div>
                </div>
                <div class="col-4 text-center">
                    <div class="text-muted small">Warning (8-15d)</div>
                    <div class="h4 mb-0 font-weight-bold text-warning">${warning}</div>
                </div>
                <div class="col-4 text-center">
                    <div class="text-muted small">Moderate (1-7d)</div>
                    <div class="h4 mb-0 font-weight-bold text-info">${moderate}</div>
                </div>
            </div><hr>`;

            let html = kpiHtml + `<table class="table table-sm table-hover">
                <thead class="thead-light"><tr>
                    <th>Policy</th><th>Customer</th><th>Product</th>
                    <th>Premium</th><th>Due Date</th><th>Days Overdue</th><th>Frequency</th>
                </tr></thead><tbody>`;
            r.message.forEach(p => {
                const days = p.days_overdue;
                const color = days > 15 ? "danger" : days > 7 ? "warning" : "info";
                const label = days > 15 ? "Critical" : days > 7 ? "At Risk" : "Past Due";
                html += `<tr>
                    <td><a href="/app/insurance-policy/${p.name}">${p.name}</a></td>
                    <td>${p.customer}</td>
                    <td>${p.insurance_product || "—"}</td>
                    <td>₹${frappe.format(p.premium_amount || 0, {fieldtype:"Currency"})}</td>
                    <td>${p.next_premium_date}</td>
                    <td><span class="indicator-pill ${color}">${days}d — ${label}</span></td>
                    <td>${p.premium_frequency}</td>
                </tr>`;
            });
            html += "</tbody></table>";
            $("#at-risk-policies-table").html(html);
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
