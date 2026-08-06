# Clinic Runtime Protocol-Decision Skill

## What this skill does

Answers clinic decision-support tasks that run against a synthetic clinic runtime
over HTTP. Each task gives you: (1) a **prompt** naming a target `case_id` and the
clinical question, (2) an **`answer_template.json`** that is the exact output
contract, and (3) an **environment access file** (e.g. `environment_access.md`)
that is the *only* source of truth for how to reach the runtime.

Your job is to read the runtime, map the clinical facts onto the template's
controlled vocabulary, and emit **exactly one JSON object** that conforms to the
template — no markdown, no comments, no prose.

The task domains this skill covers (illustrative, not exhaustive): adult
respiratory / CAP assessment, pediatric head-injury triage, potassium
replacement and escalation, care-management routing, and observation-window
retrieval with a protocol gate. The workflow below is identical for all of them.

## Workflow

### 1. Read the contract first — before any network call

Open `input/payloads/answer_template.json` and extract, for every field:

- `required_top_level_keys` — the exact top-level keys that must appear (and no
  others, unless the template explicitly says extras are ignored).
- `type` and `allowed_values` — most scored fields are **controlled enums**.
  You may only emit values that appear in `allowed_values`. Never invent a value.
- `required_keys` / nested `fields` — for object-valued fields.
- Nullability (`string_or_null`, `integer_or_null`, `["string","null"]`,
  `nullable: true`, `required_when`) — use `null` *only* where permitted.
- `ordering` / `ordering_rule` — some lists are sets (normalized, order
  irrelevant), others must be sorted (by `effective_time`, by relevance, by
  clinical sequence, "case identifier first"). Obey exactly.
- `precision` / `unit` — round numbers as specified (one decimal place for
  mmol/L, HbA1c, phosphorus; two decimals for probability; integer hours/days).
- `expected_constant` / `required_value` — some fields (e.g. `task_id`,
  `case_id`) are fixed by the task; copy the literal from the template/prompt.

Treat the template as a strict schema validator. Your final object must pass it.

### 2. Read the environment access file

Open the run's environment access file (e.g. `environment_access.md`). From it —
and **only** from it — obtain:

- the **Base URL** (substituted for `<TASK_ENV_BASE_URL>` in the prompt),
- the **allowed `GET /api/*` endpoints**,
- any **auth header** required for `POST /api/query` (e.g. an `X-...-Token`).

Do not hardcode URLs, tokens, or endpoints from memory; do not use any other
source for network access. If the file is missing or lists no endpoint you need,
stop rather than guess.

### 3. Resolve the target case

`GET {BASE_URL}/api/cases/{case_id}` using the `case_id` from the prompt. The
response is a **bundle**: it typically embeds the `case`, `allergies`,
`observations`, `medications`, `imaging`, `problems`, `care_registry`, and
`sdoh` for that case in one object. Capture the `patient_id` (and `case_type`,
`service_date`, `status`) from here.

### 4. Gather the clinical evidence

Use the dedicated endpoints to confirm/complete the bundle (always filter to the
target `patient_id` / case):

- `GET /api/patients/{patient_id}`
- `GET /api/observations` (filter by patient + code + status + time)
- `GET /api/medications`
- `GET /api/allergies`
- `GET /api/problems`
- `GET /api/imaging`
- `GET /api/care-registry`
- `GET /api/sdoh`

For ad-hoc structured lookups, `POST /api/query` with the required auth header
and a body of the shape `{"sql": "..."}` (read-only SELECTs only). **Do not
mutate state, place orders, or POST anything that changes data.**

See `references/retrieval_patterns.md` for endpoint-specific filtering and
distractor-handling notes.

### 5. Load the applicable protocol

`GET /api/protocols` lists available protocols; `GET /api/protocols/{protocol_id}`
returns the full protocol. Pick the protocol whose domain matches the
`case_type` / clinical question (respiratory, head injury, potassium
repletion, care management, observation-window, etc.). The protocol defines the
risk tiers, red-flag catalogs, escalation thresholds, and gating rules you must
apply.

### 6. Map facts onto the template's controlled vocabulary

Every scored status / assessment / action field is a controlled enum from the
template. Walk the clinical data and select the matching enum value:

- **Assessment / risk / disposition** — derive from observations, vitals, and
  protocol thresholds.
- **Red flags / absent red flags** — list only flags actually supported by the
  data; use the absent-red-flags list for flags the protocol catalogs but the
  patient does not have.
- **Medication / order plan** — pick the strategy enum, then fill
  medication/dose/route/frequency/duration only when an action is recommended;
  use the `null` / `defer` / `not_recommended` options when it is not.
- **Allergy-awareness** — cross-reference `/api/allergies` so the chosen
  medication avoids active allergens; populate `avoid_allergens` accordingly.

When the data does not support an action, prefer the template's "no / defer /
not_recommended / null" option over asserting one.

### 7. Assemble `evidence_ids`

Populate `evidence_ids` (and any provenance / source-grouping fields) with
**real resource identifiers** read from the runtime — `case_id`,
`observation_id`, imaging ids, protocol ids, registry keys. Obey the template's
ordering rule: "case identifier first, then clinical source identifiers" means
exactly that; "descending relevance" means most-decisive evidence first.

### 8. Observation-window tasks

When the template has `matched_observation_ids` / `excluded_observation_ids` /
`latest_final`:

- Filter observations to the target `patient_id` and `target_code`.
- Apply the `window` (`from` inclusive, `to` exclusive) and require **final**
  status (exclude preliminary/cancelled).
- `matched_observation_ids` = final, in-window, target-code observations, sorted
  by `effective_time` ascending, then `observation_id` ascending.
- `excluded_observation_ids` = relevant distractors that fail on date, code, or
  status — sorted the same way (by `effective_time` when available).
- `latest_final` = the last matched observation (or `null` if `lab_found` is
  false); include `observation_id`, `value_mmol_l` (one decimal), and
  `effective_time` as an ISO-8601 UTC timestamp with trailing `Z`.

### 9. Derive `safety_checks`

These booleans are a **self-audit** that guards against unsupported claims
(e.g. "did not prescribe a contraindicated drug class", "did not claim a normal
imaging result that the imaging does not support", "did not assert a red flag
the patient lacks"). Set a check `true` only when your answer genuinely avoids
the unsupported claim given the data. If a check would be `false`, fix the
answer rather than leaving the false claim in place. Do not default them all to
`true` without verifying each against the evidence.

### 10. Numeric precision and timestamps

- Round per the template (`precision`): mmol/L, HbA1c, phosphorus → one decimal;
  probability → two decimals; counts / hours / days → integers.
- Timestamps are ISO-8601 UTC with a trailing `Z` (e.g.
  `2026-02-10T06:20:00Z`), unless the field explicitly permits `null`.
- Blood-pressure strings use `systolic/diastolic` form.

### 11. Validate and emit

Before emitting, re-check against the template: every required top-level key
present; no extra top-level keys (unless ignored); every enum value in
`allowed_values`; every type correct; every list ordered per its rule; nulls
only where permitted; numbers at the right precision. Then output **exactly one
JSON object** and nothing else.

## Guardrails

- Use the environment access file as the **sole** source for runtime access.
- **Read-only**: never mutate the runtime, place orders, or send state-changing
  requests.
- Never copy clinical conclusions from anywhere but the live runtime data for
  the target case — distractor cases exist in `/api/cases` to tempt you off
  target; always filter to the prompt's `case_id` / `patient_id`.
- Never invent enum values, identifiers, or timestamps not present in the
  runtime.
- If anything in `/work` is unexpected (files beyond the prompt, environment
  access file, train inputs, and train answers), stop and write
  `contamination_report.txt` instead of proceeding.

## Files in this skill

- `SKILL.md` — this entry point.
- `references/runtime_access.md` — how to read and use the environment access
  file safely.
- `references/output_contract.md` — how to obey `answer_template.json` field by
  field.
- `references/retrieval_patterns.md` — endpoint filtering, distractor handling,
  and evidence assembly.
