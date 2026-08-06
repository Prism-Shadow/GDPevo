---
name: synthetic-clinic-protocol-answer
description: >-
  Produce the required JSON answer for a synthetic-clinic protocol-bound
  clinical decision-support task. Use when the input gives a target case id
  plus an answer_template.json and points at a read-only clinic runtime API
  (patients, cases, observations, medications, allergies, problems, imaging,
  care-registry, sdoh, protocols). Covers acute respiratory / CAP, pediatric
  head injury, potassium replacement, care-management routing, and
  observation-window retrieval cases. The skill teaches the procedure to fetch
  the record, select and apply the matching protocol at runtime, and emit one
  schema-conformant JSON object. It never contains task-specific answer values.
---

# Synthetic-clinic protocol answer

## What this task family is

You are given, per task:

- `input/prompt.txt` — names one **target case id** (e.g. `CASE-...`) and, in
  prose, which clinical questions the answer must resolve.
- `input/payloads/answer_template.json` — the **exact output contract**:
  the required top-level keys, each field's type, the closed **enum
  `allowed_values`**, numeric precision, ordering rules, where `null` is
  permitted, and any fixed constants (often `task_id`, `case_id`).
- A separate environment-access file (e.g. `environment_access.md`) — the
  clinic runtime **base URL**, credentials (usually none), and the **allowed
  endpoints** for this run.

Your job is to return **exactly one JSON object** that conforms to the
template, with every value derived from the clinic record by applying the
governing protocol. No prose, no markdown, no extra top-level keys.

The correct answer is always *derivable* from the target patient's
authoritative records plus the protocol. Do not guess, and do not invent
findings the chart does not support.

## Procedure

### 1. Read the contract first
Parse `answer_template.json` completely before touching the network. Note, for
every field: the exact key name, type, the closed set of `allowed_values`
(you may only emit values from these sets), precision (integer vs. N-decimal),
ordering rules ("normalized as a set" vs. "sorted by ..."), nullability, and
any `required_value` / `expected_constant`. This is the ground truth for
shape; the environment supplies the content.

Set the fixed constants directly: `task_id` = the task folder id (e.g.
`train_001` / the current task id), `case_id` = the id from `prompt.txt`.

### 2. Load environment access
Read the environment-access file for the base URL and the **allowed endpoint
list**. Only call endpoints on that list. Do not mutate anything — every task
is read-only (no orders, no POSTs that change state). If a `POST /api/query`
endpoint is listed but rejects calls for a missing "clinic token" and no token
is provided, treat it as unavailable and use the `GET` resource endpoints,
which are sufficient.

### 3. Pull the case bundle
`GET /api/cases/{case_id}` returns a bundle for the target case:

- `case` — `patient_id`, `case_type`, `service_date`, `status`, `summary`.
- `findings` — list of `{finding_key, finding_value, source_id}`; the
  structured clinical narrative (vitals ranges, symptoms present/absent,
  `current_time`, allergy constraints, outreach posture, etc.).
- `observations` — FHIR-like: `observation_id`, `code`, `display`, `status`,
  `effective_time`, `value_number`/`value_text`, `unit`, `interpretation`,
  `patient_id`.
- `imaging`, `medications`, `allergies`, `problems`, `sdoh`, `care_registry`
  (any may be `null`/empty).

Fetch `GET /api/patients/{patient_id}` (and, if useful, the topical list
endpoints such as `GET /api/observations`) for demographics and fuller context.

### 4. Select and read the governing protocol
`GET /api/protocols` lists the protocols; pick the one whose title/scope matches
the case's `case_type`, then `GET /api/protocols/{protocol_id}` and read its
`body`. The protocol `body` — not your prior knowledge — is authoritative for
thresholds, `controlled_codes`, `authoritative_statuses`, follow-up timing,
ordering, dose rules, escalation triggers, and referral criteria.
See `reference/api_and_protocols.md` for the case_type → protocol map and how
each protocol's fields feed each answer section.

**Read protocol constants at runtime; never hardcode them.** Applying the
protocol you fetched is what makes the answer correct and keeps the skill
robust if the environment changes.

### 5. Derive each field, mapping to the template's controlled vocabulary
Work through the template's keys. For each, apply the protocol rule to the
case data, then translate the raw clinical fact into the template's enum. The
protocol's internal code names and the template's `allowed_values` are
*different vocabularies* — map deliberately; emit only values the template
allows. Example shape (not an answer): a saturation range in `findings`
crosses a protocol threshold → choose the corresponding template red-flag /
risk enum, not the protocol's own string.

### 6. Provenance and distractor discipline
This is where most errors happen. The environment is seeded with decoys.

- **Target patient only.** Use records whose `patient_id` matches the case's
  patient. Silently drop any wrong-patient record — it is not evidence and is
  not even a listed distractor.
- **Authoritative status only.** Treat only statuses in the protocol's
  `authoritative_statuses` (typically `final`) as satisfying gates. Exclude
  `preliminary` / `entered-in-error` / `canceled` for authoritative claims.
- **Right code, right window.** Match the target observation `code`; honor
  date windows as the protocol/template state them (commonly `from` inclusive,
  `to` exclusive).
- **Latest-wins.** When several qualifying same-code results exist, select per
  the protocol (usually the latest `final` `effective_time` in the window).
- Where the template asks for excluded/distractor ids, list the same-patient
  records that were relevant to review but disqualified by date, code, or
  status — sorted as the template directs.

### 7. Evidence ids
`evidence_ids` (or `source_provenance`) must be the **real resource ids you
actually relied on** — e.g. `observation_id`s, `imaging_id`, renal/eGFR
observation ids, the `case_id`, protocol id — in the order the template
requests (often case id first, then clinical sources; or descending relevance).
Never fabricate ids.

### 8. Safety-check booleans
Safety-check fields assert you did **not** put an unsupported claim in the
answer. Set each to reflect the chart, e.g.: do not claim a normal chest X-ray
when imaging shows consolidation; do not recommend a drug class the patient has
an active allergy to; do not assert loss-of-consciousness / vomiting /
photophobia the record marks absent. The boolean is `true` when your answer
honors that constraint.

### 9. Format exactly
- Emit **only** the required top-level keys — no extras, no prose.
- Enums: only `allowed_values`. Lists that are "normalized as a set": no
  duplicates, order-insensitive. Lists with an ordering rule: sort exactly.
- Numbers: honor precision (integer hours/days; N-decimal values). Timestamps:
  ISO-8601 UTC with trailing `Z`.
- `null` only where the field spec permits it; otherwise supply a value.
- Output one JSON object and nothing else.

## Final checklist
- [ ] Every required top-level key present; no extra keys.
- [ ] Every enum value is in the template's `allowed_values`.
- [ ] Constants (`task_id`, `case_id`, `patient_id`) correct.
- [ ] Findings, observations, imaging cross-checked against protocol
      thresholds — decision derived, not guessed.
- [ ] Only target-patient, authoritative-status, in-window, right-code records
      used; distractors excluded correctly.
- [ ] `evidence_ids` are real ids you used, ordered per the template.
- [ ] Safety checks honor the chart (no fabricated/normal/contraindicated claims).
- [ ] Numeric precision, timestamp format, nullability, ordering all match.
- [ ] Output is a single JSON object with no surrounding text.
