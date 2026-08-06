---
name: northstar-payer-ops
description: >-
  Produce a structured JSON deliverable for a Northstar Health Plan payer-operations
  work item (UM prior-auth determination, pharmacy coverage appeal + manufacturer
  assistance intake, claim repricing/payment-integrity correction, peer-to-peer
  closure, or therapy-margin queue analysis) by reading the shared read-only payer
  operations environment over its SQL and REST endpoints and returning exactly the
  JSON shape the task's answer_template.json defines. Use whenever a task gives a
  Northstar business ID (CASE-*, APPEAL-*/APL-*, CLAIM-*, P2P-*, QUEUE-*), a
  `<TASK_ENV_BASE_URL>` with a `POST /sql/query` bearer token, and an
  answer_template.json to conform to.
---

# Northstar Payer-Operations Deliverable Builder

## What this skill is for

Northstar payer-operations tasks all share the same shape:

- A **task_context.json** naming a target business ID, a requester role, a reporting
  date, and environment access.
- An **answer_template.json** that fixes the exact output JSON (required keys, enums,
  ordering rules, precision, null handling).
- A **shared read-only environment** you must query for the real facts.
- The instruction **"return JSON only"** conforming to the template.

Your job is to pull the real records from the environment, apply the operating rule
for the task's archetype, and emit one JSON object that exactly matches the template.
**Never invent facts, IDs, amounts, or dates — every value must trace to a record you
retrieved.**

Five recurring archetypes exist, each keyed to one `source_precedence` value; a sixth
precedence value exists for appeal-deadline-driven mixed tasks. See the mapping table
below and `reference/playbook.md` for the per-archetype procedure.

## Step 1 — Read access config (never hardcode)

Read `environment_access.md` (and the task's `task_context.json`) at run time for:

- **Base URL** — the `GDPEVO_ENV_BASE_URL` value, substituted for `<TASK_ENV_BASE_URL>`.
- **Bearer token** — sent as `Authorization: Bearer <token>`.
- **Allowed endpoints** — only use endpoints the file lists.

These are environment-scoped and may change between task groups, so always resolve
them from the file rather than assuming a prior value.

## Step 2 — Understand the environment (SQL is the workhorse)

- **`POST /sql/query`**, JSON body `{"sql": "<SELECT ...>"}`, with the bearer header.
  Only `SELECT`, `WITH`, and `PRAGMA table_info` are allowed (writes are rejected with
  `{"error":"invalid_sql"}`). Missing/aborted auth → `{"error":"unauthorized"}`; a bad
  table/column → `{"error":"sql_error","message":...}`.
  Success → `{"columns":[...], "rows":[{...}], "row_count":N, "limited":bool, "max_rows":500}`.
  Results cap at 500 rows — filter by the target ID so you never rely on truncated data.
- **Discover the schema** with `GET /api/tables` (returns every table with column names,
  types, PK, not-null). A cached copy is in `reference/schema.md`, but re-fetch to
  confirm — table shapes can differ per environment.
- **Business REST endpoints** (`GET /api/cases`, `/api/cases/{id}`, `/api/policies`,
  `/api/policies/{id}`, `/api/documents/{id}`, `/api/rate-schedules`, `/api/appeals`,
  `/portal`) return the same data pre-joined and are convenient for spot checks; SQL is
  better for precise joins and filters.

**Guardrails:** Do **not** read environment source files, generated data files, SQLite
files, manifests, or setup scripts directly — several prompts forbid it. Get every fact
through the SQL/REST endpoints only. Access is read-only; do not attempt writes.

## Step 3 — Identify the archetype and pull its records

Resolve the target ID in `cases` (or `claims`/`appeals` when the ID is a claim/appeal),
read `request_type` / `service_domain` / `current_stage`, then follow the matching row:

| Archetype (requester intent) | Trigger signals | Core tables | `source_precedence` |
|---|---|---|---|
| UM prior-auth determination | `prior_authorization`, nurse_review, therapy domain | cases, members, plans, request_lines, policy_criteria, case_criteria, documents, document_facts, authorizations | `current_clinical_records_over_stale_export` |
| Pharmacy appeal + assistance intake | `coverage_exception`/appeal, appeals stage | appeals, cases, drug_trials, case_criteria, policy_criteria, documents, assistance_screen | `payer_appeal_before_manufacturer_assistance` |
| Claim repricing / payment-integrity correction | `claim_payment_review`, payment_integrity stage | claims, claim_lines, members, payment_benchmarks, authorizations | `effective_benchmark_by_plan_modifier_and_date` |
| Peer-to-peer closure | `peer_to_peer`, p2p_complete | cases, request_lines, policy_criteria, case_criteria, p2p_events, documents, authorizations | `new_patient_specific_p2p_information` |
| Therapy-margin queue analysis | `queue_analysis`, finance_queue | service_margin (rows named in task_context) | `margin_threshold_then_charge_sensitivity` |
| Mixed appeal-deadline-driven review | task spans appeal timeliness + clinical + payment | appeals + clinical + claim tables | `appeal_deadline_then_clinical_then_payment_integrity` |

Full per-archetype procedures, formulas, and field mappings are in
`reference/playbook.md`. Read the one that applies before computing.

## Step 4 — Apply the operating rules (cross-archetype invariants)

- **Current-over-stale.** `documents.is_current = 1` are the evidence documents you rely
  on; `is_current = 0` (e.g. `stale_export`, legacy source systems) are **excluded** and
  become exception records — never controlling evidence.
- **Effective-dated benchmarks/policies.** When repricing or applying a rate, select the
  record matching payer + plan_type + service_domain + cpt_code + modifier whose
  `[effective_start, effective_end]` window contains the service date. Reject any schedule
  whose window ended before the service date (a stale/legacy schedule) and any
  "distractor" schedule that does not match the claim's CPT/plan. `allowed_amount` is
  **per unit** — multiply by line units.
- **Criteria come from the data, filtered to the template's keys.** `case_criteria.result`
  already holds `met`/`not_met`/`partial`/`unclear`. Emit only the criterion IDs the
  answer template's `required_keys` list; ignore informational criteria
  (`approval_required = 0`) unless the template asks for them. When a required criterion
  is not met, `policy_criteria.result_if_missing` (`pend`/`deny`/`uphold`) drives the
  disposition/route.
- **Documented vs insufficient evidence.** `drug_trials.documented = 1` (with a real fill
  record / letter) counts as a documented failure; `documented = 0` or "referenced
  without fill record" is undocumented/insufficient.
- **Assistance after payer path.** Manufacturer-assistance readiness (`assistance_screen`)
  is secondary to the payer appeal; assistance gaps rank after appeal-evidence gaps.
- **Margin math.** `total_cost = variable_cost + fixed_cost_allocated`;
  `margin = net_revenue - total_cost`; `revenue_to_cost_ratio = net_revenue / total_cost`;
  `below_threshold = ratio < threshold` (threshold from task_context, e.g. 1.2);
  `gap_to_120pct = threshold * total_cost - net_revenue` for the top below-threshold row.
- **Deadlines.** Use the plan's stated window (e.g. 180-day internal appeal) counted in
  calendar days from the relevant determination/denial date; use `null` when no deadline
  applies.

## Step 5 — Build `basis_audit` (required in every answer)

Every template requires a `basis_audit` object with these four keys:

- **`source_precedence`** — the enum value for this archetype (table above).
- **`controlling_record_ids`** — the environment record IDs that directly decide the
  result (e.g. the current documents, criteria rows, chosen benchmark, auth record, P2P
  event, or the below-threshold margin row), in operational evidence order.
- **`exception_record_ids`** — the gap/exclusion records: unmet-criteria or route gaps
  first, then stale/excluded/decoy records (stale documents, rejected legacy benchmarks,
  undocumented trials, charge-sensitive-only rows).
- **`precedence_record_order`** — the controlling and exception records merged into one
  list, highest priority first under the `source_precedence` rule.

Use the **real record IDs** from the environment (document_id, criterion_id, benchmark_id,
auth_id, line_id, month_id, appeal_id, p2p_id, etc.), not invented ones.

## Step 6 — Enforce the output contract, then self-check

- **JSON only.** No markdown, comments, or prose outside the object. Include every
  `required_top_level_field`. Honor `additional_fields_allowed` / `additional_properties`.
- **Enums.** Every enum value must be an exact allowed choice — no synonyms or casing
  drift.
- **Ordering.** Follow each field's ordering rule precisely (ascending document_id,
  ascending CPT, alphabetical medication/segment, claim-line order, the queue_row_ids
  order from task_context, choices-order for factor lists, etc.).
- **Precision & types.** Currency → 2 decimals (dollars); ratios → the stated precision
  (e.g. 4 decimals); units/counts → integers; dates → `YYYY-MM-DD` (periods `YYYY-MM`).
- **Null vs empty.** Absent modifier → `null`, not `""`. Empty list only when genuinely
  none. Absent deadline → `null`.
- **Self-check before returning:** all required keys present; enums valid; every ID and
  amount traceable to a retrieved record; stale/decoy records excluded and recorded as
  exceptions; ordering and precision applied; `basis_audit` complete.

See `reference/pitfalls.md` for the planted decoys to watch for.
