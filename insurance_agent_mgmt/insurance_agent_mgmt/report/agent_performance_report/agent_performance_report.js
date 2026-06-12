frappe.query_reports["Agent Performance Report"] = {
    filters: [
        {
            fieldname: "agent",
            label: __("Agent"),
            fieldtype: "Link",
            options: "Insurance Agent",
        },
    ],
};
