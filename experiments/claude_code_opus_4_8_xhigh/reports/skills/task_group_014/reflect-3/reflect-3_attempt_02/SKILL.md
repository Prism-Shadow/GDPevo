---
name: payer-ops-determination
description: >-
  Use for Northstar-style payer-operations "structured determination" tasks: read a
  prompt plus task_context.json and answer_template.json, query a shared read-only
  payer-operations data environment (cases, members, plans, policies, criteria,
  documents, authorizations, appeals, drug trials, assistance screens, claims,
  payment benchmarks, P2P events, service-margin rows), apply the business rules, and
  return exactly one strict JSON object matching the template — including a basis_audit
  trail. Covers prior-authorization nurse determinations, pharmacy coverage
  appeals + manufacturer-assistance intake, claim repricing/benchmark validation,
  peer-to-peer (P2P) final summaries, and finance margin-queue analyses.
---

# Payer-Operations Structured Determination

A task in this family gives you a business target (a case / appeal / claim / queue id),
access to a shared payer-operations data environment, and a strict output contract. Your
job is to pull the relevant records, apply the operational rules, and emit one JSON object
that matches `input/payloads/answer_template.json` exactly.

The specific business decision differs per task, but the **shape of the work is always the
same**. Follow this procedure.

## 1. Read the three inputs before touching the environment

- **`prompt.txt`** — the business ask and any special instructions (ordering, null rules,
  currency rounding, date-window rules, which records to include/exclude).
- **`payloads/task_context.json`** — the target business id(s), the requester role, the
  reporting/as-of date, environment access details, and a `local_memo`/`finance_memo`
  that often states the exact rule to apply (a cost definition, a threshold, an appeal
  window, a list of row ids in scope). Treat the memo as authoritative.
- **`payloads/answer_template.json`** — the required top-level keys, every field's type,
  enum choices, ordering rule, numeric precision, date format, null convention, and
  whether extra fields are allowed. This is your checklist; build to it literally.

Use the environment access details **as provided in the task inputs**. Access is read-only:
query records, never modify or inspect raw source/build/database files directly.

## 2. Discover the schema, then pull everything about the target

- Ask the environment for its table list/columns first; treat the live schema as ground
  truth (see `references/data_model.md` for the stable relational model and joins).
- Pull the target row, then every related row by joining on the case/claim/appeal id (and
  through `member -> plan`, `case.policy_id -> policies -> policy_criteria`, etc.).
- Pull **all** candidate records for the decision — including the ones you will reject.
  Stale/superseded/expired/out-of-scope records are not noise; several fields explicitly
  ask you to name what you excluded and why.

## 3. Derive each field from its authoritative source

Work field-by-field down the template. The per-family derivation rules — criteria results,
overall decision/route/letter/next-action, authorization block, evidence vs. excluded
documents, appeal routing + packet gaps + assistance, benchmark selection + line
repricing, P2P outcome + appeal-deadline math, and margin/threshold routing — are in
`references/field_playbook.md`. Core principles that hold across the whole family:

- **Copy graded facts from the record, don't re-adjudicate.** Per-criterion results,
  authorization numbers/units/dates, appeal paths/deadlines/owners, benchmark amounts,
  margin inputs — read them straight from the environment.
- **Current beats stale.** A `documents.is_current` / effective-date / "most recent
  applicable" flag separates the records you rely on from the ones you exclude. Relied-on
  records populate the evidence/controlling lists; excluded records populate the
  excluded/exception lists.
- **Prefer the most specific, current match** when choosing among candidate rate/benchmark
  rows: match on payer + plan type + service domain + CPT + modifier, effective on the
  service date. Reject expired or wrong-source rows and report which source was rejected.
- **Compute derived numbers yourself, precisely**, then round to the stated precision.
  Cross-check that line-level numbers sum to the totals.

## 4. Always fill `basis_audit`

Every task's output includes a `basis_audit` object with four keys:

- `source_precedence` — pick the one enum value describing the precedence rule this task
  turned on (current-over-stale, appeal-before-assistance, effective-benchmark-by-date,
  new-P2P-information, margin-threshold-then-charge-sensitivity, or
  appeal-deadline-then-clinical-then-payment-integrity). Match it to the decision you made.
- `controlling_record_ids` — the environment record ids that directly drove the result
  (the current evidence docs / chosen benchmark rows / the P2P event / the in-scope rows).
- `exception_record_ids` — the gap/exception/excluded records that explain an exclusion,
  denial, missing information, or routing (stale exports, undocumented-failure trials, the
  expired benchmark, a denial record, charge-sensitive rows). List criteria/route gaps
  before stale/excluded records.
- `precedence_record_order` — the controlling and exception ids together, highest priority
  first per the `source_precedence` rule (controlling records ahead of exceptions).

Use real ids that exist in the environment.

## 5. Emit and self-verify

Return JSON only — no prose, no markdown fences, nothing outside the object.

Before finishing, run the checklist in `references/output_checklist.md`. In particular:
match enum spellings exactly; include every required key and (when the template forbids
extras) no others; sort each list by its stated ordering rule and de-duplicate; obey each
field's numeric precision; use `null` (not `""`) for absent modifiers and `null` for
non-applicable dates; format dates as `YYYY-MM-DD`; and re-run every calculation to confirm
totals and derived values are internally consistent. You are your own reviewer — verify by
re-reading the template and re-deriving from the records, not by guessing.
