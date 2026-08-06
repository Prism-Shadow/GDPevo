---
name: clinic-protocol-decision-support
description: >-
  Produce a single schema-conforming JSON decision-support answer for a Harborview
  synthetic-clinic case task. Use whenever a task supplies a prompt.txt naming a target
  case id (CASE-*), an input/payloads/answer_template.json output contract, and an
  environment_access.md that points at a clinic runtime exposing GET /api/cases,
  /api/patients, /api/observations, /api/protocols, etc. Covers all five case families:
  adult respiratory / CAP (RESP-CAP), pediatric head injury (PEDS-HEAD), potassium
  repletion (K-REPLETION), observation-window retrieval (OBS-WINDOW), and high-risk
  care-management routing (CM-HIGH-RISK). The answer is derived live from the clinic
  API and the case's protocol; never invent clinical values.
---

# Clinic Protocol Decision Support

## What this task family is

Each task asks you to read one synthetic clinical case from a running clinic API,
apply that case's clinic protocol, and return **exactly one JSON object** that
conforms to a supplied `answer_template.json`. There is no free-text answer — the
grader checks structured fields (enums, numbers, booleans, id lists) against a
standard answer. The five case types and their answer shapes differ, but the
workflow below is identical for all of them.

Do **not** copy values out of any example answer. Every value must be derived from
the live case data and the live protocol for the specific case named in the prompt.

## Inputs you are given (per task)

1. `input/prompt.txt` — states the **target case id** (`CASE-…`) and, in prose, the
   decision outputs expected. Read it to learn the case id and what the task cares
   about, not for the schema.
2. `input/payloads/answer_template.json` — the **authoritative output contract**:
   `required_top_level_keys`, per-field `type`/`allowed_values` (enums), numeric
   `precision`, `ordering` rules, nullability, and any `required_value` /
   `expected_constant` (e.g. a fixed `task_id` or `case_id`). This file — not this
   skill — is the source of truth for the exact keys and enums of the run at hand.
3. `environment_access.md` — the runtime base URL (`GDPEVO_ENV_BASE_URL`), any
   credentials, and the **allowed endpoints**. Only call listed endpoints.

## Procedure

### 1. Scope the task
- From `prompt.txt`, extract the target `case_id`.
- From `answer_template.json`, list the required top-level keys and, for each,
  its type + allowed enum values + precision + ordering + null rules. Note any
  `required_value`/`expected_constant` fields (set them to that constant exactly).
- Determine `task_id`: use the template's `required_value`/`expected_constant` if
  given; otherwise use the task directory name (e.g. `train_00X` / the run's id).

### 2. Reach the environment
- Base URL comes from `environment_access.md` (`GDPEVO_ENV_BASE_URL`). **Do not
  hardcode a host** — read it from that file each run.
- Credentials are typically `none`. `POST /api/query` is token-gated and returns
  `{"error":"invalid or missing clinic token"}` without a clinic token, so treat it
  as unavailable and gather everything through the GET endpoints.
- See `references/environment_api.md` for the full endpoint + resource-shape
  reference and the case-type → protocol map.

### 3. Pull the case bundle and its protocol
- `GET /api/cases/{case_id}` returns one aggregated bundle: `case`, `patient`,
  `findings`, `observations`, `medications`, `allergies`, `problems`, `imaging`,
  `care_registry`, `sdoh`. This is your primary data source.
- Read `case.case_type`, map it to a `protocol_id`, and `GET
  /api/protocols/{protocol_id}`. **Apply the rules from the live protocol `body`**
  (thresholds, controlled codes, dose rules, follow-up hours, escalation triggers).
  Do not rely on memorized threshold numbers — read them from the response.
- `patient_id` for the answer = `case.patient_id` (== `patient.patient_id`).

### 4. Verify and filter the evidence (critical)
- **Patient ownership**: bundles can contain cross-patient distractor resources
  (e.g. an observation whose `patient_id` differs from the case's). Also
  `GET /api/observations?patient_id={patient_id}` to get the patient-scoped
  universe, and discard any resource whose `patient_id` ≠ the case patient.
- **Status**: only `status:"final"` observations satisfy protocol gates. Exclude
  `preliminary`, `entered-in-error`, `canceled`.
- **Exact codes**: match the protocol's `controlled_codes` exactly. E.g. serum
  potassium is code `"K"`; a whole-blood potassium (`6298-4`) is a *different* code
  and is a distractor. Chest x-ray impression is `CXR-2V`, viral panel is
  `SARS_FLU_RSV_PCR`, etc.
- **Time windows**: parse `effective_time` yourself and apply the window as
  `[from inclusive, to exclusive)`. The server's `from`/`to` query params are **not
  reliable** — do the windowing client-side.
- **Active only**: only `status:"active"` allergies/problems constrain the plan.
- When a task asks for `matched` vs `excluded` observation id lists, "excluded"
  means *relevant to this patient's review but disqualified by date/code/status* —
  it does **not** include resources that belong to another patient (those are
  dropped entirely).

### 5. Decide, using the live protocol
Apply the protocol body to the filtered evidence. The decision logic per case type
is summarized in `references/environment_api.md`, but always read the actual
protocol response for the exact constants. General rules that hold across types:
- Choose enum values only from the template's `allowed_values`; map a narrative
  finding to the closest allowed enum.
- Risk/escalation tiers come from comparing measured values to the protocol's
  threshold fields (e.g. `ed_escalation`, `urgent_branch`, `urgent_route_triggers`,
  `high_predictive_risk_min`).
- Medication/plan choices must respect **active allergies** — avoid implicated
  classes and record the avoided-allergen enums the template asks for.
- Numeric outputs (doses, follow-up hours, risk scores) come from protocol
  formulas/fields, at the template's stated precision.

### 6. Assemble the answer
- Emit **only** the `required_top_level_keys`, nothing extra (unless the template
  explicitly permits additional properties).
- Enums: exact allowed strings. List-type set fields have no required order unless
  the template gives an `ordering` rule — follow it when present.
- Numbers: honor `precision` (decimal places), integer-vs-null, units. Timestamps:
  ISO-8601 UTC with trailing `Z` exactly as specified.
- `evidence_ids`: cite the **real** resource ids you actually used
  (`observation_id`, `imaging_id`, the `case_id`, renal-function obs, etc.),
  ordered per the template's rule (often case id first, then clinical sources; some
  templates want descending relevance).
- `safety_checks` booleans: set `true` only after confirming you did **not** assert
  an unsupported finding — e.g. never claim a "normal CXR" or "clear lungs" when
  imaging shows consolidation; never assert loss of consciousness / vomiting /
  photophobia that the record does not support. These booleans attest to what you
  did not fabricate.

### 7. Output
Return one JSON object and nothing else — no markdown fences, no comments, no prose
outside the object. Write it to the run's answer file (e.g. `answer.json`).

## Guardrails
- Read the base URL and endpoint list from `environment_access.md`; only call
  allowed endpoints; do not mutate anything (all needed calls are GET).
- Never place orders or POST changes; `POST /api/query` is out of reach without a
  token and is not needed.
- Ignore distractor records: case ids like `CASE-D30xx` and patient ids like
  `PAT-D20xx` are synthetic distractors — never the target unless the prompt names
  them.
- Do not fabricate clinical values, ids, or timestamps. If a required datum is
  genuinely absent, follow the template's null/empty-list rules rather than
  inventing one.
- Re-read `answer_template.json` for the run in front of you; enums and required
  keys can differ between tasks even within the same family.

## Pre-submit checklist
- [ ] Output has exactly the `required_top_level_keys`, no extras.
- [ ] Every enum value is in the template's `allowed_values`.
- [ ] `task_id` / `case_id` match any `required_value`/`expected_constant`.
- [ ] `patient_id` is the case's patient; no cross-patient data leaked in.
- [ ] Only `final` observations and `active` allergies/problems drove the decision.
- [ ] Controlled codes matched exactly; whole-blood/preliminary/other-code
      distractors excluded (and listed under `excluded_*` if the template asks).
- [ ] Time-window membership computed client-side, `[from, to)`.
- [ ] Numbers at required precision; timestamps ISO-8601 `Z`.
- [ ] `evidence_ids` are real ids, ordered per template rule.
- [ ] `safety_checks` reflect no unsupported/fabricated claims.
- [ ] Single JSON object, no prose or markdown.

## Helper
`scripts/gather_case.py` is an optional convenience that pulls the case bundle, the
matching protocol, and the patient-scoped observation list for a given base URL and
case id, so you can inspect all evidence at once. It performs no clinical decision
logic — you still apply the protocol and fill the template yourself.
