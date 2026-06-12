/**
 * Insurance Agent Management — Global JS
 * Loaded on every desk page.
 */

// ── Global utility to render AI Score badge ────────────────────────────────
window.renderAIScore = function (score) {
    if (score === undefined || score === null) return "—";
    const cls = score >= 70 ? "ai-score-high" : score >= 40 ? "ai-score-medium" : "ai-score-low";
    const label = score >= 70 ? "High" : score >= 40 ? "Medium" : "Low";
    return `<span class="ai-score-badge ${cls}">${score} (${label})</span>`;
};

// ── List View customizations ───────────────────────────────────────────────
frappe.listview_settings["Insurance Lead"] = {
    add_fields: ["ai_score", "status", "priority", "assigned_agent"],
    get_indicator(doc) {
        const map = {
            "New": "blue", "Contacted": "cyan", "Follow-up": "orange",
            "Qualified": "green", "Proposal Sent": "purple",
            "Converted": "green", "Not Interested": "grey", "Lost": "red",
        };
        return [doc.status, map[doc.status] || "grey", "status,=," + doc.status];
    },
    formatters: {
        ai_score(value) {
            return renderAIScore(value);
        },
    },
};

frappe.listview_settings["Insurance Policy"] = {
    add_fields: ["policy_status", "premium_amount", "next_premium_date"],
    get_indicator(doc) {
        const map = {
            "Active": "green", "Lapsed": "red", "Surrendered": "orange",
            "Matured": "blue", "Claimed": "purple", "Proposal": "grey",
        };
        return [doc.policy_status, map[doc.policy_status] || "grey", "policy_status,=," + doc.policy_status];
    },
};

frappe.listview_settings["Policy Renewal"] = {
    add_fields: ["status", "priority", "renewal_due_date"],
    get_indicator(doc) {
        const map = {
            "Due": "red", "Contacted": "orange",
            "Renewed": "green", "Lapsed": "grey", "Grace Period": "yellow",
        };
        return [doc.status, map[doc.status] || "grey", "status,=," + doc.status];
    },
};

frappe.listview_settings["Agent Commission"] = {
    add_fields: ["payment_status", "commission_amount"],
    get_indicator(doc) {
        const map = { "Pending": "orange", "Paid": "green", "Held": "red" };
        return [doc.payment_status, map[doc.payment_status] || "grey", "payment_status,=," + doc.payment_status];
    },
};
