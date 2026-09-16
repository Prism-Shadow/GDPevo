---
name: clinic-decision-support
description: >
  Use when the user needs to produce a structured, protocol-driven clinical
  decision-support result from a synthetic clinic FHIR-like REST API. This
  includes respiratory assessments, pediatric head-injury triage, potassium
  replacement orders, care-management routing, observation-window retrieval,
  and any similar workflow where a case ID and a strict JSON answer template
  are provided. Trigger on phrases such as "clinical decision support",
  "protocol assessment", "clinic case", "synthetic clinic", "answer template",
  "structured JSON response", "FHIR", or mentions of clinic case IDs and
  runtime environments.
---

# Clinic Decision Support

A solver for producing structured clinical decision-support results from a
synthetic clinic FHIR-like REST API. The API models a small outpatient clinic
with patients, cases, observations, imaging, medications, allergies, problems,
social determinants, care-registry entries, and protocols.

## Task structure

Every task provides:

- A **prompt** naming a target case ID (e.g. `CASE-RESP-140`) and a task type.
  The prompt references `<TASK_ENV_BASE_URL>`, which is the root URL of the
  clinic API runtime.
- An **answer template** (`answer_template.json`) that defines the exact JSON
  shape to return: required top-level keys, allowed enum values, numeric
  precision, nullability, and ordering rules. The answer MUST match this
  template exactly.

Read both files before making any API calls. The template tells you exactly
what the evaluator expects; every field constraint in it is a scoring rule.

## Core workflow

### 1. Read the prompt and the answer template

Load `input/payloads/answer_template.json` (or wherever the prompt points you).
Note every required key, every enum constraint, every precision rule.

The prompt always names a **case ID**. Copy it into the output under `case_id`
exactly as given.

### 2. Orient through the API

Start with a single call to the case detail endpoint to discover what data is
attached and to find the patient ID:

```
GET {base}/api/cases/{case_id}
```

This often returns the richest payload: a nested object with `case`, `findings`
(flat key-value clinical facts), inline `observations`, `imaging`, `patient`
summary, `allergies`, `medications`, `problems`, and `sdoh`. Read it thoroughly
before drilling into other endpoints.

### 3. Pull supporting data

After reading the case detail, pull additional data from these endpoints as
needed by the template:

| Endpoint | When to use |
|---|---|
| `GET /api/patients/{patient_id}` | When you need the full patient record with medications, problems, allergies, and sdoh merged into one response. Often redundant with the case detail, but sometimes carries extra fields. |
| `GET /api/observations?patient_id=X` or `?case_id=X` | When the template requires observations not included inline in the case detail, or when you need to filter by code/date/status. |
| `GET /api/imaging?patient_id=X` | When imaging records are needed and not inline in the case detail. |
| `GET /api/medications?patient_id=X` | For a complete active medication list. |
| `GET /api/allergies?patient_id=X` | For the active allergy list. |
| `GET /api/problems?patient_id=X` | For active problem-list conditions. |
| `GET /api/sdoh?patient_id=X` | For social-determinant domains (transportation, financial, food, housing). |
| `GET /api/care-registry?patient_id=X` | For risk scores, dialysis schedules, chronic-condition counts, recent admissions. |
| `GET /api/protocols` | To list available protocols. |
| `GET /api/protocols/{protocol_id}` | To read the decision rules, thresholds, controlled codes, and constraints for a protocol. |

Do not wait for permission between calls; pull everything you need in parallel
where possible.

### 4. Read the relevant protocol

The case detail's `case_type` field or the prompt itself usually signals which
protocol applies. Fetch it and read its `body` carefully. Protocols carry:

- **Authoritative statuses** (e.g., only `"final"` observations count).
- **Controlled codes** mapping template entries (like `CXR-2V`, `K`, `CBC_BASIC`)
  to LOINC or local codes used in observations.
- **Thresholds** and decision rules (oxygen saturation, potassium levels, risk
  scores, symptom lists).
- **Follow-up timing**, return precautions, restriction lists.
- **Exclusion rules** (e.g., excluded observation statuses, urgent-branch
  triggers).

Apply these rules directly to the data you gathered. Do not guess thresholds;
read them from the protocol.

### 5. Collect evidence IDs

The template always expects an `evidence_ids` array. Collect stable identifiers
from the API responses:

- The case ID itself (always include first).
- Observation IDs for key lab/vital/imaging results used in the decision.
- Imaging IDs when imaging was reviewed.
- In care-management tasks, include care-registry and observation IDs.

Use the exact `observation_id`, `imaging_id`, or `case_id` values from the API
responses. Do not invent identifiers.

### 6. Fill the template precisely

Work key by key through the template. For every field:

- **Enums**: Use only values listed in `allowed_values`. Copy them exactly,
  including underscores and casing. If the protocol implies a value not in the
  allowed list, re-read the template — the allowed values are the complete
  universe the evaluator accepts.
- **Numbers**: Match the precision in the template (e.g., `"one decimal place"`
  means `3.2`, not `3.20` or `3`). Follow `round_to_nearest` rules from
  protocols when computing doses.
- **Nulls**: Only use `null` when the template explicitly permits it (a field
  with `"type": ["integer", "null"]` or `"type": "string_or_null"`). When a
  medication or dose is not applicable, use `null` only if the template allows
  it; otherwise use a placeholder like `"not_recommended"` when that is an
  allowed enum.
- **Lists**: Respect set semantics when noted (order does not matter), but sort
  chronologically when the template says to (e.g., matched observation IDs
  ascending by effective_time).
- **Booleans**: Use JSON `true`/`false`, never strings.
- **Timestamps**: Use ISO-8601 with trailing `Z` and seconds precision
  (`2026-01-14T10:00:00Z`). A `from`/`to` window is inclusive start, exclusive
  end unless the template says otherwise.

### 7. Return only the JSON object

Do not wrap the output in markdown fences, do not add commentary, do not
include extra top-level keys. The evaluator parses the raw response. If the
template says `"output_rule": "Return exactly one JSON object..."`, follow it.

## Task-type specifics

### Observation-window retrieval

When the template has `window`, `lab_found`, `matched_observation_ids`, and
`excluded_observation_ids`:

1. Read the template for the window bounds (`from`/`to`) and the target code
   (always `"K"` for serum potassium in this system).
2. Pull observations for the patient. Filter by:
   - `code` matching the target code.
   - `status` equal to `"final"`. Exclude `preliminary`, `canceled`,
     `entered-in-error`.
   - `effective_time` inside the window (inclusive start, exclusive end).
   - `patient_id` matching the target patient.
3. Sort matched observations by `effective_time` ascending, then by
   `observation_id` ascending.
4. Identify the **latest final** (the last one in the sorted list) for the
   `latest_final` field.
5. Collect excluded observations: any that share the target code or patient
   but fail because of date, status, or a different code. Sort excluded IDs
   by `effective_time` then `observation_id`.
6. Determine the `protocol_gate` from the latest final's value against protocol
   thresholds. The protocol `OBS-WINDOW-2026` defines observation-window rules;
   the potassium protocol `K-REPLETION-2026` defines potassium thresholds.

### Potassium replacement

When the template includes `latest_potassium`, `replacement_required`, and
`medication_order`:

1. Find the latest final serum potassium observation (code `"K"`) for the
   patient, regardless of window. Use this for `latest_potassium`.
2. Check the **urgent branch first**: potassium below 3.0 mmol/L, dialysis-
   dependent ESRD, ECG abnormality, or arrhythmia symptoms trigger urgent
   escalation. Do not compute a routine oral dose if any urgent trigger fires.
3. If the urgent branch does not apply and potassium is below the target (3.5
   mmol/L), compute the oral dose: 10 mEq per 0.1 mmol/L below target, rounded
   to the nearest 10 mEq. Example: K = 3.1 → deficit = 0.4 mmol/L → 40 mEq.
4. Check contraindications: eGFR, dialysis status, arrhythmia symptoms. If a
   contraindication applies, set `potassium_plan` to `hold_due_to_contraindication`
   or `urgent_escalation` as appropriate.
5. Set the follow-up lab to the next morning (protocol says "next morning final
   serum potassium"). Use LOINC `2823-3` and schedule the timestamp for the
   morning of the day after `current_time`.

### Care-management routing

When the template includes `risk_tier`, `program`, `priority_problems`,
`numeric_anchors`, and `source_provenance`:

1. Pull the care-registry for the patient: `risk_score`, `chronic_condition_count`,
   `dialysis_schedule`, `recent_admission_date`, `medication_count`.
2. Pull problems, medications, and sdoh.
3. Apply protocol `CM-HIGH-RISK-2026` thresholds:
   - `risk_tier`: `"high"` when risk_score ≥ 0.75 with supporting triggers;
     `"moderate"` otherwise if risk_score ≥ 0.5; `"low"` below that.
   - `program`: `"complex_care_management"` when risk_score ≥ 0.75 AND
     supporting triggers are met (chronic conditions ≥ 3, recent admission,
     dialysis/advanced CKD, heart failure, uncontrolled diabetes).
4. Map problems to `priority_problems` enum values. Map sdoh domains to
   `referrals` (transportation → `transportation_benefits`, financial/food →
   `social_worker`, ≥ 2 moderate-or-severe sdoh domains → `social_worker`).
5. Build `source_provenance.chart_facts` from what came from structured API
   data (risk score, labs, vitals). Build `member_disclosure_needed` from
   facts the patient reported (barriers, fatigue, preferences) that are not
   in the structured chart data.
6. Set `care_plan_minima` based on protocol: 3 problems minimum, weekly follow-
   up required, member-stated priority required, at least 2 disciplines.
7. `outreach_stance`: use `"permission_based_plain_language"` when sdoh data
   shows the member is reluctant or when barriers suggest sensitivity.

## Common pitfalls

- **Not reading the case detail first.** `/api/cases/{case_id}` returns findings
  (flat key-value clinical facts) that are often the fastest path to clinical
  context. Skipping it means extra API calls for the same data.
- **Using preliminary or canceled observations.** Protocols only accept
  `status: "final"`. Always filter out `preliminary`, `canceled`, and
  `entered-in-error` observations.
- **Active vs. inactive allergies.** Only active allergies constrain medication
  choices. Check the `status` field.
- **Computing potassium dose without checking the urgent branch.** Always
  evaluate the urgent branch before computing a routine oral dose.
- **Wrong timestamp format.** Use ISO-8601 with trailing `Z` and seconds.
  `2026-04-07T14:30:00Z`, not `2026-04-07T14:30Z` or `2026-04-07 14:30:00`.
- **Extra keys or commentary in output.** The evaluator parses the JSON object
  directly. Any extra text, markdown fences, or additional keys cause failures.
- **Misreading the answer template's allowed values.** An enum field only
  accepts the exact strings listed. If the protocol says "moderate risk" but
  the template allows `"moderate"`, use the template's value.
- **Not using the protocol's controlled codes.** The protocol maps template
  entries to actual observation codes. `CBC_BASIC` may not appear directly in
  observations; the protocol tells you how to locate it.

## API reference

All endpoints are read-only unless noted. Query parameters use standard
`?key=value` syntax.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/cases` | List all cases (paginated, with `count` and `items`) |
| GET | `/api/cases/{case_id}` | Single case with nested findings, observations, imaging, allergies, etc. |
| GET | `/api/patients` | List all patients |
| GET | `/api/patients/{patient_id}` | Single patient with nested medications, allergies, problems, sdoh |
| GET | `/api/observations` | List observations; filter with `?patient_id=` or `?case_id=` |
| GET | `/api/medications` | List medications; filter with `?patient_id=` |
| GET | `/api/allergies` | List allergies; filter with `?patient_id=` |
| GET | `/api/problems` | List problems; filter with `?patient_id=` |
| GET | `/api/imaging` | List imaging studies; filter with `?patient_id=` |
| GET | `/api/care-registry` | List registry entries; filter with `?patient_id=` |
| GET | `/api/sdoh` | List social-determinant observations; filter with `?patient_id=` |
| GET | `/api/protocols` | List available protocols |
| GET | `/api/protocols/{protocol_id}` | Single protocol with decision rules and thresholds |
| POST | `/api/query` | Authenticated query endpoint (requires a token; not used in standard tasks) |

List endpoints return `{ "count": N, "items": [...] }` with `limit` and
`offset`. Single-resource endpoints return a flat object.

The case detail endpoint (`/api/cases/{case_id}`) includes `findings`: an array
of `{ "finding_key", "finding_value", "source_id" }` objects that encode
clinical context. These are often the most efficient way to get symptom
presence/absence, encounter time, and allergy constraints.

Protocols include `authoritative_statuses` (always `["final"]`),
`controlled_codes` mapping template labels to observation codes, threshold
values, and decision rules. Read the protocol body carefully before making
clinical determinations.
