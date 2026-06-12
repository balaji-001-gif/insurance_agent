"""
Create default insurance products if none exist.
"""
import frappe


def execute():
    products = [
        {
            "product_name": "LIC Jeevan Anand",
            "product_code": "LIC-JA-915",
            "product_type": "Life Insurance",
            "insurance_company": "LIC",
            "plan_type": "Endowment",
            "min_age": 18,
            "max_age": 50,
            "min_sum_assured": 100000,
            "max_sum_assured": 50000000,
            "premium_frequency": "Yearly",
            "commission_rate": 15,
            "renewal_commission_rate": 5,
            "min_policy_term": 10,
            "max_policy_term": 35,
        },
        {
            "product_name": "LIC Jeevan Labh",
            "product_code": "LIC-JL-936",
            "product_type": "Life Insurance",
            "insurance_company": "LIC",
            "plan_type": "Endowment",
            "min_age": 18,
            "max_age": 55,
            "min_sum_assured": 200000,
            "max_sum_assured": 25000000,
            "premium_frequency": "Yearly",
            "commission_rate": 12,
            "renewal_commission_rate": 5,
            "min_policy_term": 10,
            "max_policy_term": 25,
        },
        {
            "product_name": "LIC New Money Back 20 Years",
            "product_code": "LIC-NMB-820",
            "product_type": "Life Insurance",
            "insurance_company": "LIC",
            "plan_type": "Money Back",
            "min_age": 13,
            "max_age": 45,
            "min_sum_assured": 100000,
            "max_sum_assured": 25000000,
            "premium_frequency": "Yearly",
            "commission_rate": 20,
            "renewal_commission_rate": 7.5,
            "min_policy_term": 20,
            "max_policy_term": 20,
        },
    ]

    for p in products:
        if not frappe.db.exists("Insurance Product", p["product_code"]):
            doc = frappe.get_doc({"doctype": "Insurance Product", **p})
            doc.insert(ignore_permissions=True)

    frappe.db.commit()
