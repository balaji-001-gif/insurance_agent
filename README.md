# Insurance Agent Management for ERPNext V15+

A full-featured Insurance Agent CRM built on Frappe/ERPNext V15+ for LIC and
private insurance agents to manage leads, customers, policies, renewals, and commissions
with AI-powered lead scoring.

## Features
- Lead management with AI scoring and conversion probability
- Customer lifecycle tracking
- Multi-product policy management
- Premium payment tracking
- Policy renewal automation
- Agent commission management
- Follow-up activity logging
- Smart notifications (birthday, renewal, premium due)
- Rich analytics dashboard
- 5 built-in reports

## Installation

```bash
# From your Frappe bench
cd /path/to/frappe-bench
bench get-app https://github.com/balaji-001-gif/insurance_agent.git
bench --site your-site.local install-app insurance_agent_mgmt
bench --site your-site.local migrate
bench restart
```

## Quick Start
1. Go to **Insurance Management** workspace
2. Create Insurance Products first
3. Add Insurance Agents
4. Start adding Leads
5. Convert qualified leads to Customers
6. Issue Policies

## Roles
- **Insurance Admin**: Full access
- **Insurance Manager**: Manage agents, view all reports
- **Insurance Agent**: Own leads, customers, policies only

## License
MIT
