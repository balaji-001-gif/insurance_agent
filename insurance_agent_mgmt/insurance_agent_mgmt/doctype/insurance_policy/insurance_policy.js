frappe.ui.form.on("Insurance Policy", {
    refresh(frm) {
        const statusColors = {
            "Active": "green", "Lapsed": "red", "Surrendered": "orange",
            "Matured": "blue", "Claimed": "purple", "Proposal": "grey",
        };
        frm.dashboard.add_indicator(
            `Status: ${frm.doc.policy_status}`,
            statusColors[frm.doc.policy_status] || "grey"
        );

        if (!frm.doc.__islocal && frm.doc.docstatus === 1) {
            frm.add_custom_button(__("Record Premium Payment"), () => {
                frappe.new_doc("Premium Payment", {
                    policy: frm.doc.name,
                    customer: frm.doc.customer,
                    agent: frm.doc.agent,
                    amount: frm.doc.premium_amount,
                    due_date: frm.doc.next_premium_date,
                });
            }, __("Actions"));
        }

        // Show Service Request creation button
        if (!frm.doc.__islocal) {
            frm.add_custom_button(__("New Service Request"), () => {
                frappe.new_doc("Customer Service Request", {
                    customer: frm.doc.customer,
                    insurance_policy: frm.doc.name,
                });
            }, __("Actions"));
        }

        // Toggle dynamic field visibility based on product type
        if (frm.doc.insurance_product) {
            frappe.db.get_value("Insurance Product", frm.doc.insurance_product, "product_type", (r) => {
                toggle_fields_by_product_type(frm, r ? r.product_type : "");
            });
        } else {
            toggle_fields_by_product_type(frm, "");
        }
    },

    insurance_product(frm) {
        if (frm.doc.insurance_product) {
            frappe.db.get_value("Insurance Product", frm.doc.insurance_product,
                ["product_type", "premium_frequency", "min_policy_term",
                 "enable_auto_calculation", "base_sum_assured", "age_multiplier",
                 "min_sum_assured_auto", "max_sum_assured_auto", "calculation_formula"],
                (r) => {
                    if (r) {
                        if (!frm.doc.premium_frequency) frm.set_value("premium_frequency", r.premium_frequency);
                        if (!frm.doc.policy_term) frm.set_value("policy_term", r.min_policy_term);

                        // Auto-calculate sum assured if enabled
                        if (r.enable_auto_calculation && frm.doc.commencement_date && frm.doc.customer) {
                            frm.trigger("auto_calculate_sum_assured");
                        }

                        // Toggle fields based on product type
                        toggle_fields_by_product_type(frm, r.product_type || "");
                    }
                }
            );
        }
    },

    customer(frm) {
        if (frm.doc.customer && frm.doc.commencement_date) {
            frm.trigger("auto_calculate_sum_assured");
        }
    },

    regenerate_schedule(frm) {
        frm.call("regenerate_schedule").then(() => {
            frm.reload_doc();
            frappe.msgprint(__("Premium schedule regenerated successfully."));
        });
    },

    commencement_date(frm) {
        if (frm.doc.commencement_date && frm.doc.premium_frequency) {
            const freqDays = { Monthly: 30, Quarterly: 90, "Half-Yearly": 180, Yearly: 365 };
            const days = freqDays[frm.doc.premium_frequency];
            if (days) {
                frm.set_value("next_premium_date",
                    frappe.datetime.add_days(frm.doc.commencement_date, days));
            }
        }

        // Auto-calculate age and sum assured
        if (frm.doc.commencement_date && frm.doc.customer) {
            // Calculate age at commencement
            frappe.call({
                method: "frappe.client.get",
                args: {
                    doctype: "Insurance Customer",
                    name: frm.doc.customer,
                },
                callback(r) {
                    if (r.message && r.message.date_of_birth) {
                        const birth = frappe.datetime.str_to_obj(r.message.date_of_birth);
                        const comm = frappe.datetime.str_to_obj(frm.doc.commencement_date);
                        let age = comm.getFullYear() - birth.getFullYear();
                        const m = comm.getMonth() - birth.getMonth();
                        if (m < 0 || (m === 0 && comm.getDate() < birth.getDate())) age--;
                        frm.set_value("age_at_commencement", age);

                        // Auto-calculate sum assured
                        frm.trigger("auto_calculate_sum_assured");
                    }
                }
            });
        }
    },

    auto_calculate_sum_assured(frm) {
        if (!frm.doc.insurance_product || !frm.doc.age_at_commencement) return;

        frappe.db.get_value("Insurance Product", frm.doc.insurance_product,
            ["enable_auto_calculation", "base_sum_assured", "age_multiplier",
             "calculation_formula", "min_sum_assured_auto", "max_sum_assured_auto",
             "min_sum_assured", "product_type"],
            (r) => {
                if (!r || !r.enable_auto_calculation) return;

                const age = frm.doc.age_at_commencement;
                let calculated = 0;
                const base = r.base_sum_assured || 0;
                const multiplier = r.age_multiplier || 0;

                if (r.calculation_formula === "Base + (Age × Multiplier)") {
                    calculated = base + (age * multiplier);
                } else if (r.calculation_formula === "Base × Age") {
                    calculated = base * age;
                } else if (r.calculation_formula === "Fixed Amount") {
                    calculated = base;
                } else {
                    calculated = base;
                }

                // Apply min/max limits
                if (r.min_sum_assured_auto && calculated < r.min_sum_assured_auto) {
                    calculated = r.min_sum_assured_auto;
                }
                if (r.max_sum_assured_auto && calculated > r.max_sum_assured_auto) {
                    calculated = r.max_sum_assured_auto;
                }
                if (r.min_sum_assured && calculated < r.min_sum_assured) {
                    calculated = r.min_sum_assured;
                }

                frm.set_value("sum_assured", calculated);

                // Suggest premium based on product type
                const ptype = r.product_type || "";
                let rate = 0.05;
                if (ptype.indexOf("Health") !== -1) rate = 0.02;
                else if (ptype.indexOf("Vehicle") !== -1) rate = 0.03;
                else if (ptype.indexOf("Property") !== -1) rate = 0.01;
                const suggested = calculated * rate;
                if (!frm.doc.premium_amount) {
                    frm.set_value("premium_amount", suggested);
                }
            }
        );
    },
});

/**
 * Dynamically show/hide fields based on the insurance product type.
 * This implements the "dynamic fields based on insurance type" feature.
 */
function toggle_fields_by_product_type(frm, productType) {
    const ptype = productType || "";

    // Health Dependencies table: only visible for Health Insurance
    const isHealth = ptype === "Health Insurance";
    frm.set_df_property("section_health", "hidden", !isHealth);
    frm.set_df_property("health_dependencies", "hidden", !isHealth);

    // Additional detail fields by type
    const isVehicle = ptype === "Vehicle Insurance";
    const isProperty = ptype === "Property Insurance";
    const isLife = ptype === "Life Insurance" || ptype === "Term Insurance" || ptype === "ULIP" || ptype === "Pension Plan";

    frm.set_df_property("add_on_riders", "hidden", !isLife);
    frm.set_df_property("vehicle_details", "hidden", !isVehicle);
    frm.set_df_property("property_details", "hidden", !isProperty);

    // Show/hide the additional details section based on whether any type-specific fields exist
    const hasExtraFields = isHealth || isVehicle || isProperty || isLife;
    frm.set_df_property("section_additional_details", "hidden", !hasExtraFields);
}

