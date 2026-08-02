---
name: northstar-payer-ops-determination
description: >
  Produce a structured JSON determination for a Northstar Health Plan payer-operations
  work item (UM prior-auth nurse review, pharmacy coverage appeal + manufacturer
  assistance intake, payment-integrity claim repricing, peer-to-peer closure, or
  UM-finance margin-queue review) by reading the task's own answer_template, querying
  the shared read-only payer-operations environment, and mapping the environment
  records into the exact output contract. Use whenever a task hands you a
  prompt.txt + payloads/task_context.json + payloads/answer_template.json referencing
  a Northstar / payer-operations environment reachable at <TASK_ENV_BASE_URL> with a
  POST /sql/query endpoint.
---

# Northstar Payer-Operations Determination

You are answering a single Northstar Health Plan payer-operations work item. The
task gives you a target **business id** (a case / appeal / claim / P2P / queue id)
and a strict JSON **answer_template**. Every answer is *derived from records already
present in the environment* — the environment pre-stages criteria results,
recommended authorizations, appeal packets, benchmarks, and margin rows. Your job is
to **find the right records for the exact target, apply light operational logic, and
render them into the template's exact shape** — including the shared `basis_audit`
audit trail that every template requires.

Do not invent facts. If a value is not derivable from the environment, re-query
before guessing.

## 1. Read the task contract first

Read all three input files before touching the network:

- `input/prompt.txt` — the narrative ask, the requester role, and any special rules
  (e.g. "180-day internal appeal window", "use null for absent modifiers", "do not
  inspect database/source files directly", "JSON only").
- `input/payloads/task_context.json` — the machine-readable target: `target_business_id`
  (and sometimes `target_appeal_id`), `reporting_date`/as-of date, service domain or
  work type, environment connection block, and often a `local_memo`/`finance_memo`
  with the operative definitions (thresholds, row ids, cost formulas, deadlines).
- `input/payloads/answer_template.json` — **the authority on output shape.** It lists
  the required top-level keys, per-field types, enum `choices`, list `ordering` rules,
  numeric precision, date format, and whether extra fields are allowed
  (`additional_fields_allowed` / `additional_properties`). Build your answer to this
  file, not to your memory of a prior task — future tasks may add or drop fields.

Extract and hold onto: the target id, the as-of date, every required key, every enum
choice list, every ordering rule, numeric precision, and the `additional_*` flag.

## 2. Reach the environment (read-only)

Connection details come from `environment_access.md` and the `environment` block of
`task_context.json` — read them from there rather than hardcoding (base URL / port /
token may differ per deployment). As observed:

- Base URL: the value of `<TASK_ENV_BASE_URL>` (e.g. `http://task-env:9014/`).
- SQL: `POST /sql/query`, header `Authorization: Bearer <token>` (e.g.
  `pa-review-token-014`), JSON body `{"sql": "SELECT ..."}`. Only `SELECT`, `WITH`,
  and `PRAGMA table_info` are accepted; results cap at 500 rows.
- Business GET endpoints (see `reference/environment.md`) return JSON and, in practice,
  do not require the token — but sending it is harmless.

**Safety / rules that appear in prompts:** use *only* the network environment. Never
read the environment's source files, generated data files, SQLite files, manifests, or
setup scripts directly, even if present. Treat the environment as read-only — non-SELECT
SQL is rejected anyway.

Start by confirming the schema with `GET /api/tables` (or `PRAGMA table_info`). The full
table/column catalog and endpoint list are in **`reference/environment.md`**.

## 3. Gather records for the EXACT target only

The environment holds hundreds of distractor rows (≈160 cases, decoy rate schedules
named "…Distractor Schedule", and benchmark rows belonging to *other* task namespaces).
Always filter to your exact target business id, and when several records look eligible,
disambiguate by the operative keys (payer + plan_type + service_domain + cpt + modifier
+ effective date window, or the explicit row-id list in the memo). Never let a distractor
into the answer.

Fastest paths:

- **Case-linked work** (nurse review, appeal, P2P): `GET /api/cases/{case_id}` returns a
  single `case` object that bundles member, provider, plan, `criteria` (joined with the
  policy criteria + `result_if_missing`), `documents`, `document_facts`, `request_lines`,
  `authorizations`, `appeals`, `assistance_screen`, `drug_trials`, `p2p_events`, and
  `claims`. This is usually all you need for one case.
- **Claims / benchmarks:** query `claims`, `claim_lines`, and `payment_benchmarks` by id;
  use `GET /api/rate-schedules` to see benchmark sources.
- **Margin queue:** query `service_margin` for the exact `month_id`s the memo lists.
- **Appeals:** `GET /api/appeals` or query `appeals`, `drug_trials`, `assistance_screen`.

## 4. Identify the task family and derive each field

Recognize the family from the answer_template's required keys / criterion-id prefixes /
enums, then follow the matching recipe in **`reference/task_patterns.md`**:

| Signal in the template | Family | Core sources |
|---|---|---|
| `recommendation`, `authorization`, `PT-*` criteria, `evidence_documents` | UM nurse prior-auth determination | cases, case_criteria, documents(`is_current`), authorizations |
| `appeal_path`, `documented_failures`, `assistance`, `DRUG-*` criteria | Pharmacy appeal + assistance intake | appeals, drug_trials(`documented`), case_criteria, assistance_screen |
| `benchmark_source`, `lines`, `recovery_amount`, `paid_total` | Payment-integrity claim repricing | claims, claim_lines, payment_benchmarks |
| `p2p_outcome`, `PET-*` criteria, `missing_pet_factors`, `internal_appeal_deadline` | Peer-to-peer closure | p2p_events, case_criteria, documents, authorizations |
| `revenue_to_cost_ratio`, `below_threshold_segments`, `gap_to_120pct` | UM-finance margin queue | service_margin |

The environment usually pre-stages the outcome: `case_criteria.result`,
`authorizations.status` (`recommended_approval`/`denied`), `appeals.appeal_path`/`.owner`,
`p2p_events.outcome`/`.final_status`. Read those signals; apply only the small computations
the template demands (ratios, date arithmetic, current-vs-stale filtering, sorting,
mapping to the template's enums). Full formulas are in `reference/task_patterns.md`.

## 5. Build `basis_audit` (required by every template)

Every answer_template contains a `basis_audit` object with the same four keys. It is a
business audit trail, not free text:

- `source_precedence` — pick the one enum choice matching the family (each family maps to
  exactly one; see the table in `reference/task_patterns.md`).
- `controlling_record_ids` — the environment record ids that *directly drive* the result,
  in operational evidence order (e.g. the current evidence docs; the appeal + documented
  trials; the claim lines then the current benchmarks; the P2P event + clinical note; the
  queue rows in listed order).
- `exception_record_ids` — the gap/exclusion records that explain what was set aside:
  criteria/route gaps *before* stale/excluded records when both appear (e.g. the stale
  export; the undocumented trial + missing packet field; the stale benchmark; the unmet
  criterion + missing factors; the below-threshold row).
- `precedence_record_order` — the controlling records then the exception records, listed
  highest-priority-first under the chosen precedence rule (the "what superseded what"
  trail; it may be a curated subset — e.g. the winning benchmarks then the stale one,
  not every claim line).

Use the real environment ids for records, and the template's own enum tokens (e.g.
`household_income_proof`, `PET-FACTOR`, `prior_equivocal_spect`) where the driver is a
requirement/criterion rather than a stored row.

## 6. Format, validate, and emit JSON only

Before returning, verify against the template:

- Output is **exactly one JSON object, no prose/markdown/comments** outside it.
- The top-level key set matches `required_top_level_fields` exactly. If
  `additional_fields_allowed` is `false`, include **no** extra keys; if extras are
  "allowed but not evaluated," still prefer the minimal exact set.
- Every enum value is one of the template's `choices`; every criterion map has exactly
  the `required_keys`.
- Lists obey their stated `ordering` (ascending id, alphabetical, claim-line order,
  the memo's row-id order, or "order shown in choices"). Empty list vs `null`: use what
  the field says (e.g. modifiers → `null`, not `""`; "empty list only if none").
- Numbers use the stated precision — currency rounded to 2 decimals (as JSON numbers,
  dollars), ratios to 4 decimals. Recovery/underpayment = corrected − paid.
- Dates are `YYYY-MM-DD`. Date windows are counted from the record date the rule names
  (e.g. an internal-appeal deadline is *N days from the final adverse determination /
  P2P date*, not from the reporting date).
- Recompute derived numbers from source rows; re-check that no distractor id slipped in.

See `reference/task_patterns.md` for the per-family derivation details and
`reference/environment.md` for the schema and endpoint catalog.
