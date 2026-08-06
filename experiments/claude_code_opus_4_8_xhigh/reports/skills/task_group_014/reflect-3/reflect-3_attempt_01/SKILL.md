---
name: payer-ops-case-determination
description: >-
  Produce a structured JSON determination for a Northstar-style health-plan
  "payer operations" case by reading the case's records out of the shared
  operations data environment and reasoning over policy criteria, evidence,
  and business rules. Use when a task asks for a JSON determination /
  disposition / repricing packet / summary for a prior-authorization,
  coverage-appeal, claim-payment-integrity, peer-to-peer, or
  finance/margin-queue work item, and gives you (a) a target business id, (b)
  access to a SQL-queryable operations environment, and (c) an
  answer_template that fixes the required output shape.
---

# Payer-ops case determination

These tasks all have the same shape: a payer-operations analyst needs one
**JSON object** that resolves a single work item (a case, claim, appeal,
peer-to-peer event, or finance queue), grounded entirely in records stored in
a shared relational operations environment. Your job is to pull the right
records, apply the governing policy/business logic, and emit JSON that matches
the task's `answer_template` exactly.

The work is retrieval + rule application, not judgment calls. For almost every
output field there is a specific record (or a small computation over records)
that determines the value. Find that record; don't guess.

## Inputs every task gives you

1. **`prompt.txt`** — the business ask and the target id.
2. **`task_context.json`** (or similar) — the target business id, the
   requester role, the reporting date, any finance definitions/thresholds,
   and the environment access to use.
3. **`answer_template.json`** — the authoritative output contract: required
   keys, enum choices, ordering rules, precision, and null conventions.
4. **Environment access** (provided with the task) — a base URL, an auth
   token, a **read-only SQL query endpoint**, and a set of **business read
   endpoints**. Use whatever the task hands you; never hardcode credentials or
   assume endpoints from another task. Do not read raw environment source
   files, generated data files, DB files, manifests, or setup scripts — go
   through the query/read endpoints only.

## Workflow

1. **Read all three input files first.** Identify the task *shape* (prior
   auth / appeal / claim repricing / peer-to-peer / margin queue) and the
   target business id. The `answer_template` is your spec — skim every field,
   enum, ordering rule, and precision note before querying.
2. **Confirm the schema.** List the available tables/columns from the
   environment before writing queries, so you use exact table and column
   names. See `references/data_model.md` for the data model these
   environments typically expose and how the tables join.
3. **Resolve the anchor row**, then join outward only as the template needs:
   the case/claim/appeal/queue row → member → plan, provider, policy →
   policy_criteria, and the case-specific evidence tables (case_criteria,
   request_lines, documents + document_facts, authorizations, appeals,
   drug_trials, assistance_screen, claim_lines, payment_benchmarks,
   p2p_events, service_margin).
4. **Apply the shape's decision logic.** See
   `references/task_playbooks.md` for a field-by-field playbook per shape.
5. **Assemble JSON to the template contract** (see Output rules below).
6. **Self-check** every field against the template before returning: required
   keys present, no extra keys (templates usually forbid extras), enums valid,
   orderings applied, precision/null conventions honored, list contents
   justified by a record.

## Output rules (apply to every task)

- **Return only the JSON object.** No markdown, prose, or commentary around it.
- **Exactly the required keys.** Include every required top-level key; when the
  template says additional fields are not allowed, add nothing extra.
- **Enums are closed sets.** Every enum-typed value must be one of the listed
  choices, spelled exactly.
- **Orderings are explicit and graded.** Common ones: ascending by id
  (e.g. document_id, CPT code), alphabetical by value, source-row order (use
  the exact order given in context, e.g. a list of queue row ids), and
  claim-line / line_number order. Read the ordering note on each list field.
- **Null vs empty string.** Use `null` (not `""`) for an absent scalar such as
  a missing modifier. Use `[]` for a list only when the rule says an empty
  list is allowed.
- **Numeric precision matters.** Round to the precision the field states
  (e.g. currency to 2 decimals, ratios to 4). Compute at full precision and
  round once at the end.
- **`criteria_results`** maps the governing policy's criterion ids to their
  per-case result, taken from the case's criteria records (values such as
  `met` / `not_met` / `partial` / `unclear` / `not_applicable`).
- **Current vs stale evidence.** Documents carry a currency flag; treat
  current documents as the evidence relied on and non-current / superseded /
  stale exports as excluded. This "current over stale" split recurs and is
  often the deliberate trap in the data.
- **`basis_audit`.** Populate all four keys and keep it well-formed:
  - `source_precedence` — the governing precedence rule for the shape (see the
    selection table in `references/task_playbooks.md`).
  - `controlling_record_ids` — the environment record ids that directly drive
    the result, in operational evidence order.
  - `exception_record_ids` — the gap/exclusion records that explain
    exclusions, denials, missing info, or route priority (criteria/route gaps
    before stale/excluded records when both appear).
  - `precedence_record_order` — the controlling + exception records listed in
    source-precedence order, highest priority first.

## Habits that keep these correct

- Prefer the record over inference. If a field has a home column (an auth
  number, an appeal deadline, an outcome, a benchmark version), read it
  directly rather than deriving it.
- Watch for planted distractors: superseded rate schedules, non-current
  documents, duplicate/near-duplicate rows for other CPTs or plan types, and
  "mentioned but not documented" items. Filter by the exact
  payer/plan_type/service_domain/cpt/modifier/date the case calls for.
- When a criterion is `partial`, the gap is a **specific** missing
  sub-document, not the whole category — name the specific item.
- Compute deadlines from the **operative event date** (e.g. the date an
  adverse determination became final), using the window the task states — not
  from the reporting date.
- Distinguish the **formal required set** (what a policy/packet requires) from
  the **case-specific gaps** (what is actually missing here); they are
  different fields with different contents.

## Reference files

- `references/data_model.md` — the operations data model (tables, key columns,
  join graph, and the record each field type comes from).
- `references/task_playbooks.md` — per-shape, field-by-field decision logic and
  the `source_precedence` selection table.
