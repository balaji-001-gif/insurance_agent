# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import frappe
from frappe.utils import add_days, today, now_datetime, fmt_money


def send_daily_agent_digest():
    """Daily scheduled task: send each active agent a summary email
    with their upcoming renewals, overdue premiums, and pending commissions."""
    agents = frappe.db.get_all(
        "Insurance Agent",
        filters={"status": "Active"},
        fields=["name", "agent_name", "email_id", "user"],
    )

    sent = 0
    skipped = 0

    for agent in agents:
        recipient = agent.email_id
        if not recipient and agent.user:
            recipient = frappe.db.get_value("User", agent.user, "email")

        if not recipient:
            skipped += 1
            continue

        data = _gather_agent_summary(agent.name)
        if not _has_any_items(data):
            skipped += 1
            continue

        subject = "📋 Daily Agent Summary — {date}".format(
            date=now_datetime().strftime("%b %d, %Y")
        )
        message = _build_digest_html(agent.agent_name, data)

        try:
            frappe.sendmail(
                recipients=[recipient],
                subject=subject,
                message=message,
                reference_doctype="Insurance Agent",
                reference_name=agent.name,
            )
            sent += 1
        except Exception as e:
            frappe.log_error(
                title="Agent Digest Email Failed",
                message=f"Agent {agent.name} ({recipient}): {e}"
            )

    frappe.db.commit()

    if sent or skipped:
        frappe.log_error(
            title="Agent Daily Digest Summary",
            message=f"Emails sent: {sent}, Skipped (no email or no data): {skipped}, Date: {now_datetime()}"
        )


def _has_any_items(data):
    return any([
        data.get("renewals"),
        data.get("at_risk_policies"),
        data.get("pending_commissions"),
    ])


def _gather_agent_summary(agent_name):
    """Collect renewals, at-risk policies, and pending commissions for one agent."""
    week_end = add_days(today(), 30)

    # Upcoming renewals (next 30 days) — limit to 20
    renewals = frappe.db.sql(
        """
        SELECT pr.name, pr.policy, pr.customer, pr.renewal_due_date,
               pr.renewal_amount, pr.priority, pr.status,
               DATEDIFF(pr.renewal_due_date, CURDATE()) as days_left
        FROM `tabPolicy Renewal` pr
        WHERE pr.agent = %(agent)s
          AND pr.status IN ('Due', 'Contacted', 'Grace Period')
          AND pr.renewal_due_date <= %(end_date)s
          AND pr.renewal_due_date >= CURDATE()
        ORDER BY pr.renewal_due_date ASC
        LIMIT 20
        """,
        {"agent": agent_name, "end_date": week_end},
        as_dict=True,
    )
    # Count total renewals for overflow messaging
    total_renewals = frappe.db.count("Policy Renewal", {
        "agent": agent_name,
        "status": ["in", ["Due", "Contacted", "Grace Period"]],
        "renewal_due_date": ["between", [today(), week_end]],
    })

    # At-risk policies (overdue premiums, no payment received) — limit to 20
    at_risk = frappe.db.sql(
        """
        SELECT ip.name, ip.customer, ip.insurance_product,
               ip.next_premium_date, ip.premium_amount,
               DATEDIFF(CURDATE(), ip.next_premium_date) as days_overdue
        FROM `tabInsurance Policy` ip
        WHERE ip.agent = %(agent)s
          AND ip.policy_status = 'Active'
          AND ip.premium_frequency != 'Single'
          AND ip.next_premium_date IS NOT NULL
          AND ip.next_premium_date < CURDATE()
          AND NOT EXISTS (
              SELECT 1 FROM `tabPremium Payment` pp
              WHERE pp.policy = ip.name
                AND pp.status = 'Paid'
                AND pp.docstatus = 1
                AND pp.payment_date >= ip.next_premium_date
          )
        ORDER BY ip.next_premium_date ASC
        LIMIT 20
        """,
        {"agent": agent_name},
        as_dict=True,
    )

    # Pending commissions
    pending_comm = frappe.db.sql(
        """
        SELECT ac.name, ac.policy, ac.customer, ac.commission_type,
               ac.commission_amount, ac.commission_date, ac.net_commission
        FROM `tabAgent Commission` ac
        WHERE ac.agent = %(agent)s
          AND ac.payment_status = 'Pending'
        ORDER BY ac.commission_date DESC
        """,
        {"agent": agent_name},
        as_dict=True,
    )

    # Premium achievement info
    achievement = frappe.db.get_value(
        "Insurance Agent", agent_name,
        ["target_premium", "achieved_premium"], as_dict=True
    )

    # Count total at-risk for overflow messaging
    total_at_risk = frappe.db.count("Insurance Policy", {
        "agent": agent_name,
        "policy_status": "Active",
        "premium_frequency": ("!=", "Single"),
        "next_premium_date": ("<", today()),
    })

    return {
        "agent_name": agent_name,
        "renewals": renewals,
        "total_renewals": total_renewals,
        "at_risk_policies": at_risk,
        "total_at_risk": total_at_risk,
        "pending_commissions": pending_comm,
        "target_premium": achievement.target_premium if achievement else 0,
        "achieved_premium": achievement.achieved_premium if achievement else 0,
    }


def _build_digest_html(agent_name, data):
    """Build a styled HTML email with the agent's summary data."""
    renewals = data.get("renewals", [])
    total_renewals = data.get("total_renewals", 0)
    at_risk = data.get("at_risk_policies", [])
    total_at_risk = data.get("total_at_risk", 0)
    pending_comm = data.get("pending_commissions", [])

    # Achievement bar
    target = float(data.get("target_premium") or 0)
    achieved = float(data.get("achieved_premium") or 0)
    pct = round((achieved / target * 100), 1) if target else 0
    bar_color = "green" if pct >= 100 else "orange" if pct >= 60 else "red"

    rows = ""

    # Renewals section
    if renewals:
        rows += """
        <tr><td colspan="2" style="background:#f0f4ff;padding:10px 14px;font-weight:700;font-size:15px;border-bottom:2px solid #5e64ff;">
            ⏰ Upcoming Renewals ({count})
        </td></tr>""".format(count=len(renewals))
        for rn in renewals:
            days = rn.days_left
            color = "red" if days <= 3 else "orange" if days <= 7 else "green"
            rows += """
            <tr>
                <td style="padding:6px 14px;border-bottom:1px solid #eee;">
                    <a href="{url}" style="color:#5e64ff;text-decoration:none;">{policy}</a>
                    <br><span style="color:#666;font-size:12px;">{customer}</span>
                </td>
                <td style="padding:6px 14px;border-bottom:1px solid #eee;text-align:right;white-space:nowrap;">
                    ₹{amount}<br>
                    <span style="color:{color};font-size:12px;font-weight:600;">{days}d left</span>
                    <span style="display:inline-block;background:{pbg};color:#fff;font-size:10px;padding:1px 6px;border-radius:8px;margin-left:4px;">{priority}</span>
                </td>
            </tr>""".format(
                url=f"/app/policy-renewal/{rn.name}",
                policy=rn.policy,
                customer=rn.customer,
                amount=fmt_money(rn.renewal_amount or 0, currency="INR"),
                color=color,
                days=days,
                pbg={"Critical": "red", "High": "orange", "Medium": "#5e64ff", "Low": "grey"}.get(rn.priority, "grey"),
                priority=rn.priority,
            )
        if total_renewals > len(renewals):
            rows += """
            <tr><td colspan="2" style="padding:6px 14px;text-align:center;color:#666;font-size:12px;">
                ... and {more} more renewals due this month
            </td></tr>""".format(more=total_renewals - len(renewals))

    # At-risk section
    if at_risk:
        rows += """
        <tr><td colspan="2" style="background:#fff5f5;padding:10px 14px;font-weight:700;font-size:15px;border-bottom:2px solid #dc3545;">
            🚨 Overdue Premiums ({count})
        </td></tr>""".format(count=len(at_risk))
        for p in at_risk:
            days = p.days_overdue
            color = "red" if days > 15 else "orange"
            label = "Critical" if days > 15 else "Past Due"
            rows += """
            <tr>
                <td style="padding:6px 14px;border-bottom:1px solid #eee;">
                    <a href="{url}" style="color:#5e64ff;text-decoration:none;">{policy}</a>
                    <br><span style="color:#666;font-size:12px;">{customer} — {product}</span>
                </td>
                <td style="padding:6px 14px;border-bottom:1px solid #eee;text-align:right;white-space:nowrap;">
                    ₹{amount}<br>
                    <span style="color:{color};font-size:12px;font-weight:600;">{days}d overdue — {label}</span>
                </td>
            </tr>""".format(
                url=f"/app/insurance-policy/{p.name}",
                policy=p.name,
                customer=p.customer,
                product=p.insurance_product or "",
                amount=fmt_money(p.premium_amount or 0, currency="INR"),
                color=color,
                days=days,
                label=label,
            )
        if total_at_risk > len(at_risk):
            rows += """
            <tr><td colspan="2" style="padding:6px 14px;text-align:center;color:#666;font-size:12px;">
                ... and {more} more overdue premiums
            </td></tr>""".format(more=total_at_risk - len(at_risk))

    # Pending commissions section
    if pending_comm:
        total_pending = sum(float(c.commission_amount or 0) for c in pending_comm)
        rows += """
        <tr><td colspan="2" style="background:#fffbf0;padding:10px 14px;font-weight:700;font-size:15px;border-bottom:2px solid #ffc107;">
            💰 Pending Commissions — Total: ₹{total}
        </td></tr>""".format(total=fmt_money(total_pending, currency="INR"))
        for c in pending_comm[:10]:  # Show top 10
            rows += """
            <tr>
                <td style="padding:6px 14px;border-bottom:1px solid #eee;">
                    <a href="{url}" style="color:#5e64ff;text-decoration:none;">{policy}</a>
                    <br><span style="color:#666;font-size:12px;">{type}</span>
                </td>
                <td style="padding:6px 14px;border-bottom:1px solid #eee;text-align:right;white-space:nowrap;">
                    ₹{amount}<br>
                    <span style="color:#28a745;font-size:12px;">Net: ₹{net}</span>
                </td>
            </tr>""".format(
                url=f"/app/agent-commission/{c.name}",
                policy=c.policy,
                type=c.commission_type,
                amount=fmt_money(c.commission_amount or 0, currency="INR"),
                net=fmt_money(c.net_commission or c.commission_amount or 0, currency="INR"),
            )
        if len(pending_comm) > 10:
            rows += """
            <tr><td colspan="2" style="padding:6px 14px;text-align:center;color:#666;font-size:12px;">
                ... and {more} more pending commissions
            </td></tr>""".format(more=len(pending_comm) - 10)

    # Fallback if nothing
    if not rows:
        rows = """
        <tr><td colspan="2" style="padding:20px;text-align:center;color:#666;">
            ✅ All clear — no pending renewals, overdue premiums, or unpaid commissions.
        </td></tr>"""

    html = """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f5f5f5;">
<table width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:20px 10px;">
<table width="600" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.08);">

<!-- Header -->
<tr><td style="background:linear-gradient(135deg,#5e64ff,#3a40cc);padding:24px 30px;text-align:center;">
    <h1 style="margin:0;color:#fff;font-size:22px;">📋 Daily Agent Summary</h1>
    <p style="margin:6px 0 0;color:rgba(255,255,255,0.85);font-size:14px;">
        {agent_name} &mdash; {date}
    </p>
</td></tr>

<!-- Achievement -->
<tr><td style="padding:16px 30px;background:#f8f9ff;border-bottom:1px solid #e8e8e8;">
    <table width="100%" cellpadding="0" cellspacing="0">
    <tr>
        <td style="font-size:13px;color:#666;">Annual Target Achievement</td>
        <td style="text-align:right;font-size:13px;font-weight:600;">
            ₹{achieved} / ₹{target}
            <span style="color:{bar_color};">({pct}%)</span>
        </td>
    </tr>
    </table>
    <div style="margin-top:6px;height:6px;background:#e0e0e0;border-radius:3px;overflow:hidden;">
        <div style="width:{bar_width}%;height:100%;background:{bar_color};border-radius:3px;"></div>
    </div>
</td></tr>

<!-- Data table -->
<tr><td style="padding:0;">
<table width="100%" cellpadding="0" cellspacing="0">
{rows}
</table>
</td></tr>

<!-- Footer -->
<tr><td style="padding:16px 30px;text-align:center;border-top:1px solid #eee;">
    <p style="margin:0;color:#999;font-size:11px;">
        This is an automated daily summary from the Insurance Management System.<br>
        <a href="{dashboard_url}" style="color:#5e64ff;text-decoration:none;">Open Dashboard</a>
    </p>
</td></tr>

</table>
</td></tr></table>
</body>
</html>""".format(
        agent_name=agent_name,
        date=now_datetime().strftime("%b %d, %Y"),
        achieved=fmt_money(achieved, currency="INR"),
        target=fmt_money(target, currency="INR"),
        pct=pct,
        bar_color=bar_color,
        bar_width=min(pct, 100),
        rows=rows,
        dashboard_url="/app/insurance-dashboard",
    )

    return html
