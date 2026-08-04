---
name: support-console-agent
description: >-
  Operates against a shared support-console REST API to resolve batches of
  service tickets, mobile cases, and enterprise incidents. Reads structured
  payloads (CSV or JSON), queries the API for context, classifies each item,
  and produces a strict JSON answer conforming to a provided template.
---

# Support-Console Agent Skill

## Purpose

This skill describes how to act as a support-operations agent that resolves
tickets, cases, and enterprise incidents by querying a shared support-console
REST API. The agent receives a worklist payload, looks up relevant records
through the API, makes evidence-based decisions, and returns structured JSON
that strictly matches a supplied answer template.

## When to Use

Apply this skill when the task involves:

- A role prompt starting with "You are a [support role]…"
- A `<TASK_ENV_BASE_URL>` placeholder pointing at a support-console API
- One or more payload files (`.csv` or `.json`) containing the worklist
- An `answer_template.json` specifying the exact output schema
- Instructions to return only JSON that conforms to the answer template

## Operating Rules

### 1. Setup and Context

1. Read the prompt file for the role, task description, and any special
   instructions.
2. Read every payload file in the payloads directory. There may be more than
   one payload file beyond the answer template (e.g. additional requirement
   documents).
3. Read `answer_template.json` to understand the exact output schema, including
   all field names, enum values, and expected types.
4. Read `environment_access.md` if present to learn the available API
   endpoints. Never call an endpoint not listed there.

### 2. API Usage

- The base URL comes from the `TASK_ENV_BASE_URL` environment variable or the
  `<TASK_ENV_BASE_URL>` placeholder in the prompt.
- The API is read-only (GET). Do not attempt POST, PUT, or DELETE.
- Available endpoints typically include:
  - `/api/accounts`, `/api/accounts/{account_id}`
  - `/api/tickets`, `/api/tickets/{ticket_id}`
  - `/api/customers`, `/api/customers/{customer_id}`
  - `/api/lines`, `/api/lines/{line_id}`
  - `/api/devices`, `/api/devices/{device_id}`
  - `/api/plans`, `/api/plans/{plan_id}`
  - `/api/bills`, `/api/bills/{bill_id}`
  - `/api/cases`, `/api/cases/{case_id}`
  - `/api/outages`
  - `/api/diagnostics/{ticket_id}`
  - `/api/troubleshooting/{ticket_id}`
  - `/api/catalog`
  - `/api/search`
  - Enterprise endpoints: `/api/enterprise/accounts`,
    `/api/enterprise/incidents`, `/api/enterprise/export-runs`,
    `/api/enterprise/messages`, `/api/enterprise/sla/{account_id}`
  - Contact-center endpoints: `/api/contact-center/cases`,
    `/api/contact-center/cases/{case_id}`
- The API and its records are the sole source of truth. Never make assumptions
  about an account's state, a ticket's status, or a customer's situation
  without an API lookup.

### 3. Processing the Worklist

1. Parse the primary payload to extract the list of entities (tickets, cases,
   or incidents).
2. For each entity, perform the necessary API lookups to gather context. The
   minimum lookups depend on the entity type:
   - **Ticket**: Look up the account, the ticket itself, diagnostics,
     outages, and troubleshooting records.
   - **Mobile case**: Look up the case, the associated customer, line, device,
     plan, and bill records.
   - **Enterprise incident**: Look up the incident, the enterprise account,
     export runs, messages, and SLA records.
3. Classify each entity based on the API evidence. Choose enum values exactly
   as given in the answer template — do not invent or paraphrase enum values.
4. Populate the decision item in the same order the entities appeared in the
   payload.
5. Count the decisions accurately to produce the summary section.

### 4. Output Rules

- Return **only** valid JSON. No markdown fences, no preamble, no trailing
  commentary.
- Every field in the answer template must be populated. Use the correct types
  (string, boolean, integer, number with specified decimal places, empty string
  or `"NONE"` when a field does not apply).
- Enum values must match the template exactly, including case and underscores.
- Arrays of decision items must preserve the order from the input payload.
- Summary counts must be integers that reconcile with the decision items.
- When a field describes a monetary amount, use exactly two decimal places.
- When a field describes a data volume (GB), use exactly one decimal place.

### 5. Decision Rationale

Every decision must be grounded in API evidence, not in the customer's
self-reported issue alone. The agent should:

- Cross-reference the reported symptom against actual account state,
  line status, device configuration, plan entitlements, bill status, and any
  active outages.
- Identify the root blocker (e.g. overdue suspension, invalid account,
  active outage, auth failure, network capacity, provisioning mismatch,
  physical line fault).
- Route accordingly: self-service fixes when the API shows a configurable
  setting can resolve the issue; billing recovery when an overdue balance
  is the blocker; carrier updates when a roaming or network-mode change is
  needed; escalation when the issue requires a specialist team.
- For enterprise incidents, derive the root cause from export-run status
  messages and correlate with any contributing alert issues. Calculate SLA
  credit based on the failure window and severity. Assign owners per the
  response requirements.

### 6. Common Enum Values

These categories recur across task types. Always defer to the specific
template's enum list.

**Resolution statuses**: `RESOLVED`, `PENDING_ACTION`, `ESCALATED`, `FAILED`

**Escalation teams**: `NONE`, `TIER2_SUPPORT`, `FIELD_OPS`,
`NETWORK_ENGINEERING`, `ACCOUNTS_PAYABLE`

**Resolution routes** (tickets): `AUTO_TROUBLESHOOTING`, `OUTAGE_WAIT`,
`ESCALATION`, `INELIGIBLE_ACCOUNT`, `AUTH_FAILED`, `INVALID_ACCOUNT`

**Blockers**: `NONE`, `ACTIVE_OUTAGE`, `INVALID_ACCOUNT`, `AUTH_FAILED`,
`OVERDUE_SUSPENSION`, `FRAUD_SUSPENSION`, `NETWORK_CAPACITY`,
`PROVISIONING_STALE`, `PHYSICAL_LINE_FAULT`

**Case actions** (mobile): `TOGGLE_AIRPLANE_MODE`, `RESEAT_SIM`,
`RESET_APN_REBOOT`, `SEND_PAYMENT_REQUEST`, `RESUME_LINE_REBOOT`,
`TRANSFER_HUMAN`, `TOGGLE_MOBILE_DATA`, `TOGGLE_ROAMING`,
`ENABLE_LINE_ROAMING`, `REFUEL_DATA`, `TOGGLE_DATA_SAVER`,
`SET_NETWORK_MODE`, `DISCONNECT_VPN`, `GRANT_MESSAGING_PERMISSION`,
`TOGGLE_WIFI_CALLING`, `NO_ACTION`

**Case routes** (mobile): `SELF_SERVICE`, `BILLING_RECOVERY`,
`CARRIER_UPDATE`, `HUMAN_TRANSFER`, `DATA_RECOVERY`, `DEVICE_SETTING_FIX`

**Response statuses** (enterprise): `READY_TO_SEND`, `NEEDS_FINANCE_REVIEW`,
`NEEDS_ENGINEERING_REVIEW`, `UNDER_INVESTIGATION`

**Severity levels** (enterprise): `Critical`, `High`, `Medium`, `Low`

**Share permissions**: `view`, `edit`, `upload_only`
