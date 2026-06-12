frappe.ui.form.on("Insurance Product", {
    refresh(frm) {
        toggle_auto_calc_fields(frm);
    },

    enable_auto_calculation(frm) {
        toggle_auto_calc_fields(frm);
    },
});

function toggle_auto_calc_fields(frm) {
    const enabled = frm.doc.enable_auto_calculation;
    frm.set_df_property("base_sum_assured", "hidden", !enabled);
    frm.set_df_property("age_multiplier", "hidden", !enabled);
    frm.set_df_property("min_sum_assured_auto", "hidden", !enabled);
    frm.set_df_property("max_sum_assured_auto", "hidden", !enabled);
    frm.set_df_property("calculation_formula", "hidden", !enabled);
}
