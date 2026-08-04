 # Support-Console Agent Skill

 ## Overview

 This skill handles support-operations tasks across multiple domains (consumer, contact-center, enterprise, mobile-data) using a shared RESTful support-console API. Every task follows the same pipeline: read the prompt and payloads, query the console API for supporting evidence, apply decision logic, and emit a single JSON answer matching the provided answer template.

 ## Environment

 The support-console API base URL is provided via the environment variable `TASK_ENV_BASE_URL`. All endpoints are read-only GET. The available endpoints are listed in an `environment_access.md` file or equivalent that ships alongside the task.

 Typical endpoints include:

 - **Catalog & Search**
   - `GET /api/catalog` — list all catalogued resources
   - `GET /api/search` — free-text search across the console

 - **Consumer / Lines / Plans / Devices / Billing**
   - `GET /api/accounts` — list all accounts
   - `GET /api/accounts/{account_id}` — single account detail
   - `GET /api/tickets` — list all tickets
   - `GET /api/tickets/{ticket_id}` — single ticket detail
   - `GET /api/diagnostics/{ticket_id}` — diagnostic run results for a ticket
   - `GET /api/troubleshooting/{ticket_id}` — automated troubleshooting results
   - `GET /api/outages` — list known service outages
   - `GET /api/customers` — list all customers
   - `GET /api/customers/{customer_id}` — single customer detail
   - `GET /api/lines` — list all lines
   - `GET /api/lines/{line_id}` — single line detail
   - `GET /api/devices` — list all devices
   - `GET /api/devices/{device_id}` — single device detail
   - `GET /api/plans` — list all plans
   - `GET /api/plans/{plan_id}` — single plan detail
   - `GET /api/bills` — list all bills
   - `GET /api/bills/{bill_id}` — single bill detail

 - **Cases / Contact Center**
   - `GET /api/cases` — list all cases
   - `GET /api/cases/{case_id}` — single case detail
   - `GET /api/contact-center/cases` — list contact-center cases
   - `GET /api/contact-center/cases/{case_id}` — single contact-center case detail

 - **Enterprise**
   - `GET /api/enterprise/accounts` — list enterprise accounts
   - `GET /api/enterprise/accounts/{account_id}` — single enterprise account detail
   - `GET /api/enterprise/incidents` — list enterprise incidents
   - `GET /api/enterprise/incidents/{incident_id}` — single incident detail
   - `GET /api/enterprise/export-runs` — list export pipeline runs
   - `GET /api/enterprise/messages` — list internal messages / alerts
   - `GET /api/enterprise/sla/{account_id}` — SLA details for an enterprise account

 ## Workflow

 Every task, regardless of domain, follows this six-step pipeline:

 ### Step 1 — Read the Prompt

 The prompt (typically `prompt.txt`) defines the agent persona, the task scope, and the payload file(s) to consume. Look for:
 - The persona (e.g., "support operations analyst", "contact-center lead", "enterprise support lead", "queue-quality analyst", "mobile-data recovery analyst").
 - Which payload file(s) to read.
 - Any special instructions (e.g., "return only JSON that conforms to the answer template", "preserve payload order").

 ### Step 2 — Read the Payloads

 Payloads are in the `payloads/` directory and may be CSV, JSON, or plain text. They contain the work items:
 - **CSV payloads** — typically ticket/queue snapshots with columns like `ticket_id`, `account_id`, `reported_service_type`, `queue_note`, `customer_report`.
 - **JSON payloads** — typically case queues or worklists with `case_id` and `reported_issue`, possibly `customer_preferences`.
 - **Text payloads** — complaint emails or narrative descriptions with client identity, issue references, and requirements.

 Read every payload row/entry; each represents one decision to make.

 ### Step 3 — Read the Answer Template

 The file `payloads/answer_template.json` defines the exact output schema. Treat it as the contract:
 - Every field is required unless explicitly marked optional.
 - Enum values are fixed; do not invent new ones.
 - Preserve ordering: for array fields, keep the same order as the input payload.
 - Numeric fields must match the specified type (integer, number with one/two decimals).
 - String placeholders like `"string"`, `"string; preserve payload order"`, `"YYYY-MM-DD"` are descriptions, not literal values.

 ### Step 4 — Query the Console API

 For each work item, call the relevant API endpoints to gather evidence. Common query patterns:

 **Ticket-based tasks** (consumer support, queue quality):
 - `GET /api/tickets/{ticket_id}` — ticket status, account link, service type
 - `GET /api/accounts/{account_id}` — account standing, suspensions, eligibility
 - `GET /api/diagnostics/{ticket_id}` — latency, stability, bandwidth metrics
 - `GET /api/troubleshooting/{ticket_id}` — automated fix results
 - `GET /api/outages` — active outages matching the service area

 **Case-based tasks** (contact center, mobile data):
 - `GET /api/cases/{case_id}` or `GET /api/contact-center/cases/{case_id}` — case metadata, linked customer/line
 - `GET /api/customers/{customer_id}` — customer profile, permissions
 - `GET /api/lines/{line_id}` — line status, roaming, data usage, suspension
 - `GET /api/bills/{bill_id}` — outstanding charges
 - `GET /api/plans/{plan_id}` — plan caps, data limits
 - `GET /api/devices/{device_id}` — device capabilities, network mode

 **Enterprise tasks**:
 - `GET /api/enterprise/accounts/{account_id}` — account owner, channel name
 - `GET /api/enterprise/incidents/{incident_id}` — severity, status, affected services
 - `GET /api/enterprise/export-runs` — export pipeline history, failure windows
 - `GET /api/enterprise/messages` — alerts, root-cause messages
 - `GET /api/enterprise/sla/{account_id}` — SLA terms and credit percentages

 Always query endpoints in parallel when possible (e.g., fetch all tickets first, then all diagnostics, then all outages). Batch independent calls to reduce latency.

 ### Step 5 — Apply Decision Logic

 Synthesize API evidence into decisions. General guidelines:

 **Resolution status determination:**
 - `RESOLVED` — automated troubleshooting succeeded or device/line fix applied.
 - `PENDING_ACTION` — blocked by an active outage (customer must wait).
 - `ESCALATED` — requires human intervention (field ops, network engineering, tier 2, accounts payable).
 - `FAILED` — ineligible account, invalid account, auth failure, or unrecoverable state.

 **Escalation routing:**
 - `TIER2_SUPPORT` — complex provisioning or configuration issues.
 - `FIELD_OPS` — physical line faults or on-site work needed.
 - `NETWORK_ENGINEERING` — backbone capacity, routing, or infrastructure issues.
 - `ACCOUNTS_PAYABLE` — billing, overdue, or financial holds.

 **Case primary actions:**
 - `RESEAT_SIM` — no-service after physical movement.
 - `SEND_PAYMENT_REQUEST` + `RESUME_LINE_REBOOT` — suspended line with willing customer.
 - `TOGGLE_ROAMING` / `ENABLE_LINE_ROAMING` — international data issues.
 - `GRANT_MESSAGING_PERMISSION` — app permission missing (sms, storage).
 - `TOGGLE_DATA_SAVER` / `SET_NETWORK_MODE` — slow data from device settings.
 - `TOGGLE_MOBILE_DATA` — data off after settings change.
 - `REFUEL_DATA` — data cap reached, customer accepted top-up.
 - `DISCONNECT_VPN` — VPN causing slowness.

 **Root cause for enterprise exports:**
 - Cross-reference export-run failures with messages/alerts around the same window.
 - Check for credential rotations, pipeline config changes, or upstream data issues.
 - Count failed consecutive days from export-run records.

 ### Step 6 — Emit JSON Output

 Produce a single JSON object conforming exactly to the answer template. Requirements:
 - No extra commentary, markdown fences, or preamble — only raw JSON.
 - No invented enum values; use only values listed in the template.
 - Preserve input ordering for array fields.
 - Use the exact field names, nesting, and types from the template.
 - Empty string `""` for optional fields with no applicable value; `0` or `0.0` for numeric fields with no applicable value.
 - Boolean fields are `true`/`false` (not strings).

 ## Domain Glossary

 - **Ticket** — a consumer support request tied to an account and service type (internet, voice, video).
 - **Case** — a contact-center or mobile-data work item tied to a customer and line.
 - **Account** — the billing and service relationship; may be suspended, ineligible, or in good standing.
 - **Line** — the individual service line (phone number, data line) under an account.
 - **Plan** — the rate plan governing data caps, roaming, and features.
 - **Device** — the customer's hardware; has capabilities like network modes.
 - **Bill** — outstanding charges tied to an account.
 - **Outage** — a known service interruption affecting an area or service type.
 - **Diagnostic** — automated metrics (latency, stability, bandwidth) run against a ticket.
 - **Troubleshooting** — automated remediation steps attempted for a ticket.
 - **Enterprise Account** — business/wholesale customer with SLA agreements.
 - **Incident** — a tracked enterprise service disruption with severity and status.
 - **Export Run** — a scheduled data pipeline export for enterprise clients.
 - **SLA** — service-level agreement defining uptime and credit terms.
 - **Channel** — the named communication channel (e.g., Slack) for an enterprise account.

 ## Notes

 - Always read `environment_access.md` first to confirm available endpoints; endpoints may vary between task instances.
 - The API is read-only; all actions described in the answer are classification/routing decisions, not state changes.
 - When a work item references an account ID that does not exist in the console, treat it as `INVALID_ACCOUNT` or `INELIGIBLE_ACCOUNT`.
 - When authentication repeatedly fails for a ticket, classify as `AUTH_FAILED`.
 - Customer preferences in payloads (e.g., accepted refuel GB, plan-change opt-out) constrain the available actions.
