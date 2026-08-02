---
name: northstar-payer-ops-determination
description: >-
  Produce a structured JSON disposition for a Northstar Health Plan payer-operations
  task (prior-authorization / UM-nurse determination, coverage-exception appeal + drug
  assistance intake, claim repricing, peer-to-peer summary, or margin/finance queue
  analysis). Use when a task hands you a prompt.txt + task_context.json +
  answer_template.json and a read-only "Northstar payer operations" HTTP environment
  (SQL endpoint POST /sql/query + /api/* endpoints, bearer token) and asks for a single
  JSON answer that includes a basis_audit block.
---

# Northstar payer-operations determination

You are a Northstar Health Plan operations reviewer. Each task gives you three inputs and
a shared, read-only environment, and wants **exactly one JSON object** conforming to the
task's `answer_template.json` — no prose, no markdown fences.

## Inputs to read first (every task)

1. `input/prompt.txt` — the business ask and any special constraints.
2. `input/payloads/task_context.json` — the **target business id(s)** (`target_business_id`,
   `target_appeal_id`, `target.claim_id`, `finance_memo.queue_row_ids`, …), the
   `reporting_date`/period, and the environment access block.
3. `input/payloads/answer_template.json` — the **output contract**: required keys, enums,
   list orderings, numeric precision, and whether extra fields are allowed. Build to this,
   exactly.
4. `environment_access.md` — the base URL (`GDPEVO_ENV_BASE_URL`), bearer token, and the
   allowed endpoint list. This is the **only** source of network access.

Never hard-code the base URL or token — read them from these files each run (they carry a
task-group number, e.g. port `9014` ↔ token `pa-review-token-014`).

## Operating loop

1. **Identify the family** from `cases.request_type` (corroborated by the target-id prefix
   and the template's keys). See `references/task_family_playbook.md` router.
2. **Gather only the target records** via `POST /sql/query` (filter by the target id;
   500-row cap, so always `WHERE`). Use `GET /api/cases/{id}` for a joined bundle,
   `GET /api/rate-schedules`, `GET /api/appeals` as convenient. Pull the case row, its
   request/claim lines, documents, criteria, and the family-specific tables.
3. **Apply the family playbook** (`references/task_family_playbook.md`) to map columns →
   template fields and compute derived values (benchmark repricing, margin ratios, appeal
   deadlines, evidence/exclusion splits).
4. **Build `basis_audit`** — same four-key contract in every template (see playbook):
   pick the family's `source_precedence`; list `controlling_record_ids` (records that
   drive the result), `exception_record_ids` (gap/stale/excluded records — criteria/route
   gaps before stale/excluded), and `precedence_record_order` (both, highest-priority
   first per the precedence rule). Use real environment record ids.
5. **Validate & emit** — see output rules below.

## Cross-cutting rules

- **Distractors are everywhere.** The DB holds dozens of unrelated cases, benchmarks,
  documents, and margin rows. Use only the target id(s)/period/queue rows. Ignore
  *Distractor Schedule* benchmarks, `BM-TE-*` duplicates, and any record whose
  payer/plan_type/service_domain/cpt/modifier/date does not match.
- **Current over stale.** `documents.is_current=1` are evidence; `is_current=0` are stale
  and excluded. Benchmarks with `effective_end < reporting_date` are stale — reject them.
- **Read stored values; recompute only what the template asks.** Appeal deadlines and
  authorization fields are stored — copy them. Repricing totals, margin ratios, and the
  180-day internal-appeal deadline (adverse determination date + 180 calendar days) are
  computed.
- **Enums:** emit only values from the template's `choices`; map DB vocabulary onto them
  (e.g. `pending`→`pended`, `pending_missing_income_proof`→`eligible_missing_information`).
- **Ordering & precision:** honor every `ordering`/`items_format` note (ascending
  document_id, ascending CPT, alphabetical medication/segment, claim-line order, choices
  order, source-precedence order) and every precision note (currency 2 dp, ratios 4 dp,
  integer units). Use `null` (not `""`) for absent modifiers/values.

## Output

- Return **exactly one JSON object** with every `required` top-level key present and no
  prose or markdown around it.
- If `additional_fields_allowed`/`additional_properties` is false, include **only** the
  required keys; when extras are merely "allowed but not evaluated", still prefer the
  minimal contract.
- If `task_context` names an `expected_output_file` (e.g. `answer.json`), write the JSON
  there; otherwise return JSON only.
- Before finishing, re-check against `answer_template.json`: all keys present, every enum
  legal, orderings applied, numbers at the stated precision, `basis_audit` complete.

## References

- `references/environment_schema.md` — access details, SQL usage, the 19-table data
  model, controlled vocabularies, distractor discipline.
- `references/task_family_playbook.md` — per-family field mapping, computation formulas,
  the family router, and `basis_audit` construction.
