---
name: synthetic-clinic-protocol
description: >-
  Protocol-bound clinical decision support for the Harborview Synthetic Clinic runtime.
  Use when presented with a task that provides a clinic case identifier, an answer
  template JSON schema, and prompt text directing the agent to a synthetic clinic
  runtime environment accessible via HTTP API. Covers adult respiratory assessment,
  pediatric head injury triage, potassium replacement, care-management routing, and
  observation-window retrieval. The skill provides the endpoint catalog, case-type to
  protocol mapping, protocol decision rules, and a repeatable retrieve-map-decide-fill
  workflow.
---

# Synthetic Clinic Protocol

## Overview

This skill covers the Harborview Synthetic Clinic runtime, a read-only HTTP API that
serves synthetic patient records, observations, medications, allergies, problems,
imaging, SDOH, care-registry data, and clinical decision protocols. Tasks arrive as
prompts naming a case ID and an answer template. The solver retrieves the case bundle,
maps its case type to the appropriate protocol, applies the protocol decision
thresholds and enumerated values to the clinical data, and returns a single JSON
object matching the supplied answer template.

## Workflow

### 1. Read the prompt and locate the answer template

The prompt names a case ID and references `input/payloads/answer_template.json`.
Read the answer template first: it defines the exact JSON shape, required keys,
allowed enum values, nullability rules, and numeric precision requirements.
Every value in your final answer must come from an allowed set or follow the
template precision rules.

### 2. Retrieve the case bundle

Call the case detail endpoint:

```
GET {TASK_ENV_BASE_URL}/api/cases/{case_id}
```

`TASK_ENV_BASE_URL` is provided separately in the task environment access
document. The response is a JSON bundle containing sections listed in
[references/api_reference.md](references/api_reference.md).

### 3. Map case type to protocol

Use `case.case_type` from the bundle to select the protocol:

| case_type | Protocol ID |
|---|---|
| `acute_respiratory` | `RESP-CAP-2026` |
| `pediatric_head_injury` | `PEDS-HEAD-2026` |
| `potassium_repletion` | `K-REPLETION-2026` |
| `care_management` | `CM-HIGH-RISK-2026` |
| `observation_window` | `OBS-WINDOW-2026` |

Retrieve the protocol:

```
GET {TASK_ENV_BASE_URL}/api/protocols/{protocol_id}
```

### 4. Apply protocol rules to clinical data

Each protocol defines thresholds, enumerated rule paths, and controlled
vocabularies that map the clinical data to the output fields. The full protocol
decision rules for all five case types are in [references/protocols.md](references/protocols.md).
Load that file when you have identified the case type and protocol.

General decision principles that apply across all protocols:

- **Status filter**: Only observations with `status` = `"final"` are authoritative
  for protocol decisions, unless a protocol explicitly accepts other statuses.
  Preliminary, entered-in-error, and cancelled observations are excluded.
- **Allergy constraint**: When the answer template includes medication decisions,
  cross-reference the patient active allergies (`allergen` field with
  `status` = `"active"`) against the medication class. Avoid implicated classes.
- **Evidence IDs**: Collect the case_id and all observation, imaging, and
  source identifiers whose values directly informed your decisions. List them
  in descending order of clinical relevance, case_id first when included.
- **Safety checks**: When the template contains boolean safety assertions (e.g.,
  `no_penicillin_or_sulfa`, `no_false_loc`, `no_normal_cxr_claim`), set them
  by verifying the clinical data against the assertion claim. A safety check
  is `true` when the claim stated in the key name is correct given the data.
- **Enum-only values**: Never substitute free-text prose for a field that has
  enumerated allowed values. If no enum matches exactly, choose the closest
  fit and ensure it is in the allowed list.

### 5. Fill the answer template

Populate every required key in the answer template JSON with values derived
from the clinical data and protocol rules. Follow these rules:

- `task_id` and `case_id`: Copy from the prompt and template (often specified
  as `required_value` or `expected_constant`).
- `patient_id`: From `case.patient_id` in the bundle.
- Timestamps: Use ISO-8601 UTC with trailing Z. The `current_time` or
  `effective_time` comes from the `findings` section or the most recent
  observation timestamp.
- Numeric values: Use the precision specified in the template. Round to the
  specified decimal places.
- Lists: No semantic ordering is required unless the template explicitly
  states otherwise. Include each value at most once.
- Nullable fields: Use `null` only where the template permits. When a
  medication is not recommended, null the medication-specific fields.
- Output exactly one JSON object with no surrounding markdown, comments,
  or extra top-level keys.

### 6. Return the JSON object

Return the completed JSON object. Do not include narrative text outside it.

## Decision guidance by case type

### acute_respiratory

- Identify red flags from oxygen saturation (borderline 92-93% = `hypoxemia_92_93`,
  below 90% = `hypoxemia_below_90`), pleuritic chest pain presence, confusion,
  respiratory rate >= 30, systolic BP < 90.
- Risk level depends on red flag count and severity. Moderate when there are
  borderline O2 findings without full ED triggers. High when ED escalation
  thresholds are met.
- Antibiotic strategy must avoid allergens. Map the active allergy list to
  the `avoid_allergens` enum values. Penicillin allergy -> avoid penicillin;
  sulfonamide allergy -> avoid sulfonamide.
- Disposition is `outpatient_close_followup` unless ED triggers are met.
- Follow-up is 48 hours to primary care for outpatient disposition.
- Evidence IDs include the case ID, imaging ID, and key observation IDs.
- Safety checks: `no_penicillin_or_sulfa` is true when the patient has active
  penicillin/sulfonamide allergies and the plan correctly avoids them.
  `no_normal_cxr_claim` is true when the CXR shows abnormal findings.
  `no_clear_lungs_claim` is true when lung exam or imaging shows consolidation.

### pediatric_head_injury

- Red flags include `head_impact` (always present), `mild_nausea`,
  `coordination_symptom_observe`. Absent red flags are the serious triggers
  that are NOT present: `loss_of_consciousness`, `repeated_vomiting`, `seizure`,
  `focal_weakness`, `worsening_headache`, `basilar_skull_signs`, `photophobia`.
- GCS of 15 and no LOC -> `no_immediate_ct`.
- Restrictions include cognitive/physical rest, return-to-learn accommodations,
  no high-risk sports until cleared, and no driving until symptom-free.
- Follow-up is 48 hours to primary care or concussion recheck.
- Safety checks confirm the absence of false claims about LOC, vomiting, photophobia.

### potassium_repletion

- Identify the latest `final` serum potassium (code `"K"`) observation.
  Ignore preliminary results and whole-blood potassium (code `"6298-4"`).
- Calculate the dose: for every 0.1 mmol/L below the protocol target (3.5),
  add 10 mEq, rounded to nearest 10 mEq. Only when the urgent branch is false.
- The urgent branch triggers when any of: potassium < 3.0, dialysis-dependent
  ESRD, ECG abnormality, severe renal contraindication, or symptoms
  (palpitations, syncope, weakness with arrhythmia concern).
- eGFR comes from the observation with code `"33914-3"`.
- Follow-up lab LOINC is `2823-3`, scheduled for the next morning.
- Sort `urgent_actions` by clinical sequence when non-empty; empty list otherwise.
- The NDC for routine oral potassium chloride is `40032-917-01`.

### care_management

- Risk tier derives from the registry `risk_score`: >= 0.75 -> `high`.
- Program eligibility requires chronic_condition_count >= 3, plus supporting
  triggers such as recent admission, dialysis/ESRD, heart failure, or
  uncontrolled diabetes. `complex_care_management` when multiple triggers
  are present and risk is high.
- Priority problems are selected from the problem list, lab values, and SDOH
  barriers. Map clinical conditions to the allowed enum codes.
- Numeric anchors come from observations: HbA1c from code `"4548-4"`,
  phosphorus from code `"2777-1"`, blood pressure from systolic/diastolic
  observation pairs.
- Pharmacist referral triggers at medication_count >= 10, insulin use, or
  high-risk diuretic/electrolyte regimens.
- Social work referral triggers when >= 2 SDOH domains are moderate or severe.
- Outreach stance is `permission_based_plain_language` when the member has
  expressed preferences about contact timing or is reluctant.
- Care plan minima: min_problem_count >= 3, weekly contact, member-stated
  priority required, minimum 2 disciplines.
- Source provenance distinguishes chart-derived facts (from observations and
  registry) from member-disclosed facts (from SDOH with source `"member-disclosed"`).

### observation_window

- The window bounds come from the `findings` section (window_start, window_end).
- Only observations with code matching `target_code` (typically `"K"`),
  status `"final"`, and patient_id matching the case patient belong in
  `matched_observation_ids`.
- Sort matched observations by effective_time ascending, then observation_id
  ascending.
- Excluded observations are those relevant to the case review but disqualified
  by date, code, or status: outside the window, wrong code, wrong patient,
  or non-final status.
- `latest_final` is the last (most recent) matched observation.
- `protocol_gate` is determined by the latest final value: normal range
  -> `satisfies_recent_final_normal`, low -> `recent_final_low_repletion_needed`,
  critical -> `recent_final_critical_or_urgent`, absent -> `no_final_lab_in_window`.
- `repeat_lab.recommended` is false when the gate is satisfied; true when
  a gap requires follow-up.

## References

- [references/protocols.md](references/protocols.md) — Full protocol thresholds, enum mappings, and decision trees for all five case types. Load after identifying the case type.
- [references/api_reference.md](references/api_reference.md) — Complete API endpoint catalog with response structures and query parameters.
