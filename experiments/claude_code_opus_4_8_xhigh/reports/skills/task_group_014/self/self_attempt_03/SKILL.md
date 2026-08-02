---
name: northstar-payer-ops-determination
description: >-
  Produce a structured JSON determination for a Northstar Health Plan payer-operations
  work item (prior-authorization / UM nurse review, pharmacy coverage appeal + manufacturer
  assistance intake, payment-integrity claim repricing, peer-to-peer close-out, or UM-finance
  margin-queue summary). Use when a task ships an input/payloads/task_context.json plus an
  input/payloads/answer_template.json, points at a shared "Northstar" / "payer operations"
  environment reachable via POST /sql/query (bearer token) and GET /api/* endpoints, and asks
  for JSON conforming to the answer template. Triggers: "UM nurse determination", "prior
  authorization", "coverage appeal", "manufacturer assistance", "claim repricing / payment
  integrity", "peer-to-peer summary", "margin queue", "basis_audit", "source_precedence",
  "pa-review-token".
---

# Northstar payer-operations structured determination

You are handed one payer-operations work item and must return a single JSON object that
exactly matches the task's `answer_template.json`. Every task in this family follows the
same shape: read two payload files, pull the relevant records from a shared read-only
environment, apply the decision rules for the item's family, and serialize the result.

The final numeric/enum values are **case-specific** — never carry values between tasks.
This skill gives you the *procedure and decision rules*, not answers.

## Step 1 — Read the contract before touching the network

Read both payload files first:

- `input/payloads/task_context.json` — gives the **target business id** (`target_business_id`
  / `target.claim_id` / `business_id` / `queue_row_ids`), the `reporting_date` (a.k.a.
  `request_date` / `memo_date` — this is "today" for every deadline and effective-date test),
  the `service_domain`/`work_type`, and any memo with explicit rules (e.g. a stated appeal
  window, a threshold, an ordered list of row ids).
- `input/payloads/answer_template.json` — the **strict output contract**. Extract, verbatim:
  the `required_top_level_fields`, every `enum`/`choices` list, each field's ordering rule,
  numeric precision, and null-vs-empty conventions. Treat `additional_fields_allowed: false`
  as prohibiting any extra key. Do not invent keys or enum values that are not listed.

Identify the **task family** from the target id prefix / `request_type` / `service_domain`
(see `references/task_families.md`). The families are: UM nurse determination, pharmacy
appeal + assistance, payment-integrity repricing, peer-to-peer close-out, finance margin
queue.

## Step 2 — Resolve environment access

The base URL in the payloads is a `<TASK_ENV_BASE_URL>` placeholder. Get the real
connection details from **`environment_access.md`** (the only sanctioned source of network
config), which supplies:

- the base URL (e.g. `GDPEVO_ENV_BASE_URL=...`),
- the bearer token and the exact `Authorization: Bearer <token>` header,
- the allow-listed endpoints.

Use only the listed endpoints and only that token. Do **not** read the environment's source
files, generated data, SQLite/db files, manifests, or setup scripts — several prompts
forbid it explicitly. The environment is read-only (writes are rejected); treat it as the
single source of truth over any stale local copy.

## Step 3 — Pull the records

Two interchangeable access paths (see `references/data_model.md` for the full schema):

- **SQL** — `POST /sql/query` with JSON body `{"sql": "<SELECT ...>"}`. The body key is
  `sql` (not `query`). Only `SELECT` / `WITH` / `PRAGMA table_info` run; results come back as
  `{"columns":[...],"rows":[...],"row_count":N,"max_rows":500}` (cap 500 rows — filter/paginate).
  Start with `GET /api/tables` (or `PRAGMA table_info`) to confirm columns before querying.
- **REST** — `GET /api/cases/{case_id}` returns a bundle (case + criteria with `result` and
  `result_if_missing`, authorizations, appeals, assistance_screen, claims). Also
  `GET /api/cases`, `/api/policies[/{id}]`, `/api/documents/{id}`, `/api/appeals`,
  `/api/rate-schedules`, `/api/portal`.

Pull the target record **and every related record the answer template references**: request
or claim lines, policy + policy_criteria, case_criteria, documents + document_facts,
authorizations, appeals, assistance_screen, drug_trials, p2p_events, payment_benchmarks,
service_margin, members/plans. Query by the exact target id — the environment also contains
`-TE-` (test) and `-D-` (distractor) rows; never let a distractor row leak into an answer.

## Step 4 — Apply the family decision rules

Follow `references/task_families.md` for the family you identified. Recurring principles that
hold across all families:

- **The environment usually records the graded result** — `case_criteria.result`,
  `authorizations.status`/`denial_reason`, `appeals.appeal_path`/`outcome`,
  `p2p_events.outcome`/`final_status`, `assistance_screen.assistance_status`. Read those
  directly and cross-check them against the underlying facts; don't re-derive a grade the
  data already states.
- **Current clinical records beat stale exports.** `documents.is_current = 1` are evidence;
  `is_current = 0` (stale_export / legacy) are excluded. For rate schedules, the controlling
  benchmark is the one whose `[effective_start, effective_end]` window contains the service
  date and whose `payer + plan_type + cpt_code + modifier + service_domain` all match;
  expired/legacy schedules are the stale source you reject, and mismatched "Distractor"
  schedules simply don't match.
- **Map to the template's vocabulary.** Translate raw statuses into the exact enum the
  answer_template allows (e.g. all required criteria met → an "approve"/"approved" family of
  values; a `not_met` criterion whose `result_if_missing = deny` → an adverse/deny family; a
  gap whose `result_if_missing = pend` → a pend/request-information family).

## Step 5 — Build `basis_audit` (present in every template, identical shape)

Four keys: `source_precedence`, `controlling_record_ids`, `exception_record_ids`,
`precedence_record_order`.

- `source_precedence` — pick the one enum value that names your family's governing rule
  (mapping in `references/output_contract.md`).
- `controlling_record_ids` — the environment record ids that **directly determine** the
  result, in operational evidence order (the current documents / effective benchmark / graded
  criteria / disposition record that drove the outcome).
- `exception_record_ids` — the gap/exception records, in **gap order: criteria or route gaps
  before stale or excluded records** (missing-evidence criteria, then stale/expired/excluded
  document or schedule ids, charge-sensitive rows, etc.).
- `precedence_record_order` — the controlling and exception ids merged and re-sorted by
  source-precedence priority, highest first.

Use real record ids drawn from the environment, not invented ones.

## Step 6 — Serialize and self-check

Emit **JSON only** — no markdown, prose, or comments around it. Before returning, verify
against `references/output_contract.md`: every required key present, no extra keys when
disallowed, every enum value in-list, every list ordered exactly as specified (ascending
id / ascending CPT / alphabetical enum / claim-line order / the memo's row-id order),
numbers at the required precision (currency to cents), and `null` (not `""` or `[]`) used
only where the template says a value may be absent.

See the `references/` files for the full data model, per-family recipes, and the output
contract details.
