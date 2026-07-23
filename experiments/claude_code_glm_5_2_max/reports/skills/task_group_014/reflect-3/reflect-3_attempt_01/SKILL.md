---
name: northstar-payer-ops
description: Solve Northstar Health Plan payer-operations structured-output tasks — UM prior-authorization determinations, pharmacy appeals + manufacturer-assistance intake, payment-integrity claim repricing, peer-to-peer (P2P) final summaries, and therapy margin-queue summaries — by querying the shared payer-operations environment and returning exactly one JSON object that matches the task's answer_template. Use when a task names Northstar Health Plan, gives a prior-auth / appeal / claim / P2P / margin-queue business ID, points at a shared payer-operations environment, and asks for JSON matching an answer_template.
---

# Northstar Payer-Operations Determination Skill

This skill solves Northstar Health Plan payer-operations tasks. Each task asks for **one JSON
object** that conforms to a provided `answer_template.json`. The work is: read the task inputs,
query the shared environment for the relevant records, apply the business rules and policy
criteria, and emit the structured result with a `basis_audit` trail.

## When to use

Use this skill when a task matches this shape:
- It names **Northstar Health Plan** and a business/case ID (prior-authorization case, appeal,
  claim, P2P case, or margin queue).
- It points at a shared payer-operations environment and gives SQL + business-endpoint access.
- It requires JSON conforming to an `answer_template.json`, including a `basis_audit` object.

The five task families this covers:
1. **UM nurse prior-authorization determination** (physical therapy, etc.)
2. **Pharmacy coverage appeal + manufacturer-assistance intake** (specialty drug)
3. **Payment-integrity claim repricing** (imaging claim against a rate benchmark)
4. **Peer-to-peer (P2P) final authorization summary** (with appeal deadline if adverse)
5. **Therapy margin-queue summary** (finance margin analysis by payer segment)

## Inputs to read first

Read these in order before querying anything:
1. `prompt.txt` — the request, the target business ID, and the "as-of" date.
2. `payloads/task_context.json` — target IDs, requester role, reporting date, finance/rule
   definitions, and an `environment` block with base URL + SQL endpoint + bearer token.
3. `payloads/answer_template.json` — the **exact** required top-level fields, nested object
   shapes, enum choices, list-ordering rules, and numeric precision. This is the contract.
4. `environment_access.md` — the allowed endpoints and the SQL bearer token.

Treat the template as authoritative: every enum value, ordering rule, precision rule, and
"additional_fields_allowed" flag comes from it. Do not invent fields; do not add fields when
`additional_fields_allowed` is false.

## The environment

The shared payer-operations environment is a read-only data store. Access it **only** through
the endpoints listed in `environment_access.md` and the task's `environment` block — get the
base URL, SQL path, and bearer token from there (do not assume they are fixed).

- **SQL endpoint** (`POST /sql/query`, bearer token required): accepts a JSON body
  `{"sql": "<SELECT ...>", "params": {...}}` (the request field is `sql`, not `query`).
  It returns `{"columns": [...], "rows": [...], "row_count": N, "max_rows": 500, "limited": bool}`.
  Filter with `WHERE` on the target IDs; results cap at 500 rows. Use it to join and filter
  across tables. Inline string literals work; `params` is optional.
- **Business GET endpoints** (open, no auth): `GET /api/tables` (schema), `/api/cases`,
  `/api/cases/{id}`, `/api/policies`, `/api/policies/{id}`, `/api/documents/{id}`,
  `/api/rate-schedules`, `/api/appeals`. Use these for quick single-record lookups.

Do **not** inspect environment source files, SQLite files, manifests, or setup scripts — only
the HTTP endpoints. The full table schema is in `schema_reference.md`.

## Core workflow

1. **Identify the target.** Pull the target business ID(s) and the "as-of" date from
   `task_context`. Note the requester role and service domain — they pick the task family.
2. **Load the schema.** Skim `schema_reference.md` so you know which tables hold which facts.
3. **Gather the records** for the target ID. Always pull the case row plus the records the
   template's fields imply. A typical gather set:
   - `cases` (case row: stage, status, policy_id, service_domain, urgency, due_date)
   - The line table for the family: `request_lines` (PA/P2P), `claim_lines` (claim repricing),
     `service_margin` (margin queue).
   - `policies` + `policy_criteria` (criterion IDs, text, `approval_required`, `result_if_missing`)
   - `case_criteria` (the **per-case criterion results** — usually maps directly to
     `criteria_results`; note `gap_description` and `reviewer_scope`)
   - `documents` + `document_facts` (evidence; `is_current` flags current vs stale)
   - The decision/event table for the family: `authorizations` (PA/claim), `p2p_events` (P2P),
     `appeals` + `assistance_screen` + `drug_trials` (pharmacy appeal), `payment_benchmarks`
     (claim repricing), `service_margin` (margin queue).
   - `members` + `plans` (plan_type, product, state — needed for benchmark selection and appeal
     rules) and `providers` when relevant.
4. **Apply the business rules / criteria.** Map each criterion to met/not_met/partial/unclear
   from `case_criteria`; derive the recommendation, route, and letter from the criteria +
   `result_if_missing` + case stage + the decision record. See `task_patterns.md`.
5. **Compute derived numbers** with the template's precision: currency to 2 decimals (cents),
   ratios to 4 decimals, integers as integers. Re-check each line and the totals reconcile.
6. **Build the `basis_audit`.** Pick the one `source_precedence` rule that matches the task,
   then list `controlling_record_ids`, `exception_record_ids`, and `precedence_record_order`.
   This is the most error-prone field — read `basis_audit_guide.md` before filling it.
7. **Emit exactly one JSON object** matching the template. No markdown, no prose, no comments
   outside the JSON. Respect every enum, ordering, precision, and null rule.

## Output rules (apply to every task)

- **One JSON object only.** No surrounding text, no code fences, no trailing prose.
- **Enums exact.** Use the exact string from the template's `choices` (lowercase, underscores).
- **Ordering.** Lists with an ordering rule must follow it: ascending document_id / CPT code /
  criterion ID; queue rows in `task_context` row order; claim lines in claim-line order;
  alphabetical enum lists; payer-appeal items before assistance items; etc.
- **Precision.** Currency → 2 decimals (dollars rounded to cents). Ratios → 4 decimals.
  Counts/units → integers.
- **Null, not empty.** Use JSON `null` (never `""`) for an absent modifier or a field that is
  "null only when no ... applies." Use an empty list `[]` only where the template allows it
  (e.g., `unresolved_criteria` when none remain, `exception_record_ids` when none exist).
- **No extra fields** when `additional_fields_allowed` is false.
- **Reconcile totals.** Line `recovery_amount` sum must equal the claim-level `recovery_amount`;
  `correct_allowed_total` must equal the sum of line `correct_allowed_amount`s; margin
  `below_threshold`/`charge_sensitive` lists must match the per-row flags.

## Test-time solving

Solve directly from the environment and the template. There is **no** scoring, feedback, or
"judge" endpoint available at solve time — do not attempt to call one and do not rely on any.
Produce the single best JSON answer from the gathered records and the rules below.

## Supporting files

- `schema_reference.md` — the full environment table schema and the SQL request/response shape.
- `basis_audit_guide.md` — `basis_audit` semantics: the six `source_precedence` rules, what goes
  in `controlling_record_ids` vs `exception_record_ids`, and the ordering rules.
- `task_patterns.md` — per-task-family field-derivation rules (how each output field is derived
  from environment records). These are general rules, not specific answers.
