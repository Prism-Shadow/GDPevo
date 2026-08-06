---
name: payer-ops-structured-determination
description: >-
  Produce the exact structured JSON deliverable for a Northstar-style payer-operations
  task by reading a shared read-only case environment. Use this when a task hands you a
  target business ID (a case, appeal, claim, peer-to-peer event, or finance queue), a
  read-only operations environment (a SQL query endpoint plus business GET endpoints),
  and a JSON answer template to fill. Covers prior-authorization / UM nurse
  determinations, coverage-exception appeals with manufacturer-assistance intake, claim
  repricing against rate benchmarks, peer-to-peer closures, and margin-queue analysis.
---

# Payer-operations structured determination

You are acting as a payer-operations analyst (UM nurse, appeals coordinator, payment-integrity
analyst, peer-to-peer coordinator, or UM-finance analyst). The task gives you one target
business entity and an **answer template**, and asks for a single JSON object that a downstream
team will act on. Your job is to pull the relevant records from the shared environment, apply
the operational decision rules, and emit JSON that matches the template's contract exactly.

Getting a high score depends on two things equally: **the right business decision** and **exact
conformance to the output contract** (every required field, correct enum spelling, correct
ordering, correct numeric precision, `null` vs `""`). Treat both as first-class.

## Inputs you are given

- `prompt.txt` — the narrative request and the requester role.
- `payloads/task_context.json` — the target business ID(s), reporting/effective date, and any
  memo that pins down definitions, thresholds, row IDs, or windows to use. **Read the memo
  carefully — it often supplies the exact constants and the scope filter for the answer.**
- `payloads/answer_template.json` — the authoritative output contract: required top-level keys,
  field types, enum choices, ordering rules, and numeric precision.
- The task's environment-access notes — the base URL, auth credentials, and the list of allowed
  read-only endpoints (a SQL query endpoint plus business GET endpoints). Use exactly the access
  the task provides. Do **not** read environment source files, generated data files, SQLite
  files, manifests, or setup scripts — query the API/SQL only.

## Workflow

1. **Parse the contract first.** From `answer_template.json`, list every required top-level key,
   its type, its enum choices, its ordering rule, and its precision. This list is your
   checklist; you will verify against it before finishing.

2. **Confirm the data model.** Retrieve the environment's table/schema listing so you know the
   real table and column names before writing queries. The environment is a small relational
   model of payer operations — see `reference/data_model.md`.

3. **Gather everything tied to the target.** Query by the target business ID across every
   relevant table (case, member, plan, provider, policy + policy_criteria, case_criteria,
   request_lines, documents + document_facts, authorizations, appeals, assistance_screen,
   drug_trials, claims + claim_lines, payment_benchmarks, p2p_events, service_margin). Pull the
   raw rows before deciding anything. Never invent an ID, amount, date, or status — every value
   in your answer must trace to a row you retrieved.

4. **Identify the task family and apply its decision rules.** Match the request to one of the
   families in `reference/task_families.md` (prior-auth determination, appeal + assistance,
   claim repricing, peer-to-peer closure, margin queue) and derive each field from the recorded
   facts using the rules there.

5. **Fill `basis_audit`.** Almost every template requires a `basis_audit` object. Fill all four
   required keys using `reference/basis_audit.md`: the `source_precedence` rule for the family,
   the record IDs that control the result, the gap/exception record IDs, and the
   precedence-ordered union of both.

6. **Format to the contract, then self-verify.** Produce exactly one JSON object with only the
   required keys, correct types, exact enum strings, the ordering each list field specifies, and
   numbers rounded to the stated precision. Then walk your checklist from step 1 field by field.

## Core rules that recur across every family

- **Current beats stale.** Records carry a currency/recency signal (e.g. `documents.is_current`,
  or a benchmark's `effective_start`/`effective_end` window vs. the service date). Records that
  are current and on-point are the *evidence/controlling* records and drive the result; records
  that are superseded, expired, closed, or off-topic are *excluded/exception* records. A paid
  amount or prior value that matches a stale record is a signal the stale record was wrongly
  used.

- **Criteria come from the case, not your judgment.** When the template asks for criteria
  results, read them from `case_criteria` for the required criterion IDs and map the recorded
  `result` onto the template's enum. Let the overall pattern of criteria (all met / one not_met /
  partial / unclear) drive the recommendation, route, letter type, and next action.

- **Dates anchor on the governing event, not the reporting date.** When you compute a deadline
  (e.g. an internal appeal window), count from the date of the event that starts the clock (the
  adverse-determination / decision / denial date on the record), using the exact window the memo
  or policy states.

- **Follow ordering rules literally.** Ascending ID, ascending code, alphabetical by name, "order
  shown in choices", source order, queue-row order, claim-line order — whatever the field
  specifies. Ordering of substantive list fields is scored.

- **Numbers must be exact.** Honor the stated precision (cents for currency, the stated decimal
  places for ratios). Compute totals by rolling up the lines/rows you priced; do not eyeball.
  Use `null`, not `""`, for a genuinely absent value (e.g. a missing modifier).

- **Output discipline.** Exactly one JSON object, only the required keys, no markdown, no prose
  outside the JSON.

## Self-verification checklist (do this before returning)

- [ ] Every required top-level key is present, and no field the contract forbids is added.
- [ ] Every enum value is spelled exactly as one of the allowed choices.
- [ ] Every ID, amount, date, and status traces to a retrieved record.
- [ ] Each list field is ordered exactly as its ordering rule states.
- [ ] Numbers match the required precision; totals equal the sum of their parts.
- [ ] `null` is used (not empty string) for absent values.
- [ ] `basis_audit` has all four keys, the correct `source_precedence`, and real record IDs.
- [ ] Any threshold/window/definition from the task memo was applied exactly as written.

See `reference/data_model.md`, `reference/task_families.md`, and `reference/basis_audit.md`.
