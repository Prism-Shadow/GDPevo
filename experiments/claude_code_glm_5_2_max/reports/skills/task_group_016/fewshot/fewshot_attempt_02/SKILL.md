---
name: clinic-protocol-cds
description: Produce a schema-conformant JSON clinical decision-support answer for a synthetic clinic case. Use whenever a task gives a case id, an answer_template.json contract, and access to the clinic runtime environment over HTTP. Drives the runtime API, applies the matching protocol, and emits exactly one JSON object that conforms to the template.
---

# Clinic Protocol Decision-Support Skill

This skill turns a clinical case-task prompt into one JSON object that conforms
**exactly** to the `answer_template.json` contract supplied with the task. It does
not invent clinical facts: every populated value is grounded in data read from
the clinic runtime, and every field shape matches the template.

## When to use

A task matches this skill when it has all of:

- A **case id** named in the prompt (e.g. `CASE-…-…`).
- A **runtime environment** reachable over HTTP, described by an
  `environment_access.md` file (base URL + allowed endpoints + any auth header).
- An **`answer_template.json`** that defines the required top-level keys, field
  types, enums, null rules, numeric precision, and list ordering rules.
- An instruction to **return only a single JSON object** (no markdown, no prose).

If any of these are missing, stop and report what is missing before proceeding.

## Inputs you must read first

1. The task `prompt.txt` — gives the case id and lists which clinical dimensions
   the answer must cover.
2. `input/payloads/answer_template.json` — **the contract**. This is the source
   of truth for every field. Read it end to end before fetching anything.
3. `environment_access.md` — base URL, allowed endpoints, and the auth header
   required for protected endpoints. Treat the base URL as a placeholder
   (`<TASK_ENV_BASE_URL>`); substitute the real base URL from this file.

Do **not** read or rely on any `train_answers/` material. Those are grading
references for a different purpose and are out of scope for producing a new
answer. Do **not** copy case-specific values (patient ids, medication names,
doses, lab values, observation ids) from anywhere other than the live runtime.

## Procedure

### 1. Parse the contract

From `answer_template.json`, extract and keep a working checklist of:

- **Required top-level keys** (in order). The output must contain exactly these
  keys unless the template explicitly says extra keys are ignored.
- **Constant fields** — some templates pin `task_id` and `case_id` to fixed
  values (e.g. `expected_constant` / `required_value`). Use the constant
  verbatim; do not recompute it.
- **Enums** — list the allowed values for every enum field. Output values must
  match an allowed value **character-for-character**. Watch for underscores vs
  spaces, and singular vs plural.
- **Null rules** — for each field note whether `null` is permitted (`string_or_null`,
  `integer_or_null`, `[type, null]`, `nullable: true`). Use `null` only where
  explicitly allowed; otherwise populate with a real value.
- **Numeric precision** — e.g. "one decimal place", "two decimal places", "whole
  hours". Round/format the final number to that precision.
- **List ordering** — three kinds appear:
  - "No semantic ordering" → order does not matter (evaluator normalizes as a
    set). Still emit each value at most once unless duplicates are allowed.
  - Explicit ordering rule (e.g. "case identifier first", "sort by
    effective_time ascending then observation_id ascending") → apply it exactly.
  - "use an empty list when none" → emit `[]`, never omit the key.
- **Conditional presence** — e.g. `required_when: "lab_found is true"` → include
  the sub-object only when the condition holds; otherwise use `null` if the field
  is nullable, or omit per the template.

See `references/conformance_checklist.md` for the full validation pass.

### 2. Resolve the case

Using the base URL and allowed endpoints from `environment_access.md`:

1. `GET /api/cases/{case_id}` (or locate it via `GET /api/cases` then filter) to
   fetch the **case bundle**. The bundle is the primary evidence source and
   typically nests: `case`, `findings`, `allergies`, `medications`, `problems`,
   `observations`, `imaging`, `care_registry`, `sdoh`.
2. Read `case.patient_id` from the bundle — this is the `patient_id` to put in
   the answer (never guess one).
3. Note the `case_type`; it maps to the protocol you need next.

> The runtime also contains many **distractor** records (synthetic, marked as a
> "generated distractor feed" or with ids like `CASE-D…`, `PAT-D…`, `OBS-D…`).
> Scope every query to the target case id / patient id so distractors do not leak
> into your evidence.

### 3. Fetch supporting resources

Pull only the resources that the template's fields require, scoped to the target
case/patient. Available GET endpoints (confirm against `environment_access.md`,
since the allowed list is run-specific):

- `/api/patients/{patient_id}` — demographics, identifiers.
- `/api/observations` — lab and vital Observation resources (filter by
  `patient_id`/`case_id`, `code`, `status`, `effective_time`).
- `/api/medications`, `/api/allergies`, `/api/problems` — current meds, allergy
  list (note `status: active` vs `inactive`), problem list.
- `/api/imaging` — imaging studies and reads.
- `/api/care-registry`, `/api/sdoh` — care-management registry and social
  determinants.
- `/api/protocols` and `/api/protocols/{protocol_id}` — the decision rules.

Resource shapes are documented in `references/runtime_api.md`.

### 4. Use the query endpoint for filtered retrieval

`POST /api/query` runs a SQL-style read query and is the right tool when you need
to filter across many resources (e.g. "all final potassium observations for this
patient in this time window"). It requires the header from
`environment_access.md` (e.g. `X-Clinic-Token: …`) and a JSON body of the form:

```json
{ "sql": "select ... from <table> where <col> = ?", "params": ["..."] }
```

Response: `{ "columns": [...], "rows": [...], "count": N, "truncated": bool }`.
Never write/mutate (`update`/`insert`/`delete`) — these tasks are read-only. If
`truncated` is true, narrow the filter rather than paging blindly.

### 5. Load the matching protocol

`GET /api/protocols` lists protocols by id/title; pick the one whose scope covers
the `case_type`, then `GET /api/protocols/{protocol_id}` for the full body. The
protocol body is **structured**, not prose — it holds the decision thresholds,
escalation rules, controlled code mappings, follow-up timing, and red-flag
definitions that drive the answer. Apply its rules literally:

- Compare numeric findings to the protocol's thresholds (e.g. oxygen saturation
  `<` a value, respiratory rate `>=` a value) to derive risk tier, disposition,
  and escalation.
- Use the protocol's `controlled_codes` / code mappings to translate clinical
  concepts into the exact enum/code strings the template expects.
- Copy follow-up timing, return-precaution codes, and gate definitions from the
  protocol rather than from general knowledge.

### 6. Populate each field

For every required top-level key, fill the value from runtime evidence +
protocol rules. Keep these disciplines:

- **Evidence ids**: list real resource ids you actually read (case id, observation
  ids, imaging ids, protocol id, visit/encounter source ids). Apply the
  template's ordering rule. Never fabricate ids.
- **Safety-check booleans**: these assert you did **not** make an unsupported
  claim (e.g. `no_penicillin_or_sulfa` is `true` only when the medication plan
  avoids those classes; `no_normal_cxr_claim` is `true` only when you did not
  assert a normal chest x-ray). Set each from the actual content of your answer,
  not by default.
- **Allergy-aware medication plans**: cross-check the chosen medication class
  against the patient's **active** allergies (inactive allergies do not bind) and
  populate `avoid_allergens` accordingly.
- **Window/lab-gate tasks**: when the task is about an observation time window,
  enumerate the candidate observations for the patient, partition them into
  **matched** (correct code + final status + inside window) vs **excluded**
  (wrong code, wrong status, or outside window), sort each list per the template
  rule, and derive the protocol gate from the latest matched final value.

### 7. Conformance-check before returning

Run the validation pass in `references/conformance_checklist.md` against your
draft. Fix any violation. Then return **exactly one JSON object** — no markdown
fences, no commentary, no trailing text. If the task says "Return only a JSON
object", the entire response body is that object.

## What never to do

- Do not copy case-specific values (patient ids, medication names/doses, lab
  numbers, observation ids) from training/answer material or from memory — only
  from the live runtime for the current case.
- Do not add top-level keys the template did not list (unless it explicitly says
  extra keys are ignored).
- Do not use an enum value that is not in the template's `allowed_values`.
- Do not use `null` where the template forbids it, or omit a required key.
- Do not mutate the runtime or place orders.
- Do not include narrative prose, markdown, or explanations in the final output.

## Files in this skill

- `SKILL.md` — this entry procedure.
- `references/runtime_api.md` — the clinic runtime API contract: endpoints,
  auth, query DSL, and resource shapes.
- `references/conformance_checklist.md` — the output validation pass to run
  against `answer_template.json` before returning.
