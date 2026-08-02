---
name: northstar-payer-ops-determination
description: >-
  Produce a structured JSON determination for a Northstar Health Plan payer-operations
  task by reading its inputs and querying the shared read-only payer-ops environment
  (SQLite-backed portal with a POST /sql/query endpoint plus GET /api business endpoints).
  Use when a task packet gives a prompt.txt + task_context.json + answer_template.json
  that references the Northstar payer operations environment and asks for JSON matching
  the template. Covers the five archetypes: UM prior-authorization nurse determination,
  pharmacy coverage appeal + manufacturer-assistance intake, payment-integrity claim
  repricing, peer-to-peer (P2P) final summary, and service-margin queue analysis.
  Triggers: "Northstar", "payer operations", "prior authorization", "UM nurse",
  "determination", "coverage appeal", "manufacturer assistance", "claim repricing /
  benchmark", "peer-to-peer", "service margin queue", "pa-review-token", "basis_audit".
---

# Northstar Payer-Operations Determination

You are given a task packet that asks for a structured JSON answer derived from the
**Northstar Health Plan payer-operations environment** — a shared, read-only portal
backed by a SQLite database. Your job is to read the task, query the environment for
**only the target record(s)**, apply the archetype's business rules, and emit JSON that
matches the task's `answer_template.json` exactly.

Do **not** invent values. Every field is derived from environment records plus the
task's own definitions. The environment contains many unrelated "distractor" rows —
scope strictly to the target business id(s).

## 1. Read the three input files first

Every task instance provides (paths relative to the task's `input/`):

- `prompt.txt` — the narrative ask and any special instructions (rounding, ordering,
  null handling, deadline windows, "environment only", etc.). Read it carefully; it
  often states the one rule that decides an ambiguous field.
- `payloads/task_context.json` — the machine-readable context: `target_business_id`
  (and sometimes `target_appeal_id`, explicit `queue_row_ids`, finance definitions),
  `requester_role`, `reporting_date`/reporting period, and the `environment` block
  (base_url, sql endpoint, bearer token).
- `payloads/answer_template.json` — the **output contract**. Extract: the required
  top-level fields (in order), every enum's allowed `choices`, list `ordering` rules,
  numeric precision, date format, null-vs-empty conventions, and whether
  `additional_fields_allowed`/`additional_properties` is false (if so, emit *no* extra keys).

Classify the archetype (see `reference/task_playbooks.md`) from the target-id prefix,
`request_type`/`service_domain`/`work_type`, and the template's field set:

| Signal | Archetype | `basis_audit.source_precedence` |
|---|---|---|
| `CASE-…`, prior_authorization, criteria+authorization+documents | UM nurse determination | `current_clinical_records_over_stale_export` |
| `APPEAL-…`, appeal + drug_trials + assistance_screen | Pharmacy appeal + assistance | `payer_appeal_before_manufacturer_assistance` |
| `CLAIM-…`, claim_lines + payment_benchmarks, repricing | Payment-integrity repricing | `effective_benchmark_by_plan_modifier_and_date` |
| `P2P-…`, p2p_events, "peer-to-peer" | P2P final summary | `new_patient_specific_p2p_information` |
| `QUEUE-…`, service_margin, ratios/threshold | Service-margin queue | `margin_threshold_then_charge_sensitivity` |

(An appeal-deadline-driven variant uses `appeal_deadline_then_clinical_then_payment_integrity`;
pick the precedence the task's logic actually turns on.)

## 2. Resolve environment access

- **Base URL**: `task_context.environment.base_url`. If it is the literal
  `<TASK_ENV_BASE_URL>`, substitute the value of `GDPEVO_ENV_BASE_URL` from the
  repository's `environment_access.md`.
- **Bearer token**: from `task_context.environment` (e.g. `pa-review-token-014`) /
  `environment_access.md`. Required for `POST /sql/query`; GET business endpoints do
  not require it but sending it is harmless.
- Confirm reachability with `GET /api/tables` before querying.

Access rules (respect the prompt): the environment is **read-only** — `POST /sql/query`
accepts only `SELECT`, `WITH`, and `PRAGMA table_info` (writes are rejected), and caps
results at 500 rows. **Never** inspect environment source files, generated data files,
SQLite files, manifests, or setup scripts directly — use only the HTTP endpoints.

See `reference/data_model.md` for the full endpoint + table/column reference and the
`scripts/nsql.py` helper for issuing SQL queries.

## 3. Pull only the target records

1. Prefer the bundled fetch `GET /api/cases/{case_id}` — it returns the case plus its
   nested `criteria`, `authorizations`, `documents`, `claims`, `appeals`,
   `assistance_screen`, `request_lines`, `p2p_events`, and `drug_trials`.
2. For anything not in the bundle (e.g. `payment_benchmarks`, `service_margin`,
   `claim_lines`, `document_facts`, member `plan_type`), query with `nsql.py`,
   filtering by the target id: `WHERE case_id = '…'`, `WHERE claim_id = '…'`, or the
   explicit `month_id IN (…)` list the task supplies.
3. When the task lists explicit row IDs (e.g. `finance_memo.queue_row_ids`), use **only**
   those rows — do not widen the query.

## 4. Derive fields with the archetype playbook

Follow `reference/task_playbooks.md` for the per-archetype field-by-field rules
(criteria mapping, authorization roll-ups, documented/undocumented failure splits,
current-vs-stale benchmark selection and line math, P2P outcome + appeal-window date
arithmetic, and margin/ratio/threshold computation). General principles:

- **Criteria** (`criteria_results`): read `case_criteria.result` for the criterion IDs
  the template requires; carry each result through verbatim (`met`/`not_met`/`partial`/
  `unclear`/`not_applicable`). The overall recommendation/route/letter follows from
  whether required criteria are met, per policy `result_if_missing`.
- **Current vs stale**: records with `documents.is_current = 1` (or benchmarks whose
  `effective_start..effective_end` covers the service/reporting date) control; stale /
  expired / `is_current = 0` records are the *excluded/exception* records, never the basis.
- **Ordering & precision**: obey the template exactly — e.g. lists "ascending by
  document_id", "alphabetical", CPT lists sorted ascending, currency rounded to cents,
  ratios to the stated decimals, `null` (not `""`) for absent modifiers.

## 5. Build `basis_audit` (shared across all archetypes)

`basis_audit` has the same four keys everywhere:
- `source_precedence` — the enum for this archetype (table in §1).
- `controlling_record_ids` — environment record IDs that directly produce the result,
  in operational evidence order (e.g. the current documents, the chosen benchmark rows,
  the appeal + documented trial, the queue rows).
- `exception_record_ids` — the gap/exclusion records that explain what was left out or
  drove the route: criteria/route gaps and missing-info tokens **before** stale/excluded
  records when both appear.
- `precedence_record_order` — controlling + exception records listed in
  source-precedence order, highest priority first.

## 6. Emit JSON only

Output exactly one JSON object matching the template's shape and key order. No markdown,
no comments, no prose outside the JSON. Before finishing, run the checklist in
`reference/task_playbooks.md` (§ "Validation checklist"): all required keys present,
every enum value inside the allowed set, list ordering correct, numeric precision and
date formats correct, `null` where required, and no extra keys when the template
forbids them.
