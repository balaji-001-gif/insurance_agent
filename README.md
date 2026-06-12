# Insurance Agent Management for ERPNext V15+

A full-featured Insurance Agent CRM built on **Frappe/ERPNext V15+** for LIC and private insurance agents to manage leads, customers, policies, renewals, and commissions — with **AI-powered lead scoring**, **provider API integration**, and **automated renewal workflows**.

---

## Table of Contents

1. [Features Overview](#features-overview)
2. [Architecture & DocTypes](#architecture--doctypes)
3. [Installation (SOP)](#installation-sop)
4. [Post-Installation Setup](#post-installation-setup)
5. [End-to-End Business Workflow](#end-to-end-business-workflow)
6. [Standard Operating Procedures (SOPs)](#standard-operating-procedures-sops)
7. [Automation & Scheduled Tasks](#automation--scheduled-tasks)
8. [Notifications System](#notifications-system)
9. [Reports & Analytics](#reports--analytics)
10. [Provider API Integration](#provider-api-integration)
11. [AI Lead Scoring Engine](#ai-lead-scoring-engine)
12. [Agent Daily Digest](#agent-daily-digest)
13. [Troubleshooting Guide](#troubleshooting-guide)
14. [Roles & Permissions](#roles--permissions)

---

## Features Overview

| Feature | Description |
|---|---|
| **Lead Management** | Track prospects from New → Contacted → Follow-up → Qualified → Converted |
| **AI Lead Scoring** | Auto-calculated 0-100 score based on income, engagement, product interest, source, and recency |
| **Customer Lifecycle** | Full KYC (PAN/Aadhaar), nominee details, linked policies and activities |
| **Multi-Product Policies** | Life, Health, Vehicle, Property, Term, ULIP, Pension plans |
| **Premium Tracking** | Payment recording, next-date auto-calculation, status tracking |
| **Policy Renewal Automation** | Auto-create renewal records, priority assignment, lapse detection |
| **Commission Management** | Auto-calculate commissions from premium payments, TDS deduction |
| **Follow-Up Activities** | Log calls, meetings, and outcomes against leads and customers |
| **5 Smart Notifications** | Policy renewal, premium due, lapse warning, lead follow-up, birthday |
| **5 Built-in Reports** | Lead conversion, agent performance, premium collection, renewals, commissions |
| **Insurance Dashboard** | Role-based KPI cards, monthly trends chart, lead funnel |
| **Provider API Integration** | Generic REST/LIC/HDFC client framework with OAuth2 support |
| **Agent Daily Digest** | Automated daily email with upcoming renewals, overdue premiums, pending commissions |
| **Claim Management** | Submit and track insurance claims with provider push |
| **Role-Based Access** | Insurance Admin, Insurance Manager, Insurance Agent |

---

## Architecture & DocTypes

### DocType Tree

```
Insurance Product          ← Master data (auto-named by product_code)
  └── Commission rates, eligibility criteria

Insurance Agent            ← Sales personnel
  ├── Frappe User link, targets, commission rate
  ├── Leads & Customers assigned to them
  └── Policies & Commissions linked

Insurance Lead             ← Prospects (auto: INS-LEAD-YYYY-#####)
  ├── AI Score, Conversion Probability, AI Recommendations
  ├── Lead Product Interest (child table) — interested products
  ├── Follow Up Activity (linked) — call/visit logs
  └── Converts to → Insurance Customer

Insurance Customer         ← Converted leads (auto: INS-CUST-YYYY-#####)
  ├── KYC (PAN, Aadhaar, nominee)
  ├── Policies (linked)
  └── Follow Up Activities (linked)

Insurance Policy           ← Policies issued (auto: INS-POL-YYYY-#####)
  ├── Submittable (Proposal → Active)
  ├── Premium Payment (linked)
  ├── Policy Renewal (linked)
  ├── Agent Commission (linked)
  └── Insurance Claim (linked)

Premium Payment            ← Premium collections
  ├── Triggers: auto-create commission, update policy paid amount
  └── Reverses on cancel

Policy Renewal             ← Auto-created renewal records
  ├── Auto-priority (Critical/High/Medium/Low based on days left)
  └── Agent contact tracking

Agent Commission           ← Auto-created from payments
  ├── First Year / Renewal type
  ├── TDS calculation
  └── Net commissionInsurance Claim              ← Claims submitted
  ├── Submitted/Approved/Rejected flow
  └── Pushes to provider API on submit

Insurance Document          ← Document/image attachments (KYC, claim docs)

Fraud Indicator            ← Fraud flags (extensible)

Provider API Integration   ← External provider config
  └── Auth methods, sync toggles, sync logs
```

### Module Structure

```
insurance_agent_mgmt/              ← Git repo root
├── setup.py / pyproject.toml      ← Package config
├── requirements.txt               ← Python deps
├── README.md
├── MANIFEST.in / license.txt
└── insurance_agent_mgmt/          ← Level 1: Python package root
    ├── __init__.py
    ├── hooks.py                   ← App hooks, doc_events, scheduler, permissions
    ├── modules.txt                ← Module definition
    ├── patches.txt                ← Patch list
    ├── utils.py                   ← Auth helpers, dashboard stats, permissions
    ├── api.py                     ← REST endpoints & doc event handlers
    ├── ai_engine.py               ← Lead scoring engine
    ├── provider_integration.py    ← Provider API client framework
    ├── renewal_automation.py      ← Auto-create renewals & lapse detection
    ├── agent_digest.py            ← Daily email digest builder
    ├── config/
    │   └── desktop.py             ← Workspace config
    ├── patches/v1_0/
    │   ├── create_default_products.py
    │   └── setup_roles_and_permissions.py
    ├── public/                    ← Static assets (CSS/JS)
    └── insurance_agent_mgmt/      ← Level 2: Frappe Module directory
        ├── __init__.py
        ├── doctype/               ← 14 DocTypes
        ├── page/insurance_dashboard/
        ├── report/                ← 5 reports
        ├── notification/          ← 5 notifications
        └── workspace/insurance_management/
```

---

## Installation (SOP)

### Prerequisites

- Frappe/ERPNext V15+ bench installed on a Linux server (Ubuntu 20.04+)
- Python 3.10+
- Node.js 18+
- MySQL 8.0+ or MariaDB 10.6+

### Step 1 — Get the App

```bash
# Navigate to your bench directory
cd /home/frappe/f15-bk

# Clone the app from GitHub
bench get-app https://github.com/balaji-001-gif/insurance_agent.git
```

> **⚠️ Known Issue:** `uv` (the Python resolver used by bench) may fail with:  
> `"URL dependencies must be expressed as direct requirements or constraints"` for the `gunicorn` transitive dependency from Frappe.  
> **Fix:** `pyproject.toml` is included with `gunicorn` as a direct URL dependency. If the error persists, run:
> ```bash
> bench pip install --no-deps -e apps/insurance_agent_mgmt
> ```

### Step 2 — Install on Site

```bash
bench --site your-site.local install-app insurance_agent_mgmt
```

> **⚠️ Known Issue:** If a previous failed attempt left a stale `Module Def` in the DB, use `--force`:
> ```bash
> bench --site your-site.local install-app insurance_agent_mgmt --force
> ```
> Or manually remove the stale entry:
> ```bash
> bench --site your-site.local console
> frappe.db.delete("Module Def", "Insurance Agent Mgmt")
> frappe.db.commit()
> exit()
> ```

### Step 3 — Migrate & Restart

```bash
bench --site your-site.local migrate
bench restart
```

### Step 4 — Verify Installation

1. Login to your Frappe site as **Administrator**
2. Look for the **"Insurance Management"** workspace in the workspace switcher
3. You should see shortcuts for: Insurance Lead, Insurance Customer, Insurance Policy, Premium Payment, etc.

### Step 5 — Update the App (when pulling new versions)

```bash
cd /home/frappe/f15-bk/apps/insurance_agent_mgmt
git pull origin main
cd /home/frappe/f15-bk
bench --site your-site.local migrate
bench restart
```

---

## Post-Installation Setup

### 1. Create Insurance Products

Products are auto-created by the patch system on install (LIC Jeevan Anand, Jeevan Labh, New Money Back). To add more:

1. Go to **Insurance Management > Insurance Product**
2. Click **+ Add Insurance Product**
3. Fill in: Product Name, Product Code (unique), Type, Company, Eligibility (age/sum), Premium Frequency, Commission Rates
4. Save

### 2. Set Up Insurance Agents

1. Go to **Insurance Management > Insurance Agent**
2. Click **+ Add Insurance Agent**
3. Fill in: Agent Name, Mobile No (required), Email ID
4. **Link a Frappe User** — this gives the agent login access with the "Insurance Agent" role
5. Set: Agent Type (LIC/HDFC/etc.), Target Premium, Commission Rate
6. Save
7. The linked user will automatically get the **Insurance Agent** role

### 3. Create Insurance Admin/Manager Users

1. Go to **Users** (Frappe user list)
2. Create or edit a user
3. Assign roles: `Insurance Admin` (full access) or `Insurance Manager` (manage agents + reports)

### 4. Configure Notifications

5 auto-configured notifications are active on install:

| Notification | Trigger | Channel |
|---|---|---|
| Policy Renewal Reminder | 30 days before renewal due date | Email + System |
| Premium Due Reminder | 7 days before premium due date | Email + System |
| Premium Lapse Warning | 15 days after missed premium | Email + System |
| Lead Follow Up Reminder | On next_follow_up_date = today | System |
| Customer Birthday Reminder | On date_of_birth | Email |

To customize: Go to **Settings > Notification** and edit the relevant notification.

### 5. Verify Scheduled Jobs

These background jobs run automatically. To check they're enabled:

```bash
bench --site your-site.local scheduler status
```

Expected daily jobs:
- `insurance_agent_mgmt.ai_engine.batch_score_leads`
- `insurance_agent_mgmt.renewal_automation.auto_create_policy_renewals`
- `insurance_agent_mgmt.renewal_automation.mark_lapsed_policies`
- `insurance_agent_mgmt.agent_digest.send_daily_agent_digest`

Expected hourly job:
- `insurance_agent_mgmt.provider_integration.sync_all_providers`

---

## End-to-End Business Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                       COMPLETE WORKFLOW                          │
└─────────────────────────────────────────────────────────────────┘

1. CREATE INSURANCE PRODUCTS
   └── Define products with eligibility, commission rates
   
2. ONBOARD INSURANCE AGENTS
   └── Create agent records → Link Frappe users → Set targets

3. CAPTURE LEADS
   ├── Walk-in, Reference, Social Media, Campaign, Cold Call, etc.
   ├── AI auto-scores the lead (0-100) on save
   └── Assign to agent (auto-assigns if agent is logged in)

4. QUALIFY THE LEAD
   ├── Log Follow Up Activities (calls, visits, meetings)
   ├── Capture Product Interests (child table)
   ├── Update status: New → Contacted → Follow-up → Qualified
   ├── AI re-scores daily based on engagement & recency
   └── Set Priority: Low / Medium / High

5. CONVERT LEAD TO CUSTOMER
   ├── Click "Convert to Customer" button
   ├── System creates Insurance Customer with KYC fields
   ├── Lead status set to "Converted"
   └── Collect PAN, Aadhaar, Nominee details

6. ISSUE POLICY
   ├── Create Insurance Policy linked to customer
   ├── Select Insurance Product → auto-fills commission rates
   ├── Set Sum Assured, Premium Amount, Frequency
   ├── Add Nominee details
   ├── Submit → Status changes from "Proposal" to "Active"
   └── Policy statuses: Proposal → Active → Lapsed/Surrendered/Matured

7. COLLECT PREMIUM PAYMENTS
   ├── Create Premium Payment against policy
   ├── Submit → Status "Paid"
   ├── AUTO: Updates policy's total_premium_paid
   ├── AUTO: Advances next_premium_date
   ├── AUTO: Creates Agent Commission record
   └── AUTO: If policy was Lapsed, reactivates it

8. MONITOR RENEWALS (Automated)
   ├── Daily job: Creates Policy Renewal records for upcoming 30 days
   ├── Auto-priority: Critical (7d), High (15d), Medium (30d), Low (>30d)
   └── Agent notified 30 days before via email + system notification

9. MANAGE CLAIMS
   ├── Create Insurance Claim linked to policy
   ├── Submit → Status "Submitted"
   ├── Push to provider API (if configured)
   └── Track: Submitted → Under Review → Approved / Rejected

10. PAY COMMISSIONS
    ├── Agent Commission records auto-created on premium payment
    ├── Commission type: "First Year" or "Renewal"
    ├── Rate from: Product (first year %) → Agent (default %)
    ├── TDS auto-calculated
    └── Payment status: Pending → Paid
```

---

## Standard Operating Procedures (SOPs)

### 🔷 SOP: Insurance Admin (Daily)

| Time | Task | Details |
|---|---|---|
| **Start of Day** | Check Dashboard | Review KPIs: new leads, active policies, renewals due, premium collected |
| **Throughout Day** | Manage Agents | Onboard new agents, update targets, review performance |
| **Throughout Day** | Review Reports | Lead conversion trends, agent performance rankings, premium collections |
| **Weekly** | Provider Sync Check | Verify `Provider API Integration` sync logs for any failures |
| **Weekly** | Commission Approval | Review and approve pending commissions for payment |
| **Monthly** | Performance Review | Run agent performance report, set new targets |

**Admin responsibilities:**
- Create insurance products and set commission structures
- Create agent user accounts and assign roles
- Monitor system health (scheduled jobs, sync status)
- Handle escalated claims and policy exceptions
- Configure provider API integrations

### 🔷 SOP: Insurance Agent (Daily)

| Time | Task | Details |
|---|---|---|
| **Morning** | Check Daily Digest Email | Review upcoming renewals, overdue premiums, pending commissions (auto-sent) |
| **Morning** | Check Dashboard | View personal KPIs, lead funnel, follow-up reminders |
| **Throughout Day** | Follow Up on Leads | Prioritize by AI score & priority; log activities with outcome |
| **Throughout Day** | Collect Premiums | Contact customers with upcoming/due premiums; record payments |
| **Throughout Day** | Contact Renewals | Reach out to customers with upcoming renewal dates |
| **End of Day** | Log All Activities | Ensure all calls, meetings, and outcomes are recorded |

**Agent priorities (by AI score):**
- **80-100:** Hot lead — high conversion probability, prioritize immediate follow-up
- **60-79:** Warm lead — good potential, schedule follow-up within 3 days
- **40-59:** Moderate — nurture with regular follow-ups
- **Below 40:** Low priority — consider if worth pursuing further

### 🔷 SOP: Converting a Lead to Customer

1. Open the **Insurance Lead** record
2. Verify lead information (name, mobile, email)
3. Check **AI Score** and **AI Recommendations**
4. Ensure at least one **Follow Up Activity** is logged
5. Click **"Convert to Customer"** button (whitelisted API method)
6. System creates **Insurance Customer** with all lead data copied
7. Complete KYC: Enter **PAN Number** and **Aadhaar Number**
8. Add **Nominee Details**
9. Save the customer record

> ⚠️ **Do not** manually change lead status to "Converted" — use the button/API, which also creates the customer. The conversion is done via `frappe.call('insurance_agent_mgmt.api.convert_lead_to_customer', { lead_name: '...' })`. A custom button on the Lead form can be added to call this method.

### 🔷 SOP: Issuing a Policy

1. Ensure the **Insurance Customer** has KYC completed (PAN + Aadhaar + Nominee)
2. Go to **Insurance Policy > + Add New**
3. Link the **Customer** and **Insurance Product**
4. Assign the **Agent**
5. Enter **Sum Assured** (must be within product's min-max range)
6. Enter **Premium Amount** and **Frequency** (Monthly/Quarterly/Half-Yearly/Yearly/Single)
7. Set **Policy Term** in years
8. Add **Nominee** details for the policy
9. Save → **Submit** the document
10. Status changes: "Proposal" → "Active"

### 🔷 SOP: Handling Policy Renewals

1. Check **Policy Renewal** list (sorted by due date, priority)
2. Filter by status: "Due" or "Critical" priority
3. Contact the customer via phone/WhatsApp
4. Update **Contact Date** and **Contact Mode**
5. If customer agrees: Collect premium → Create **Premium Payment**
6. Once payment is submitted, renewal status will automatically be tracked
7. If customer delays: Set **Next Contact Date** for follow-up

### 🔷 SOP: Provider API Setup

1. Create a **Provider API Integration** record
2. Set **Provider Name** (e.g., "LIC India", "HDFC Life")
3. Enter **API Base URL**
4. Choose **Auth Method**:
   - **API Key** — simple key-based auth
   - **Basic Auth** — Base64-encoded key:secret
   - **Bearer Token** — static token
   - **OAuth2** — client credentials flow (auto-refresh)
5. Toggle which data types to sync (plans, renewals, policies)
6. Set **Sync Interval** (default: 1440 min = daily)
7. Test connection: Click "Verify Connection" action button
8. Enable integration

---

## Automation & Scheduled Tasks

### Daily Tasks (runs once per day)

| Task | Function | What It Does |
|---|---|---|
| **AI Lead Scoring** | `ai_engine.batch_score_leads` | Re-scores all active leads (New/Contacted/Follow-up/Qualified) |
| **Auto-Create Renewals** | `renewal_automation.auto_create_policy_renewals` | Creates Policy Renewal records for policies due within 30 days |
| **Mark Lapsed Policies** | `renewal_automation.mark_lapsed_policies` | Marks policies as Lapsed if premium is 30+ days overdue |
| **Agent Daily Digest** | `agent_digest.send_daily_agent_digest` | Emails each active agent their daily summary |

### Hourly Tasks

| Task | Function | What It Does |
|---|---|---|
| **Sync Providers** | `provider_integration.sync_all_providers` | Syncs data from all active provider integrations |

### Event-Driven Automation (doc_events)

| Event | Action | Trigger |
|---|---|---|
| Lead Validate | AI score the lead | Every lead save |
| Premium Payment Submit | Create commission, update policy paid amount | Payment submitted |
| Premium Payment Cancel | Reverse commission & paid amount | Payment cancelled |
| Policy Update/Cancel | Push status update to provider | Policy status changes |
| Claim Submit | Push claim to provider API | Claim submitted |
| User Login | Set agent session data | Agent logs in |

---

## Notifications System

| Notification | DocType | When | Recipient | Channel |
|---|---|---|---|---|
| **Policy Renewal Reminder** | Policy Renewal | 30 days before due | Agent (by field) | Email + System |
| **Premium Due Reminder** | Insurance Policy | 7 days before due | Agent (by field) | Email + System |
| **Premium Lapse Warning** | Insurance Policy | 15 days after due | Agent (by field) | Email + System |
| **Lead Follow Up Reminder** | Insurance Lead | On due date | Agent (assigned) | System |
| **Customer Birthday** | Insurance Customer | On birthday | Customer (email) | Email |

---

## Reports & Analytics

### Built-in Reports

| Report | Description |
|---|---|
| **Lead Conversion Report** | Tracks lead-to-customer conversion rates over time |
| **Agent Performance Report** | Ranks agents by premium collected, policies issued, conversion rate |
| **Premium Collection Report** | Premium collected by period, agent, product |
| **Policy Renewal Due Report** | All upcoming renewals with days left and priority |
| **Commission Summary Report** | Agent commissions earned, TDS deducted, net payable |

### Dashboard KPIs

The **Insurance Dashboard** page shows:

- **Leads Total / New / Converted** — Conversion rate %
- **Active Policies** — Total in-force policies
- **Renewals Due** — Count of due renewals
- **Premium This Month** — Total collected
- **Commission Pending** — Unpaid commissions
- **Monthly Premium Trends** — Bar chart by month
- **Lead Funnel** — Count by status stage

> 💡 The dashboard is **role-aware**: Agents see only their own data; Admins & Managers see all.

---

## Provider API Integration

The app includes a generic provider integration framework that can connect to external insurance company APIs (LIC, HDFC Life, ICICI Prudential, etc.).

### Architecture

```
BaseProviderClient (abstract)
├── GenericProviderClient — REST-based fallback
├── LICClient — LIC India API with OAuth2
└── HDFCLifeClient — HDFC Life API (extensible)
```

### Supported Features

| Feature | Description |
|---|---|
| **Sync Plans** | Fetch products from provider, auto-create/update Insurance Products |
| **Sync Renewals** | Fetch upcoming renewals, create Policy Renewal records |
| **Push Claims** | Submit claim data to provider on claim submission |
| **Push Policy Updates** | Notify provider of policy status changes (Surrender/Lapse) |
| **Verify Customers** | Batch customer identity verification with provider |

### Auth Methods

- API Key
- Basic Auth
- Bearer Token
- OAuth2 (with auto token refresh — LIC client implements this)

---

## AI Lead Scoring Engine

The AI scoring engine (`ai_engine.py`) calculates a 0-100 score for every lead on every save and re-scores all active leads daily.

### Scoring Breakdown

| Factor | Max Points | Logic |
|---|---|---|
| **Income** | 25 | ₹10L+ → 25, ₹5L+ → 20, ₹3L+ → 15, ₹1L+ → 10, below → 5 |
| **Engagement** | 25 | 5 points per follow-up activity logged (capped at 25) |
| **Product Interest** | 20 | 7 points per product selected in child table (capped at 20) |
| **Lead Source** | 15 | Reference → 15, Walk-in → 12, Social/Website → 10, Campaign → 8, Cold Call → 5 |
| **Recency** | 15 | Based on days since next follow-up date (decays over time) |

### Score Interpretation

| Score | Label | Action |
|---|---|---|
| 80-100 | 🔥 Hot | Immediate follow-up, high conversion probability |
| 60-79 | ✅ Warm | Schedule follow-up within 3 days |
| 40-59 | ⏳ Moderate | Regular nurturing |
| Below 40 | ❄️ Cold | Re-engage or consider deprioritizing |

### AI Recommendations

The engine generates contextual recommendations like:
- "💰 Low income — recommend affordable term plans."
- "📞 Low engagement — schedule follow-up activities."
- "📋 Capture product interest to improve targeting."
- "⚠️ Lead is cold — re-engage immediately."
- "✅ On track — continue current approach."

---

## Agent Daily Digest

Every morning, the system sends each active agent a personalized HTML email with:

### Email Sections

1. **Header** — Agent name, current date
2. **Target Achievement Bar** — Annual premium target vs. achieved (with color: green ≥100%, orange ≥60%, red <60%)
3. **Upcoming Renewals** — Next 30 days, sorted by priority, with days left
4. **Overdue Premiums** — Active policies past due, days overdue, criticality
5. **Pending Commissions** — Unpaid commissions with amounts

The digest only sends if there's data to report. Agents with no email address or no pending items are skipped.

---

## Troubleshooting Guide

### Installation Issues

| Error | Cause | Fix |
|---|---|---|
| `Directory not empty` | Stale directory from previous clone | `rm -rf apps/insurance_agent_mgmt apps/insurance_agent` then retry |
| `Duplicate entry 'Insurance Agent Mgmt' for key 'PRIMARY'` | Stale Module Def from previous attempt | Use `--force` flag or delete from console |
| `No module named '...lead_product_interest.lead_product_interest'` | Missing `__init__.py` or `.py` file in doctype directory | Run `git pull` on the bench server to get the latest commit with the fix |
| `URL dependencies must be expressed as direct requirements` | `uv` rejecting transitive URL dep on gunicorn | `pyproject.toml` includes gunicorn as direct dep; re-pull the latest code |
| `Cannot find app insurance_agent_mgmt` | App not registered in bench | Run `bench get-app` again or check `apps/` directory |

### Runtime Issues

| Symptom | Cause | Fix |
|---|---|---|
| AI score not updating | Scheduled job not triggered | Check `bench --site site scheduler status` |
| Renewal records not creating | Same as above | Verify daily scheduler is running |
| Agent not seeing their data | Missing permission assignment | Ensure user has "Insurance Agent" role and is linked to an Agent record |
| Provider sync failing | Auth expired / network error | Check integration's last sync log; re-test connection |
| Emails not sending | Email domain not configured | Configure Frappe email domain in **Settings > Email Domain** |

### Quick Recovery Commands

```bash
# Clear all caches
bench --site your-site.local clear-cache

# Restart bench processes
bench restart

# Check scheduler status
bench --site your-site.local scheduler status

# Enable scheduler if disabled
bench --site your-site.local scheduler enable

# Run a specific scheduled task manually
bench --site your-site.local console
import frappe
frappe.get_attr("insurance_agent_mgmt.renewal_automation.auto_create_policy_renewals")()
frappe.db.commit()
```

### Updating the App After Code Changes

```bash
cd /home/frappe/f15-bk/apps/insurance_agent_mgmt
git pull origin main
cd /home/frappe/f15-bk
bench --site your-site.local migrate
bench restart
bench --site your-site.local clear-cache
```

---

## Roles & Permissions

### Insurance Admin

- **Full access** to all DocTypes (create, read, write, delete, submit, cancel)
- Manage agents, products, integrations, and settings
- View all data across all agents
- Configure provider API integrations

### Insurance Manager

- Create, read, write (but no delete) on most DocTypes
- Submit and cancel policies
- View all reports and agent data
- Cannot delete records

### Insurance Agent

- **Scoped access** — sees only own leads, customers, policies, payments, commissions
- Create leads, customers, policies, and payments
- Cannot delete records
- Cannot see other agents' data (enforced by `has_permission` hook)

### Permission Enforcement

The `insurance_agent_mgmt.utils.has_permission` function checks:
1. **Administrator** — full access
2. **Insurance Admin / Manager** — cross-agent access
3. **Insurance Agent** — restricted to documents where `assigned_agent` or `agent` field matches their linked agent record

---

## License

MIT

---

## Support

For issues, feature requests, or contributions:
- GitHub: [https://github.com/balaji-001-gif/insurance_agent](https://github.com/balaji-001-gif/insurance_agent)
- Documentation: Refer to this README and the Frappe/ERPNext docs at [frappeframework.com/docs](https://frappeframework.com/docs)
