# ProcureOps Agent Skill

 ## Overview

 This skill enables an agent to fulfil procurement-operations tasks against a shared ProcureOps REST API. The agent reads task-local payloads (memos, templates, packet files), queries live API records, computes derived values, and returns a single JSON object that matches the provided answer template.

 ## Environment

 The ProcureOps API is served at the base URL supplied by the runner as `<TASK_ENV_BASE_URL>`. No authentication is required. All endpoints accept only `GET`. The agent must not attempt writes (POST/PUT/PATCH/DELETE).

 ## API reference

 Detailed endpoint descriptions, field maps, and query-filter rules live in the companion file `skill/api_reference.md`. Before making any API call, consult that reference for the correct collection name, filterable fields, and record shapes.

 ## Workflow

 ### 1. Read all inputs

 - Read the task `prompt.txt` for objectives, constraints, and the `as_of_date` (if any).
 - Read every file under `input/payloads/`. These are the task's local ground truth:
   - `answer_template.json` — the exact output shape the agent must produce.
   - Memos (`*_memo.md`, `*_memo.json`) — task-specific business context, target record IDs, and control parameters.
   - Packets (`*_packet.json`) — target ID bundles and supplementary registers (e.g., chargeback excerpts).
 - Read `environment_access.md` for the API base URL and allowed endpoints.

 ### 2. Plan the API calls

 Extract every record ID, supplier code, SKU, program ID, PO number, and invoice number mentioned in the payloads. Plan the minimal set of API calls to fetch all required live data:

 - **By ID**: `/collection/<id>` when the payload names a specific record.
 - **By filter**: `/collection?field=value` for exact-match lookups on nested or top-level fields.
 - **By date range**: `/collection?start=YYYY-MM-DD&end=YYYY-MM-DD` for date-scoped collections (receipts, invoices, payments, approvals, budget snapshots).
 - **Whole-collection pulls**: Pull `/suppliers`, `/items`, `/programs`, `/contracts`, `/vendor_risk_events` entirely when the task needs cross-referencing, since these collections are small.

 Always batch independent calls (same collection, different IDs) into a single plan step to minimise round-trips.

 ### 3. Query the API and store results

 Issue all planned GET requests. Record the raw API response for every call so derived values can be traced. If a record is not found, treat `null`/404 as "record does not exist" — do not fabricate data.

 ### 4. Compute derived values

 Use the companion file `skill/computation_patterns.md` for the standard formulas. Key categories:

 - **Budget headroom**: remaining budget = budget_cap − committed_amount (from budget snapshots or program records). Subtract any requested incrementals.
 - **Quantity reconciliation**: ordered vs received vs billed; variance = billed − received; completion ratio = received / ordered.
 - **Financial reconciliation**: received_goods_value = received_qty × unit_price; invoice_total = subtotal + freight + tax; net balance = opening + invoices − scheduled payments.
 - **Chargeback netting**: net_release = invoice_total − approved_chargeback − pending_chargeback.
 - **Contract ceiling**: headroom = ceiling_amount − noncancelled_subtotal (exclude cancelled POs).

 All USD amounts must be rounded to **two decimal places** (cents). Percentages round to **one decimal place**. Ratios round to **four decimal places**.

 ### 5. Assemble the output

 - Start from `answer_template.json`. Every top-level key and nested required key must appear.
 - **Lists are sets** unless the template explicitly says "sort ascending" or provides an ordering rule. Sort only when instructed.
 - **Enum fields**: use exactly the allowed values shown in the template or listed in `skill/enum_reference.md`.
 - **Nulls**: use `null` (JSON literal) when a value is genuinely absent; do not use `"null"`, `""`, or `0.00`.
 - **Dates**: format as `YYYY-MM-DD`.
 - **Evidence**: always include a field or section that lists the API record IDs used (e.g., `endpoint_record_ids`, `supporting_ids`, `evidence`). Always list the task payload files reviewed.

 ### 6. Return only JSON

 The final answer must be a single JSON object with no surrounding prose, markdown fences, or commentary. Validate that every required key from the template is present before returning.

 ## Conventions

 - **PO statuses**: `open`, `partial_receipt`, `fully_received`, `cancelled`, `closed`.
 - **Invoice statuses**: `approved`, `on_hold`, `paid`, `void`.
 - **Receipt statuses**: `accepted`, `pending_inspection`, `rejected`.
 - **Supplier risk ratings**: `clear`, `watch`, `severe`.
 - **Approval actions**: `submitted`, `approved`, `rejected`.
 - **Exclude cancelled POs** from contract usage and budget commitment calculations unless the task explicitly states otherwise.
 - **Receipt evidence as of date**: only include receipts dated on or before the `as_of_date`.
 - **Invoice exceptions as of date**: only include invoices dated on or before the `as_of_date`.
 - **Risk events**: only include events whose `status` is `open` or `monitoring`, not `closed` or `resolved`, as of the `as_of_date`.

 ## Supporting files

 - `skill/api_reference.md` — endpoint catalogue, field maps, and filter syntax.
 - `skill/computation_patterns.md` — standard formulas for budget, quantity, and financial reconciliation.
 - `skill/enum_reference.md` — canonical enum values across all task types.
