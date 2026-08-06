---
name: harborview-clinic-protocol-answers
description: >-
  Use for protocol-bound clinical decision-support tasks against the Harborview
  synthetic-clinic runtime API. Each task names a target case id and provides an
  answer_template.json contract; the job is to retrieve the case from the clinic
  runtime, apply the case's machine-readable clinic protocol, filter out seeded
  distractor records, and emit exactly one JSON object that conforms to the
  template. Covers the recurring families: adult respiratory / CAP assessment,
  pediatric head-injury triage, potassium repletion & escalation, care-management
  routing, and observation-window / protocol-gate retrieval.
---

# Harborview synthetic-clinic protocol answers

A task in this family gives you: (1) a `prompt.txt` naming a **target case id** and
what to decide, and (2) `input/payloads/answer_template.json` — the **exact output
contract**. Network access (base URL + allowed endpoints) is in a separate
`environment_access.md`. Your deliverable is **one JSON object** matching the
template, with no prose around it.

The answer is never a matter of general clinical judgment. Every scored field is
determined by **the case's data in the runtime** plus **the case's protocol** (also
in the runtime). Retrieve both, apply the protocol literally, and format to the
template.

## Golden rules

1. **The template is the contract.** Read `answer_template.json` end to end first.
   Match `required_top_level_keys` exactly, add no extra top-level keys, and for
   every field honor its `type`, `allowed_values` (enums), `precision`/`unit`,
   nullability, and `ordering`. Emit an enum value only if it appears in that
   field's `allowed_values`.
2. **The protocol is the source of truth — not your medical knowledge.** Fetch the
   governing protocol and apply its stated thresholds, codes, triggers, and rules
   verbatim. Do not invent cutoffs or substitute textbook defaults.
3. **The environment is full of distractors.** Decoy cases (`CASE-D30xx`),
   patients (`PAT-D20xx`), and observations tagged `"source": "generated distractor
   feed"` exist to trap you, alongside wrong-code / wrong-status / out-of-window
   rows. Scope strictly to the target `case_id`/`patient_id`, the correct code,
   `status == "final"`, and the correct time window.
4. **Never claim what the record does not show.** Only assert positive findings the
   retrieved evidence supports. Anything not in the record is absent/negative.
   Safety-check booleans encode this (see step 7).
5. **Output is machine-graded.** Return exactly one JSON object — no markdown,
   comments, or explanatory text; ISO-8601 UTC timestamps with trailing `Z`;
   numbers rounded to the stated precision; `null` only where the spec permits.

## Procedure

### 1. Establish identifiers
- `case_id`: from the prompt (and any `required_value`/`expected_constant` in the
  template — they must agree).
- `task_id`: if the template pins it via `expected_constant`/`required_value`, use
  that; otherwise use this run's task identifier (the task/folder name).
- `patient_id`: **do not guess** — read it from the retrieved case record
  (step 2). It is a stable clinic id like `PAT-####`.

### 2. Retrieve the case bundle
`GET {BASE}/api/cases/{case_id}` returns an aggregated bundle and is the backbone
of every task. It contains:
- `case` — `patient_id`, `case_type`, `service_date`, `status`, `summary`.
- `findings` — non-lab facts as `{finding_key, finding_value, source_id}`,
  including **`current_time`** (the clinical review time; source like
  `TASK-CLOCK-*`), symptoms, exam/ECG, and contraindication notes. Use
  `current_time` from here — **not** the wall clock.
- `allergies`, `medications`, `observations`, `imaging`, `care_registry` (and, via
  the collection endpoints, `sdoh` / `problems`).

Supplement with collection endpoints when you need to confirm scoping or list
distractors, e.g. `GET /api/observations?case_id=...` or `?patient_id=...`,
`/api/medications`, `/api/allergies`, `/api/problems`, `/api/imaging`,
`/api/care-registry`, `/api/sdoh`. (`POST /api/query` needs a clinic token that is
usually not provided — rely on the GET endpoints.)

### 3. Retrieve and parse the governing protocol
`GET {BASE}/api/protocols` lists protocols; pick the one whose title matches the
case type, then `GET {BASE}/api/protocols/{protocol_id}` for its **machine-readable
`body`**. The body carries the decision logic: target values, `controlled_codes`
(LOINC / NDC / local codes), urgent / red-flag triggers, `authoritative_statuses`
(`final`), `excluded_statuses`, `ordering`, follow-up hours, and dosing rules.
Treat the live body as authoritative — thresholds are versioned and may differ from
any example in this skill.

See `references/task-families.md` for how each case type maps its protocol body onto
its template fields.

### 4. Filter to the truth set
Before computing anything, reduce the retrieved rows to what actually qualifies:
- **Ownership**: `patient_id` / `case_id` equals the target.
- **Code**: matches the protocol's controlled code for the quantity in question
  (e.g. serum potassium `K` vs. a distractor LOINC).
- **Status**: `final` only for protocol gates; route `preliminary`,
  `entered-in-error`, `canceled` (and other non-final) to the excluded set.
- **Window** (when a window applies): `from` inclusive, `to` **exclusive** —
  `[from, to)`.
- **Latest**: the qualifying `final` row with the greatest `effective_time`; break
  ties per the protocol ordering (`effective_time` asc, then `observation_id` asc).
Keep track of the *excluded* ids and why (wrong owner / code / status / date) — some
templates ask you to list them.

### 5. Apply the protocol to fill scored fields
Compute assessment / risk / disposition / plan / gate strictly from the filtered
evidence and the protocol rules. When a contraindication or urgent trigger fires,
the protocol's safe branch wins (escalate or hold rather than treat). Select each
enum from the template's `allowed_values`; leave lists empty (not null) when nothing
applies, unless the field is explicitly nullable.

### 6. Assemble evidence_ids
Cite the **actual identifiers you relied on** — `observation_id`s, `source_id`s from
findings, the `case_id`, the `protocol_id`, medication/imaging ids — following that
template's `ordering` rule (e.g. "case id first, then clinical sources", or
"descending relevance", or a specified sort). Do not include ids you did not use.

### 7. Set safety-check / provenance booleans honestly
Safety-check keys are compliance assertions. A key like `no_false_loc`,
`no_false_vomiting`, `no_normal_cxr_claim`, or `no_clear_lungs_claim` is **`true`
when you did NOT make that unsupported claim** — i.e. you complied. Make your output
actually comply (avoid contraindicated drugs, don't assert unshown findings), then
set the booleans to reflect the truth of what you emitted. For care-management-style
provenance splits, separate facts present in the chart from facts that would require
the member to disclose them.

### 8. Validate and emit
Run the checklist in `references/output-contract.md`, then print exactly one JSON
object. No leading/trailing prose, no code fences.

## References
- `references/data-model.md` — endpoints, response shapes, distractor patterns.
- `references/task-families.md` — the five recurring case types and how each
  protocol body maps to its template.
- `references/output-contract.md` — pre-submit validation checklist.
