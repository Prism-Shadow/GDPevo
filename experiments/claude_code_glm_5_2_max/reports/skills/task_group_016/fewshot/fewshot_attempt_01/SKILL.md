# Clinic Runtime Decision-Support Skill

This skill produces a single, schema-conformant JSON decision-support object for a
synthetic clinic case served by the Harborview Synthetic Clinic runtime. It applies
across case types (respiratory, head injury, potassium replacement, care-management
routing, observation-window lab retrieval, and others that share the same shape).

Use this skill whenever a task:
- names a target `case_id` (e.g. `CASE-…`),
- points at a runtime environment described in `environment_access.md`,
- requires a JSON object conforming to an `answer_template.json`, and
- asks for a protocol-bound clinical recommendation (risk tier, disposition,
  red flags, medication/lab/follow-up plan, evidence IDs, safety checks).

## What you must NOT do

- **Never copy specific answer values from training examples.** Patient IDs,
  medication names, doses, enum selections, evidence IDs, numeric anchors, and
  timestamps are all case-specific. Derive every value fresh from the live
  runtime for the case in front of you. The skill teaches the *method*, not the
  answers.
- Do not invent endpoints, headers, or tokens beyond `environment_access.md`.
- Do not mutate the runtime or place orders. This is read-only decision support.
- Do not output prose, markdown, or comments — only the final JSON object.

## Workflow

### 1. Parse the prompt
Extract, from the prompt and the task directory name:
- `task_id` — the run/task identifier (it appears in `answer_template.json` as an
  `expected_constant` / `required_value`; use it verbatim).
- `case_id` — the target case.
- The clinical question and which facets the response must cover
  (assessment, risk, disposition, tests, medication plan, follow-up, red flags,
  contraindications, evidence, safety checks, etc.).

### 2. Read the answer template as a contract
Open `input/payloads/answer_template.json` and treat it as the strict output
specification. Before doing any clinical reasoning, extract:
- **Required top-level keys** — emit exactly these, no extras.
- **Enum fields** — copy `allowed_values` strings verbatim; never paraphrase.
- **`expected_constant` / `required_value`** — fixed values (typically `task_id`,
  `case_id`); match them exactly.
- **Numeric precision** — note per-field precision (e.g. "one decimal place",
  "two decimal places", "whole hours"). Round final values accordingly.
- **Null rules** — which fields permit `null` (`string_or_null`,
  `integer_or_null`, `enum_or_null`). Use `null` *only* where permitted.
- **List ordering rules** — three flavors appear:
  1. *"normalized as a set"* (order irrelevant, evaluators dedupe) — emit each
     selected value once; order is free.
  2. *"sort by effective_time then observation_id ascending"* — sort explicitly.
  3. *"case identifier first, then clinical source identifiers"* or
     *"descending relevance"* — apply that ordering.
- **Safety-check booleans** — these assert the *absence* of unsupported claims
  (e.g. `no_normal_cxr_claim`, `no_false_loc`, `no_penicillin_or_sulfa`). Set
  them `true` only when your reasoning genuinely avoids the unsupported claim.

### 3. Reach the runtime via `environment_access.md`
Open `environment_access.md` for the run. It gives:
- the **base URL**,
- the **allowed endpoints** for this run,
- any **header/token** required (e.g. `POST /api/query` requires
  `X-Clinic-Token`).

See `skill/environment_contract.md` for the general endpoint shapes and query
mechanics. Do not hard-code URLs/headers/tokens in the skill output — read them
from `environment_access.md` each run, because they vary.

### 4. Retrieve the case and its clinical bundle
- `GET /api/cases/{case_id}` — returns the case plus bundled clinical context:
  patient, allergies, observations, medications, imaging, problems, care-registry,
  SDOH. Confirm the `patient_id` here.
- Cross-check with `GET /api/patients/{patient_id}` when patient-level facts
  (allergies, demographics) matter.
- Pull flat lists as needed: `GET /api/observations`, `/api/medications`,
  `/api/allergies`, `/api/imaging`, `/api/problems`, `/api/care-registry`,
  `/api/sdoh`.

For precise filtering (date windows, code, status) prefer
`POST /api/query` with a SQL `sql` string and the required token — it returns
`{columns, rows, count, truncated}` and is the reliable way to select, say,
"final potassium observations for this patient in this window." See
`skill/environment_contract.md`.

### 5. Retrieve the applicable protocol
- `GET /api/protocols` lists protocols (`protocol_id`, title, version).
- `GET /api/protocols/{protocol_id}` returns the authoritative rules. Use the
  case type to pick the right protocol. Protocols carry:
  - **`controlled_codes`** — mappings from LOINC/clinical codes to the enum
    tokens the template expects (e.g. `oxygen_satulation` → `59408-5`,
    `chest_xray` → `CXR-2V`). Use these to translate chart codes ↔ enum tokens.
  - **thresholds / escalation criteria** — numeric cutoffs that drive risk tier,
    disposition, urgent actions, stabilization.
  - **`authoritative_statuses`** — which observation statuses count (typically
    `final`). Exclude `preliminary`/cancelled unless the protocol says otherwise.
  - **allergy / contraindication rules** — which allergen classes to avoid.

### 6. Apply the protocol to the chart (reasoning, grounded)
Map chart facts through protocol rules to fill every template field:
- **Assessment / risk / disposition** — from signs, vitals, and protocol
  thresholds.
- **Red flags** — list the ones the protocol defines *and* that are present.
  Where the template also wants `absent_red_flags`, enumerate the protocol red
  flags not supported by the chart (do not assert absent ones the chart never
  screened for unless the protocol defines them).
- **Recommended tests / imaging** — from `controlled_codes`, restricted to what
  the protocol and clinical picture justify.
- **Medication plan** — allergy-aware. Map active allergens to the
  `avoid_allergens` enum classes; never recommend a contraindicated class. Pick
  dose/route/frequency/duration from protocol defaults; null the medication
  fields when no medication is indicated (e.g. supportive care, or deferral to
  ED).
- **Stabilization / urgent actions** — empty list when none are indicated; sort
  by clinical action sequence when multiple.
- **Follow-up** — timeframe in the unit/precision the template demands (often
  integer hours); route from the protocol's allowed follow-up routes.
- **Return precautions** — protocol-defined warning signs to tell the patient.
- **Contraindications** — screen dialysis, arrhythmia symptoms, eGFR, etc. as
  the protocol requires.
- **Evidence IDs** — stable identifiers you actually used: `case_id`,
  `observation_id`, imaging ID, protocol ID, registry ID. Respect the ordering
  rule (case-id-first, or descending relevance, etc.). Never invent IDs.
- **Safety checks** — set each boolean true only if your reasoning avoids the
  specific unsupported claim it guards against.

### 7. Emit the JSON object
Produce exactly one JSON object:
- only the required top-level keys,
- controlled enum values copied verbatim,
- numbers at the specified precision,
- `null` only where permitted,
- lists deduped and ordered per the template's rule,
- no markdown, no comments, no trailing prose.

Re-read `answer_template.json` once more against your draft to confirm every
field type, enum, precision, null, and ordering rule is satisfied before
returning.

## Supporting references
- `skill/environment_contract.md` — endpoint shapes, query mechanics, common
  field names, and gotchas for navigating the runtime.
- `skill/answer_template_patterns.md` — recurring template constructs (enums,
  null-permitted fields, list-ordering flavors, safety-check booleans,
  expected-constant fields) and how to satisfy each.
