## When to Use

Apply this skill whenever the task involves resolving support-operation records (tickets, cases, incidents, or worklists) against a shared support-console API whose base URL is provided as `<TASK_ENV_BASE_URL>` or `GDPEVO_ENV_BASE_URL`. Use it whenever payload files (CSV or JSON) and an `answer_template.json` are present in the task input.

## API Reference

The support console exposes GET-only endpoints under the configured base URL. For a complete listing, see `skill/api_catalog.md`.

### Core pattern

- Construct every request as `GET <base_url>/api/<resource>[/<id>]`.
- Never POST — the console is read-only for our purposes.
- If an endpoint returns a 404 or an empty body, treat the resource as absent rather than assuming defaults.

## Input Conventions

- **CSV payloads** (`ticket_batch.csv`, `queue_snapshot.csv`): first row is a header. Process rows in file order and preserve that order in the output array.
- **JSON payloads** (`case_queue.json`, `mobile_data_worklist.json`): iterate the cases array in the order given, ascending by `case_id` when stated.
- **Complaint/requirements pairs** (`client_complaint_email.txt` + `response_requirements.json`): extract identifiers and constraint hints from the free-text email, then cross-reference every enumerated required field against the API evidence.

## Enrichment Workflow

For every input record follow this chain:

1. **Resolve the primary entity** — fetch the ticket, case, account, customer, line, device, plan, bill, incident, or export run that the record names.
2. **Walk related entities** — use the relationships exposed by the API (e.g., ticket → device → plan; case → customer → line → bill) to gather the evidence needed for classification.
3. **Check ambient conditions** — query `/api/outages` and `/api/diagnostics/{id}` or `/api/troubleshooting/{id}` when the task asks about latency, stability, bandwidth, or outage linkage.
4. **Cross-reference** — when the answer template requires a boolean or enum, derive it from the API evidence rather than from the customer description alone.

## Decision Vocabulary

### Resolution statuses
- `RESOLVED` — corrective action was identified and can be applied without human intervention.
- `PENDING_ACTION` — fix is known but requires an external event (outage cleared, payment processed, provisioning cycle, customer action).
- `ESCALATED` — requires a specialist team (Tier-2, Field Ops, Network Engineering, Accounts Payable).
- `FAILED` — record is unprocessable (invalid/missing account, auth failure, fraud suspension, unresolvable state).

### Escalation / route teams
- `NONE` — no escalation needed.
- `TIER2_SUPPORT` — advanced troubleshooting beyond self-service scripts.
- `FIELD_OPS` — physical visit required (line fault, hardware replacement).
- `NETWORK_ENGINEERING` — backbone, capacity, or carrier-side issue.
- `ACCOUNTS_PAYABLE` — billing, overdue, or payment-plan action needed.

### Key blockers (queue-quality tasks)
- `ACTIVE_OUTAGE` — a known outage covers the service area.
- `INVALID_ACCOUNT` — account id does not resolve in the console.
- `AUTH_FAILED` — authentication or credential failure.
- `OVERDUE_SUSPENSION` — account is suspended for non-payment.
- `FRAUD_SUSPENSION` — account has a fraud hold.
- `NETWORK_CAPACITY` — backbone or capacity errors.
- `PROVISIONING_STALE` — provisioning mismatch or stale configuration.
- `PHYSICAL_LINE_FAULT` — reported or diagnosed physical-line issue.
- `NONE` — no blocking condition.

### Mobile actions (contact-center and data-recovery tasks)
- Device-side: `TOGGLE_AIRPLANE_MODE`, `RESEAT_SIM`, `RESET_APN_REBOOT`, `RESUME_LINE_REBOOT`, `SET_NETWORK_MODE`, `DISCONNECT_VPN`, `TOGGLE_WIFI_CALLING`.
- Data-specific: `TOGGLE_MOBILE_DATA`, `TOGGLE_ROAMING`, `ENABLE_LINE_ROAMING`, `REFUEL_DATA`, `TOGGLE_DATA_SAVER`.
- Permission-related: `GRANT_MESSAGING_PERMISSION` (paired with `sms`, `storage`, or `sms_and_storage`).
- Billing: `SEND_PAYMENT_REQUEST`.
- Escalation: `TRANSFER_HUMAN`, `NO_ACTION`.

### Routing endpoints
- `SELF_SERVICE` / `DEVICE_SETTING_FIX` — fix applied through device-side instructions.
- `BILLING_RECOVERY` — resolved by clearing an overdue balance.
- `CARRIER_UPDATE` — requires a carrier-side provisioning or roaming change.
- `HUMAN_TRANSFER` / `DATA_RECOVERY` — requires human intervention or data-refuel processing.
- `OUTAGE_WAIT` — ticket resolved by waiting for outage clearance.
- `AUTO_TROUBLESHOOTING` — resolved through API diagnostics/troubleshooting.
- `ESCALATION` — routed to a specialist team.
- `INELIGIBLE_ACCOUNT` / `INVALID_ACCOUNT` / `AUTH_FAILED` — record cannot proceed.

### Enterprise response (incident/export tasks)
- Severity: `Critical` | `High` | `Medium` | `Low` — determined by SLA breach magnitude, number of failed days, and whether backfill is possible.
- `response_status`:
  - `READY_TO_SEND` — all evidence is consistent, owners are assigned, SLA credit is calculated.
  - `NEEDS_FINANCE_REVIEW` — SLA credit percentage or charge amount needs finance sign-off.
  - `NEEDS_ENGINEERING_REVIEW` — root cause or backfill scope needs engineering confirmation.
  - `UNDER_INVESTIGATION` — evidence is incomplete or contradictory.

## Output Rules

1. Return **only** JSON that conforms to the provided `answer_template.json`.
2. Preserve the enumeration order from the payload in the output array.
3. For integer fields in summaries, write bare integers (not strings).
4. For decimal fields, always include the specified number of decimal places (e.g., `0.00`, `2.0`).
5. For enum fields, match the exact casing and spelling from the template.
6. For empty/missing references (e.g., `outage_id`, `bill_id`), use an empty string `""`.
7. Do not fabricate identifiers — every `incident_id`, `account_id`, `case_id`, `line_id`, `bill_id`, or user id must come from the API response.

## Summary Computation

Every answer template includes a summary object. Compute it by:

1. Counting completed records by their final status/route category.
2. Summing charge amounts where applicable.
3. Counting cases requiring customer wait (ticket tasks) separately from other statuses.

## Error Handling

- When an API returns a non-2xx response for a record, mark that record as `FAILED` and include it in the output array — do not drop it.
- When the payload contains an account that does not exist in the console, use the `INVALID_ACCOUNT` or `INELIGIBLE_ACCOUNT` resolution route.
- When evidence from multiple endpoints conflicts, prefer the most recent diagnostic or incident record.

## Task-Type Mapping

| Prompt signals | Payload type | Enrichment focus |
|---|---|---|
| "ticket batch", "offline service tickets" | CSV | tickets, accounts, outages, diagnostics, troubleshooting |
| "contact-center", "mobile support queue" | JSON case queue | customers, lines, bills, plans, devices |
| "enterprise support", "export complaint", "structured response" | email + requirements JSON | enterprise accounts, incidents, export-runs, messages, SLA |
| "queue-quality", "SLA handoff" | CSV | tickets, accounts, outages, diagnostics |
| "mobile-data recovery", "data worklist" | JSON case list | lines, devices, plans, bills, customer preferences |
