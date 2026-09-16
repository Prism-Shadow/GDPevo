---
name: support-console-ops
description: Telecom support console operations — resolve offline service tickets, contact-center mobile cases, enterprise export incidents, queue quality reviews, and mobile data recovery worklists by querying the support console REST API and applying domain-specific decision frameworks. Use when the task provides a batch JSON/CSV of tickets, cases, or work items against the support console and asks for structured resolution JSON.
---

# Support Console Operations

Resolve telecom support tasks by querying the support console API and applying
domain decision logic. Always fetch live records — never guess from ticket
summaries alone.

## Quick Start

1. **Get the catalog first:** `GET <BASE_URL>/api/catalog` confirms available
   endpoints and gives context on the data shape.
2. **Read the payload** (CSV or JSON) to understand the task type and how
   many items need resolution.
3. **Read the answer template** from the payload's `answer_template.json` —
   every field in that template must be populated exactly.

## Five Task Types

When you see one of these task patterns, follow the corresponding decision
framework in [decision_frameworks.md](references/decision_frameworks.md):

| Task Signature | Section in Decision Frameworks | Key Endpoints |
|---|---|---|
| CSV with `ticket_id, account_id, reported_service_type, customer_report` | Section 1 — Offline Service Ticket Resolution | tickets, accounts, outages, diagnostics, troubleshooting |
| JSON case queue with `case_id` + `reported_issue` | Section 2 — Contact-Center Case Queue | cases, customers, lines, devices, bills, plans |
| Complaint email + `response_requirements.json` | Section 3 — Enterprise Export Incident Response | enterprise/accounts, enterprise/incidents, enterprise/export-runs, enterprise/messages, enterprise/sla |
| CSV with `ticket_id, account_id, reported_service_type, queue_note` | Section 4 — Queue Quality Review | Same as offline tickets; different output schema |
| JSON worklist with cases + optional `customer_preferences` | Section 5 — Mobile Data Recovery | cases, lines, devices, plans |

For endpoint schemas and field-by-field documentation, see
[api_reference.md](references/api_reference.md).

## Core Rules (Apply to Every Task Type)

### 1. Account Status First

Before analyzing diagnostics or troubleshooting, always check the account.
Account status short-circuits all other evidence:

- **Suspended account** → FAILED / INELIGIBLE_ACCOUNT. Stop.
- **Auth failure** (last_login_status FAILURE + empty recovery) → FAILED / AUTH_FAILED. Stop.
- **Not found (404)** → FAILED / INVALID_ACCOUNT. Stop.

### 2. Outage Match Overrides Diagnostics

Match ticket `service_area` + `service_type` against active outages
(`active: true`). When both match, the ticket is PENDING_ACTION / OUTAGE_WAIT.
Do not interpret diagnostics for outage-matched tickets.

### 3. Diagnostics + Troubleshooting Sequence

For tickets that survive account and outage checks:
1. Fetch diagnostics — classify latency, stability, bandwidth issues
2. Fetch troubleshooting — check if post-values are healthy
3. If healthy → RESOLVED (auto-troubleshooting worked)
4. If still degraded → ESCALATED (map root_cause to escalation team)

### 4. Root Cause → Escalation Mapping

| Diagnostic root_cause | Escalation Team |
|---|---|
| FIBER_DROP_DAMAGE, SIGNAL_LOSS | FIELD_OPS |
| BACKBONE_CAPACITY | NETWORK_ENGINEERING |
| PROVISIONING_STALE | TIER2_SUPPORT |
| CONFIGURATION_DRIFT, VOICE_PROFILE_STALE | NONE (auto-fixable) |

This mapping is consistent across all task types.

### 5. Mobile Case ID Mapping

Case IDs encode the related record IDs: CASE-XXXX → CUST-XXXX, LINE-XXXX,
DEV-XXXX. The case record itself carries all three. Always use the record
values, not string manipulation.

### 6. Device State → Self-Service Action

For mobile cases where the line is not suspended, check the device record and
map to the appropriate action. See the full mapping table in
[decision_frameworks.md](references/decision_frameworks.md).

### 7. Enterprise Naming Conventions

Always read `response_requirements.json` for naming patterns. Derive names
mechanically:
- **Channel:** account name, lowercase, spaces → hyphens
- **Evidence folder:** "<Account Name> <Month Year> Investigation"
- **Report title:** "<Account Name> Export Failure - Resolution Report"

### 8. SLA Credit Comes from the SLA Endpoint

Always fetch `/api/enterprise/sla/<enterprise_account_id>` for SLA credit
percent. Do not infer it from tier, policy, or message content.

### 9. Output Format

- Return **only JSON** — no commentary, no markdown wrapping.
- Follow the answer template's schema exactly.
- Preserve the order of input items in output arrays.
- Use consistent enum values — never invent new ones.

## Resources

### scripts/query.py

Quick API fetch utility for bulk lookups. Use when you need several records
in sequence:

```bash
python3 scripts/query.py <BASE_URL> /api/tickets/TCK-XXXX
```

### references/api_reference.md

Complete endpoint catalog with field-level schemas and decision-relationship
quick reference. Read this when you need to understand a specific endpoint's
response shape.

### references/decision_frameworks.md

Full decision flows for all five task types with detailed tables, blocker
mappings, and cross-cutting patterns. Read this as your primary guide for
structuring each task type's resolution logic.

---

**Always fetch from the API, never guess.** Every answer field must be
traceable to a live record from the support console.
