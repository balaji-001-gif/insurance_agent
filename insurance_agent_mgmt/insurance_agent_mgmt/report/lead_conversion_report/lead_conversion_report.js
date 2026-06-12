frappe.query_reports["Lead Conversion Report"] = {
    filters: [
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            default: frappe.datetime.add_months(frappe.datetime.now_date(), -1),
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            default: frappe.datetime.now_date(),
        },
        {
            fieldname: "agent",
            label: __("Agent"),
            fieldtype: "Link",
            options: "Insurance Agent",
        },
    ],
};
