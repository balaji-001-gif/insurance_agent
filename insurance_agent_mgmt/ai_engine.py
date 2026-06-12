# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import frappe
from frappe.utils import now_datetime, date_diff


def score_lead(doc, method=None):
    """AI-powered lead scoring engine.

    Calculates a score (0-100) based on multiple weighted factors:
    - Annual income (higher = more capacity)
    - Engagement (follow-up activities recorded)
    - Product interest (specific products selected)
    - Lead source quality
    - Recency of activity
    """
    if doc.get("__islocal"):
        return

    score = 0.0
    breakdown = {}
    recommendations = []

    # 1. Income score (max 25 points)
    income = doc.annual_income or 0
    if income >= 1000000:
        income_score = 25
    elif income >= 500000:
        income_score = 20
    elif income >= 300000:
        income_score = 15
    elif income >= 100000:
        income_score = 10
    else:
        income_score = 5
    score += income_score
    breakdown["income"] = income_score

    # 2. Engagement score (max 25 points)
    activities = frappe.db.count(
        "Follow Up Activity", filters={"lead": doc.name}
    )
    engagement_score = min(25, activities * 5)
    score += engagement_score
    breakdown["engagement"] = engagement_score

    # 3. Product interest score (max 20 points)
    product_count = len(doc.get("interested_products", []) or [])
    product_score = min(20, product_count * 7)
    score += product_score
    breakdown["product_match"] = product_score

    # 4. Lead source quality (max 15 points)
    source_weights = {
        "Reference": 15,
        "Walk-in": 12,
        "Social Media": 10,
        "Website": 10,
        "Campaign": 8,
        "Cold Call": 5,
        "Other": 3,
    }
    source_score = source_weights.get(doc.lead_source, 5)
    score += source_score
    breakdown["source"] = source_score

    # 5. Recency score (max 15 points)
    if doc.next_follow_up_date:
        days_since = date_diff(now_datetime().date(), doc.next_follow_up_date)
        recency_score = max(0, 15 - abs(days_since) * 2)
    else:
        recency_score = 5
    score += recency_score
    breakdown["recency"] = recency_score

    # Cap at 100
    score = min(100, max(0, score))

    # Generate recommendations
    recs = []
    if income < 300000:
        recs.append("💰 Low income — recommend affordable term plans.")
    if engagement_score < 10:
        recs.append("📞 Low engagement — schedule follow-up activities.")
    if product_score < 7:
        recs.append("📋 Capture product interest to improve targeting.")
    if recency_score <= 3:
        recs.append("⚠️ Lead is cold — re-engage immediately.")

    doc.db_set({
        "ai_score": round(score, 1),
        "conversion_probability": round(score, 0),
        "ai_recommendation": " | ".join(recs) if recs else "✅ On track — continue current approach.",
        "ai_last_updated": now_datetime(),
    })


def batch_score_leads():
    """Daily scheduled task to re-score all active leads."""
    leads = frappe.get_all(
        "Insurance Lead",
        filters={"status": ["in", ["New", "Contacted", "Follow-up", "Qualified"]]},
        fields=["name"],
    )
    for lead in leads:
        try:
            doc = frappe.get_doc("Insurance Lead", lead["name"])
            score_lead(doc)
        except Exception as e:
            frappe.log_error(f"AI Scoring failed for {lead['name']}: {e}")
    frappe.db.commit()
