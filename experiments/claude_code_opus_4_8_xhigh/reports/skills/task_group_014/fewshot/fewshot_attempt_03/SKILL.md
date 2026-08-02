---
name: northstar-payer-ops-determination
description: >-
  Produce a structured Northstar Health Plan payer-operations determination from
  a task packet (prompt.txt + task_context.json + answer_template.json) by
  querying the shared read-only operations environment and returning a single
  JSON object that conforms to the task's answer_template. Covers five recurring
  work types — UM prior-authorization nurse determinations, pharmacy coverage
  appeals + manufacturer-assistance intake, payment-integrity claim repricing,
  peer-to-peer (P2P) final summaries, and UM-finance margin-queue analysis — plus
  their shared basis_audit trail. Use whenever a task references a
  `<TASK_ENV_BASE_URL>` environment with a `POST /sql/query` endpoint and asks for
  JSON matching an answer_template.
---

# Northstar payer-operations determination

You are a Northstar Health Plan operations analyst. Each task gives you a target
business entity (a case, appeal, claim, P2P event, or margin queue) and asks for
one JSON object conforming to a supplied `answer_template.json`. The facts live in
a shared, read-only operations environment you query over the network. Your job is
to fetch the target's records, apply the business rule for its work type, and emit
the JSON — **facts and derivations come from the environment, never from guesses.**

## 1. Read the task packet first

Every task ships three input files (paths given in the prompt, usually under
`input/`):

- `prompt.txt` — the narrative ask, the requester role, and any special rule
  (e.g. "180-day internal appeal window", "currency rounded to cents", "list lines
  in claim-line order"). Read these operative sentences carefully; they override
  defaults.
- `payloads/task_context.json` — the machine-readable target: `target_business_id`
  (and sometimes `target_appeal_id`, `claim_id`, `queue_row_ids`), the
  `reporting_date`/`reporting_period`, and a `local_memo`/`finance_memo` with
  thresholds and scope. **This is the authoritative target identifier and the
  as-of date — use it, not anything inferred.**
- `payloads/answer_template.json` — the exact output contract: required top-level
  fields, nested object keys, enum choices, ordering rules, numeric precision, and
  whether extra fields are allowed. Treat it as a schema you must satisfy exactly.

Do not read environment source files, generated data files, SQLite files,
manifests, or setup scripts even if you can — several prompts forbid it. All facts
come through the HTTP endpoints below.

## 2. Reach the environment

`environment_access.md` (and `task_context.environment`) give the base URL and the
SQL bearer token. Resolve them at run time rather than hardcoding:

- Base URL — the `GDPEVO_ENV_BASE_URL` value in `environment_access.md` (the task
  packet writes it as the `<TASK_ENV_BASE_URL>` placeholder).
- Bearer token — the `Authorization: Bearer <token>` value in
  `environment_access.md`.

Two ways to read data (both allowed):

- **`POST /sql/query`** — send `{"sql": "<one SELECT statement>"}` with the
  `Authorization: Bearer <token>` header. Returns
  `{"columns": [...], "rows": [ {col: val, ...} ], "row_count": N, "max_rows": 500,
  "limited": <bool>}`. Only **one** statement per call (multi-statement or writes
  are rejected as `invalid_sql`), and results cap at 500 rows (`limited: true` means
  truncated — narrow the query). This is the primary, most precise tool.
- **Business REST endpoints** — `GET /api/tables`, `/api/cases`,
  `/api/cases/{id}` (a convenient bundle of the case plus its criteria,
  authorizations, appeals, claims, documents, etc.), `/api/policies`,
  `/api/policies/{id}`, `/api/documents/{id}` (document + its facts),
  `/api/rate-schedules`, `/api/appeals`. Handy for a quick overview; drop to SQL
  when you need exact filtering.

`scripts/nsql.sh "<SELECT ...>"` is a thin helper that resolves the URL/token and
runs one SQL statement. `GET /api/tables` returns the full schema on demand.

**The environment is shared across many tasks.** It contains records for unrelated
cases and distractor reference rows (e.g. benchmark rows that match your keys but
belong to another task, or an expired schedule for the same CPT). Always scope to
your `target_business_id` and the rows directly linked to it by foreign key
(`case_id`, `claim_id`, `appeal_id`, `month_id`, …), and select reference rows
(benchmarks, policy criteria) by their business keys **and** the effective date
window. Reject anything out of scope or out of date — that rejection is often
exactly what `basis_audit.exception_record_ids` and the `stale_source_rejected`
field are asking you to name.

## 3. Identify the work type, then apply its recipe

Match the task to one of five families by its target ID stem, `service_domain`,
`request_type`, and the answer_template's fields. Each family has a deterministic
derivation recipe in **`references/task_families.md`** — read the matching one and
follow it field by field:

| Signal in template / context | Family | Key tables |
| --- | --- | --- |
| `recommendation`, `authorization`, `evidence_documents`, criteria like `PT-*` | **A. UM prior-auth nurse determination** | cases, request_lines, case_criteria, policy_criteria, documents, authorizations |
| `appeal_path`, `documented_failures`, `assistance`, criteria like `DRUG-*` | **B. Pharmacy appeal + assistance intake** | appeals, case_criteria, drug_trials, assistance_screen |
| `benchmark_source`, `paid_total`, `lines[]`, `recovery_amount` | **C. Payment-integrity claim repricing** | claims, claim_lines, cases→members, payment_benchmarks |
| `p2p_outcome`, `missing_pet_factors`, `internal_appeal_deadline` | **D. Peer-to-peer final summary** | cases, request_lines, case_criteria, documents, p2p_events, authorizations |
| `rows[]`, `revenue_to_cost_ratio`, `gap_to_120pct`, `top_issue` | **E. UM-finance margin queue** | service_margin |

The full column list for every table is in **`references/environment.md`**.

## 4. Build the `basis_audit` trail

Every answer includes a `basis_audit` object with the same four keys and the same
enum of six `source_precedence` rules. Fill it from the records you actually relied
on — see the "basis_audit" section of `references/task_families.md` for the
per-family mapping. In short:

- `source_precedence` — the one rule (of the six) that governs your task's dominant
  tension. Each family maps to one rule (current-vs-stale clinical, payer-appeal
  before assistance, effective-benchmark by plan/modifier/date, new P2P
  information, margin-threshold before charge-sensitivity, or
  appeal-deadline→clinical→payment-integrity for a mixed case).
- `controlling_record_ids` — the environment record IDs that directly determine the
  result, in operational evidence order.
- `exception_record_ids` — the gap/exception records that explain exclusions,
  denials, missing info, or route priority; order criteria/route gaps before
  stale/excluded records. When an exception has no standalone row (a missing packet
  field, an unmet criterion, an unsupported factor), use its descriptive
  token/criterion-ID rather than inventing an ID.
- `precedence_record_order` — the controlling + exception IDs listed in
  source-precedence order, highest priority first.

Use the environment's native IDs everywhere (`document_id`, `trial_id`,
`benchmark_id`, `month_id`, `p2p_id`, `appeal_id`, `claim_line_id`, `criterion_id`).

## 5. Output rules (apply to every task)

- Return **exactly one JSON object and nothing else** — no markdown fences, no
  prose before or after.
- Include every key in `required_top_level_fields`/`required_top_level_keys` and
  every required nested key. If the template says `additional_fields_allowed:
  false`, include **no** extra keys.
- Use enum values verbatim from the template's `choices`; never invent a value.
- Ordering: honor each field's stated rule — ascending `document_id`, ascending CPT
  code, alphabetical by name/segment, claim-line order, or the exact
  `queue_row_ids` order. When unsure, re-read the field definition.
- Numbers: JSON numbers, not strings. Round currency to 2 decimals, ratios to 4 (or
  whatever `precision`/`numeric_precision` states). Apply units before rounding
  (e.g. per-line allowed = unit rate × units).
- Use `null` (not `""`) for an absent modifier or an inapplicable value the template
  says to null out.
- Dates: ISO `YYYY-MM-DD`. Do date math in whole calendar days from the stated
  anchor date (e.g. adverse-determination date + 180 days).

## 6. Validate before returning

1. Every required key present; no extras when they're disallowed.
2. Every enum value is in the allowed set.
3. Lists obey their ordering rule and drop out-of-scope/distractor rows.
4. Arithmetic re-checked (totals = sum of lines; ratio = revenue ÷ total_cost;
   recovery = allowed − paid; gap = threshold × cost − revenue).
5. `basis_audit` IDs all appear in the records you queried; precedence order is
   consistent with the chosen `source_precedence`.
6. Output parses as JSON and matches the template's shape exactly.
