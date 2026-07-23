---
name: northstar-payer-ops
description: Produce template-exact JSON determinations for Northstar Health Plan payer-operations tasks against the shared read-only environment at <TASK_ENV_BASE_URL> (POST /sql/query with bearer pa-review-token-014; open GET /api/... business endpoints). Covers UM nurse authorization summaries, pharmacy appeal + manufacturer-assistance dispositions, payment-integrity claim repricing, peer-to-peer final summaries, and therapy margin-queue analysis. Use whenever a prompt names Northstar Health Plan, the task-env base URL, the pa-review-token-014 SQL endpoint, an answer_template.json contract, or a basis_audit object with source_precedence. Read BEFORE writing the JSON answer.
---

# Northstar Payer Operations Determinations

Produce a single JSON object that exactly matches the task's `answer_template.json`, using only the shared read-only Northstar payer-operations environment. Never invent values, never inspect environment source/database/setup files, and never call any judge endpoint.

## 0. Recognize the task

Every Northstar task follows the same shape: a requester role, a target business ID, a reporting date/period, the shared environment, and an `answer_template.json` contract. Map the task to one of five families (an unseen task will be a variant of one of them):

| Family | Target ID shape | Core question | source_precedence rule |
|---|---|---|---|
| UM nurse authorization | `CASE-*` | Approve / pend / escalate / deny / partial for a requested therapy line | `current_clinical_records_over_stale_export` |
| Pharmacy appeal + assistance | `APPEAL-*` / `APL-*` | Appeal path, deadline, step-therapy failures, packet gaps, assistance screen | `payer_appeal_before_manufacturer_assistance` |
| Payment-integrity claim repricing | `CLAIM-*` | Reprice paid claim lines vs the effective benchmark; reject stale source | `effective_benchmark_by_plan_modifier_and_date` |
| Peer-to-peer final summary | `P2P-*` | Did the P2P supply new patient-specific info that changes the review? | `new_patient_specific_p2p_information` |
| Therapy margin queue | `QUEUE-*` | Below-threshold payer-service segments vs charge-sensitive rows | `margin_threshold_then_charge_sensitivity` |

The sixth precedence rule, `appeal_deadline_then_clinical_then_payment_integrity`, applies when a deadline calculation drives routing. Pick the rule that matches the task's controlling logic; do not mix.

## 1. Resolve the environment

- The prompt and `task_context.json` write the base URL as the placeholder `<TASK_ENV_BASE_URL>`. Substitute the real base URL from `environment_access.md` (e.g. `http://task-env:9014/`). All requests go to that host.
- **SQL endpoint** — `POST /sql/query`:
  - Header: `Authorization: Bearer pa-review-token-014` (required; missing/wrong token → 401).
  - Body: JSON `{"sql": "<SELECT ...>"}`. The key is **`sql`**, not `query`.
  - Response: `{"columns":[...], "rows":[...], "row_count":N, "max_rows":500, "limited":bool}`. Capped at 500 rows; if `limited` is true, re-query with a tighter `WHERE`.
  - Read-only. Only `SELECT` is useful; do not attempt writes.
- **Business endpoints** — all `GET /api/...` are open (no auth): `/api/tables`, `/api/cases`, `/api/cases/{case_id}`, `/api/policies`, `/api/policies/{policy_id}`, `/api/documents/{document_id}`, `/api/rate-schedules`, `/api/appeals`. Plus `GET /portal` (human landing page).
- **No dedicated endpoints exist for claims, claim lines, or service_margin** — those tables are reachable only via SQL. See `references/endpoints.md`.
- Do **not** open environment source files, SQLite files, manifests, or setup scripts. The HTTP API is the only interface.

A reusable helper lives at `scripts/query_env.py` (`python3 scripts/query_env.py sql "SELECT ..."` or `... get /api/cases/<case_id>`).

## 2. Gather evidence

The hub call for any case-centric task (UM, pharmacy appeal, P2P) is `GET /api/cases/{case_id}`. It returns one nested object containing: case fields + member fields + provider fields + these lists: `authorizations`, `appeals`, `assistance_screen`, `claims`, `criteria`, `documents`, `document_facts`, `drug_trials`, `p2p_events`, `request_lines`. One call usually gives you the whole case bundle.

Then load the controlling context:
- **Policy + criteria** — `GET /api/policies/{policy_id}` (the `policy_id` is on the case). Returns the policy with nested criteria definitions: `criterion_id`, `criterion_key`, `criterion_text`, `approval_required`, `result_if_missing` (`pend` or `deny`). The per-case results live in the case bundle's `criteria` list (`case_criteria`: `result`, `evidence_fact_ids`, `gap_description`, `reviewer_scope`).
- **Documents** — `documents.is_current` (0/1) is the stale-vs-current signal. Rely on `is_current=1` documents; `is_current=0` (e.g. `stale_export`) are excluded and routed to `exception_record_ids`. `document_facts` carry the structured facts (`fact_key`, `fact_value`, `numeric_value`, `supports_criteria`) that satisfy criteria.
- **Domain auxiliaries** (use the case bundle lists, or SQL for the SQL-only tables):
  - UM auth: `request_lines` (requested CPT/modifier/units), `authorizations` (existing auth record / `denial_reason`).
  - Pharmacy appeal: `appeals` (path, deadline, expedited attestation, owner), `assistance_screen` (program, `denial_required`/`denial_on_file`, `missing_fields`, status), `drug_trials` (medication, outcome, `documented` flag → step-therapy failure evidence).
  - P2P: `p2p_events` (`provider_argument`, `new_information`, `outcome`, `final_status`).
  - Claim repricing: `claims` + `claim_lines` (SQL only) → `paid_amount`, `units`, `modifier`, `service_date`; match to `payment_benchmarks` (via `GET /api/rate-schedules` or SQL).
  - Margin queue: `service_margin` rows for the `queue_row_ids` listed in `task_context` (SQL only).

Full table/column reference: `references/data_model.md`.

## 3. Evaluate and decide

- Map each applicable criterion to `met` / `not_met` / `unclear` / `not_applicable` (some templates also allow `partial`). Use the `case_criteria.result` as the starting point, then confirm against `document_facts` and current documents.
- When a criterion is `unclear` or missing, the policy's `result_if_missing` drives the route: `pend` → `pend_for_information` / `request_more_information`; `deny` → `deny` / `escalate_to_md` depending on `approval_required` and reviewer scope.
- Domain decision logic:
  - **UM auth**: current clinical records + current plan of care control; stale exports never override them. Approve only if all `approval_required` criteria are `met` and requested units are within policy limits.
  - **Pharmacy appeal**: payer appeal is resolved before manufacturer assistance. Classify each prior medication failure as `documented` vs `undocumented_or_insufficient` from `drug_trials.documented`. Packet gaps come from comparing required packet items against what is on file (`assistance_screen.denial_on_file`, `missing_fields`).
  - **Claim repricing**: for each line, pick the benchmark whose `payer`+`plan_type`+`cpt_code`+`modifier` match and whose `effective_start` ≤ `service_date` ≤ `effective_end`. Any source whose `effective_end` < `service_date` (e.g. a "Legacy ... Export") is stale → `stale_source_rejected` + `exception_record_ids`. `correct_allowed_amount` = benchmark `allowed_amount` × `units`; line `recovery_amount` = correct − paid (positive = underpayment / correct_upward; negative = overpayment / correct_downward).
  - **P2P**: if `p2p_events.new_information` is patient-specific and material, `new_information_changed_review=true` and the review may overturn to approval; otherwise uphold. If the final result is adverse, compute the internal appeal deadline = adverse determination date + the plan's internal appeal window (read from the task memo; e.g. a 180-day window) — return `null` only when no deadline applies.
  - **Margin queue**: `total_cost` = `variable_cost` + `fixed_cost_allocated`; `revenue_to_cost_ratio` = `net_revenue` / `total_cost`; `below_threshold` = ratio < configured threshold (read from `task_context.finance_memo.revenue_to_cost_threshold`); `margin` = `net_revenue` − `total_cost`. Separate below-threshold segments from `charge_sensitive=1` rows. `gap_to_120pct` = (threshold × `total_cost`) − `net_revenue` for the top below-threshold issue.

## 4. Build the basis_audit

Every template requires a `basis_audit` object with the same four keys. This is the audit trail and is scored. See `references/basis_audit.md` for the full taxonomy.

- `source_precedence` — the one rule from the enum that matches the task's controlling logic (table above).
- `controlling_record_ids` — environment record IDs that **directly control the result**, in **operational evidence order** (the order you encountered/applied them: case → policy → criteria → evidence → auth/decision).
- `exception_record_ids` — gap/exception records, in **business gap order**: criteria/route gaps first, then stale or excluded records.
- `precedence_record_order` — the union of controlling + exception IDs, listed in **source-precedence order, highest priority first**.

## 5. Serialize to template-exact JSON

Return **one JSON object** — no markdown fences, no prose, no comments. Match the template's required top-level keys exactly; most templates set `additional_fields_allowed: false`. Enforce:

- **Ordering**: ascending `document_id`; ascending CPT; claim lines in `line_number` order; queue rows in the exact order of `task_context.finance_memo.queue_row_ids`; criterion IDs ascending; alphabetical by enum value where the template says so.
- **Null**: use JSON `null` (not `""`) for absent modifiers and for deadlines that don't apply.
- **Numbers**: currency in USD rounded to 2 decimals; ratios to 4 decimals; units are integers.
- **Dates**: ISO 8601 `YYYY-MM-DD`; periods `YYYY-MM`.
- **Enums**: pick only from the template's listed choices.

Full rules: `references/output_discipline.md`.

## Critical pitfalls

- Using the `query` key instead of `sql` for the SQL endpoint → `invalid_sql` error.
- Forgetting the bearer token → 401.
- Reaching for `/api/claims` or `/api/service_margin` (they 404) — use SQL.
- Trusting a stale document (`is_current=0`) or a stale benchmark (`effective_end` < service date) as controlling — it belongs in exceptions.
- Omitting `basis_audit` or giving it the wrong `source_precedence` for the domain.
- Adding narrative or extra fields around the JSON, or reordering lists against the template's stated ordering.
- Hardcoding a prior task's answer values — re-derive every field from the current environment evidence.
