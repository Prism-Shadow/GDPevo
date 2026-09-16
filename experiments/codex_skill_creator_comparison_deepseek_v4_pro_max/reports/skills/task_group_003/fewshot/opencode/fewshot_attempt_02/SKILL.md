---
name: support-console-resolver
description: Resolve batches of support records by querying a shared REST API support console. Use when the task assigns a support operator role, provides a TASK_ENV_BASE_URL or similar API base URL, and includes payload files with records to resolve plus an answer_template.json that defines the output schema. Triggers for ticket resolution, case triage, enterprise incident response, mobile data recovery, SLA classification, and any batch-support workflow where API lookups against a support console drive structured JSON decisions. Even when the prompt is brief, trigger if it mentions a support console API, batch resolution, payloads, or enum-constrained answer templates.
---

# Support Console Resolver

Resolve batches of support records — tickets, cases, worklists, incidents — by querying a shared REST API support console. The solver must read the task inputs, discover the API surface, fetch the real state for each record, map that state to template decisions, and output structured JSON.

## Workflow

### 1. Orient

Read every file the task provides:

- **The prompt** — identifies the role, the API base URL (look for `<TASK_ENV_BASE_URL>` or similar), and any domain-specific requirements.
- **Payload files** — the records to resolve. These are CSV or JSON lists with entity identifiers (ticket_id, account_id, case_id, customer references, etc.) plus contextual notes.
- **Answer template** (`answer_template.json`) — the exact output schema: field names, enum values for each field, and the summary structure. Every enum value listed in the template is a valid decision; choose among them based solely on API evidence.
- **Requirements files** — if the prompt references additional requirements files (naming conventions, permission lists, required fields), read those too.

If the prompt references a file listing allowed API endpoints, read it. Otherwise, or in addition, query `GET /api/catalog` to confirm which endpoints are live. Compare available endpoints with the full catalog in [references/api-endpoints.md](references/api-endpoints.md) to identify the right endpoints for the task domain.

### 2. Resolve each record against the API

For every record in the payload batch, query the API to learn its real state. The customer-reported symptom or queue note is a starting hint — the API response is the ground truth.

**Lookup strategy for each record:**

1. Start with the record's own endpoint (e.g., `/api/tickets/{ticket_id}`, `/api/contact-center/cases/{case_id}`, `/api/enterprise/incidents/{incident_id}`). This returns the record's status, assigned entity references, and metadata.

2. Follow entity references. If the record links to an account, customer, line, bill, plan, device, or enterprise account, query those endpoints too. The circumstances that drive decisions (suspended account, overdue bill, active outage, provisioning state, roaming status, export failure window) live in those linked entities.

3. Use diagnostic and troubleshooting endpoints when available. `/api/diagnostics/{ticket_id}` reveals technical root causes — latency metrics, packet loss rates, stability indicators, bandwidth measurements, authentication state. `/api/troubleshooting/{ticket_id}` reports what automated fixes succeeded or failed.

4. Check outages. Query `/api/outages` and match by service type or affected area. An active outage covering the record's service means the resolution route is OUTAGE_WAIT rather than active troubleshooting.

5. For enterprise tasks, expand across the enterprise endpoints: incidents for root cause and severity, export-runs for failure windows and backfill status, messages for alert references, and SLA for credit terms. Cross-reference incident owners and account owners from these records.

6. For mobile/contact-center tasks, query the customer to get assigned line, plan, and device. Then query line, plan, device, and bill as needed. The line endpoint shows status (active, suspended, roaming), feature flags (data-saver, VPN, network mode), and permissions. The bill endpoint shows amounts due. The plan endpoint shows data limits and roaming support.

**Parallelize queries.** Query independent endpoints in parallel — a ticket and its outages are independent; a case's customer and a separate case's customer are independent. But entity chains (customer → line → plan) require sequential resolution since each step depends on the previous one.

**Handle errors:**
- A 404 on an entity endpoint means that entity does not exist — an invalid account, a stale reference, a missing record. This is a signal to map the record to the appropriate failure or invalid-account enum.
- A non-404 error: retry once. If it persists, note it and work from the best available evidence.

### 3. Map evidence to template decisions

The answer template defines exactly which fields to populate and which enum values are available. For each field, match the API evidence to the most appropriate enum value.

**How to choose enums from API evidence:**

- **Status enums** (RESOLVED, PENDING_ACTION, ESCALATED, FAILED): resolved when the API shows a fixable issue with successful automated troubleshooting. Pending action when a blocking condition will clear on its own (e.g., an active outage being resolved, a payment then a line resumption). Escalated when the root cause requires a specialist team. Failed when the record is unresolvable through support channels (invalid account, auth failure that cannot be recovered, account ineligible).

- **Boolean flags** (diagnostic_needed, latency_issue, stability_issue, bandwidth_issue, carrier_update_required): set from diagnostic/line/plan endpoint results. If diagnostics show relevant measurements, mark the corresponding flags true. If a resolution requires a carrier-side change, mark carrier_update_required true.

- **Team enums** (TIER2_SUPPORT, FIELD_OPS, NETWORK_ENGINEERING, ACCOUNTS_PAYABLE): match the team whose domain covers the root cause. Use FIELD_OPS for physical line faults or field-level issues. Use NETWORK_ENGINEERING for backbone or capacity problems. Use ACCOUNTS_PAYABLE for billing suspensions or payment holds. Use TIER2_SUPPORT for provisioning, configuration, or complex troubleshooting.

- **Action enums**: pick the operation that directly addresses the root cause revealed by the API. When multiple actions could apply, choose the one most specific to the problem (e.g., if a line needs both roaming enabled and a data refuel, but only one issue is the root cause, pick the matching action). The secondary action should be a necessary follow-up — leave it as NO_ACTION unless the API evidence indicates a two-step resolution.

- **Key blocker enums**: identify the single most fundamental blocking condition from the API evidence. An active outage is more fundamental than a diagnostic issue. An invalid account is more fundamental than an overdue bill.

- **Reference fields** (outage_id, bill_id, incident_id, customer_id, line_id): populate with the exact ID from the API response when one is implicated in the resolution. Leave empty string or omit when none applies.

- **Numeric fields** (charge amounts, backfill days, data refuel GB, SLA credit percent): derive from API data — bill amounts, SLA terms, plan limits, export-run failure windows — rather than assuming or computing.

- **Text fields** (root cause category, channel name, folder name, report title): infer from API evidence (incident root cause, account name, date ranges) and apply any naming conventions specified in requirements files.

**Evidence priority.** When API data conflicts with the customer report or queue note, the API is authoritative. When two API endpoints provide different information about the same concern, prefer the more specific endpoint (diagnostics over ticket summary; incident over account message; line state over customer state).

### 4. Compute aggregate summaries

After populating all per-record decisions, tally the summary counts as defined by the template's summary structure. Count each category exactly — a record classified as RESOLVED counts under RESOLVED regardless of any other properties it has.

For team/route summaries, count which team each record was routed to. For status summaries, count how many records fell into each status. For sub-category summaries (tickets requiring customer wait, self-service fixes, billing recoveries, etc.), derive from the per-record decisions: records with OUTAGE_WAIT or PENDING_ACTION require customer wait; records with SELF_SERVICE route are self-service fixes; records with BILLING_RECOVERY route are billing recoveries.

Where the template asks for total estimated charge, sum the charge_amount_usd across all records.

### 5. Output

Return only the JSON object conforming to the answer template. No markdown fences, no explanatory text, no preceding or trailing content. The output must be valid, complete JSON with every field from the template present for every record.

Preserve record order: use the same order as the input payload (ascending ID order, or row order as-read from the CSV).

## API endpoint reference

The full endpoint catalog with per-endpoint return data and chaining patterns is at [references/api-endpoints.md](references/api-endpoints.md). Read it when you need to understand what each endpoint provides, what fields to expect in responses, and how to chain calls for common resolution domains.
