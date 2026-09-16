---
name: clinic-decision-support
description: "Protocol-bound clinical decision support for a synthetic FHIR-like clinic REST API. Use when a prompt references a clinic case ID, a structured answer template with controlled enums, and a task environment base URL for fetching patient data, observations, protocols, and related clinical resources. Covers respiratory assessment, pediatric head injury, potassium replacement, care-management routing, observation-window retrieval, and similar protocol-driven structured-answer tasks."
license: MIT
compatibility: designed for deepagents-code
---

# Clinic Decision Support

## Quick Start

Read the prompt to identify the target `case_id`, the `answer_template.json` path,
and the `<TASK_ENV_BASE_URL>`. Then follow this sequence:

1. Read `input/payloads/answer_template.json` first — it defines every field, its
   allowed values, and the output structure.
2. Fetch the case composite at `GET {BASE}/api/cases/{case_id}`. It returns
   `patient`, `case`, `observations`, `findings`, `imaging`, `medications`,
   `allergies`, `problems`, `care_registry`, and `sdoh` in one payload.
3. Identify which protocols are relevant. If the case response names a protocol
   or the task description implies one, fetch it from
   `GET {BASE}/api/protocols/{protocol_id}`.
4. Apply protocol decision rules to the clinical facts, then map every finding
   to one of the template's controlled enum values.
5. Return exactly one JSON object matching the template, with no markdown or
   prose outside the JSON.

## Core API Summary

The environment provides these GET endpoints at `{BASE}` (no auth):

| Endpoint | Description |
|----------|-------------|
| `/api/patients` | All patients; `patient_id` is the join key |
| `/api/patients/{patient_id}` | Single patient detail |
| `/api/cases` | All cases; each has `case_type`, `patient_id`, `summary` |
| `/api/cases/{case_id}` | Composite: case + patient + observations + findings + imaging + medications + allergies + problems + care_registry + sdoh |
| `/api/observations` | All observations; filter on `patient_id`, `code`, `status`, `effective_time` |
| `/api/medications` | All medication records |
| `/api/allergies` | All allergy records; `status` is `active` or `inactive` |
| `/api/problems` | All problem-list entries (ICD-10 codes) |
| `/api/imaging` | All imaging studies; `status` is `final` or `preliminary` |
| `/api/care-registry` | Care-management registry records |
| `/api/sdoh` | Social determinants of health |
| `/api/protocols` | All protocol identifiers and titles |
| `/api/protocols/{protocol_id}` | Full protocol with decision rules |

Full response shapes and field semantics are in [references/api_schema.md](references/api_schema.md).

## Protocol Interpretation

Protocols live at `/api/protocols/{protocol_id}` and contain a `body` with
decision rules. See [references/protocol_guide.md](references/protocol_guide.md)
for detailed interpretation patterns. Key conventions:

- **`authoritative_statuses`**: Only observations with `status` in this list
  count for protocol gates. Typically `["final"]`.
- **Thresholds**: Numeric comparison operators are named explicitly, e.g.
  `oxygen_saturation_room_air_less_than` means "below this value triggers."
- **`controlled_codes`**: Maps clinical concepts (e.g. `serum_potassium`) to
  observation `code` values (e.g. `"K"`). Use these codes when filtering
  observations, not free-text display names.
- **`allergy_rule`**: Describes how to constrain medication choices from the
  allergy list. Apply this before selecting antibiotic strategy.
- **`excluded_statuses`**: Observations with these statuses must not count for
  protocol gates (common list: `preliminary`, `entered-in-error`, `canceled`).

## Common Decision Patterns

### Filtering Observations

For tasks that require finding a specific lab in a time window:
- Filter by `patient_id`, `code` matching the protocol's controlled code,
  `status` = `"final"`, and `effective_time` inside the window (inclusive
  start, exclusive end unless the template says otherwise).
- Sort results by `effective_time` ascending, then `observation_id` ascending
  as a tiebreaker.
- The latest entry is the last in sorted order.
- Observations that match the patient and code but fail on date or status go
  into `excluded_observation_ids`.
- Observations with a non-matching `code` but same patient and window also go
  into excluded observations.

### Allergy-Aware Medication Selection

- Collect all `active` allergies for the patient from the case composite.
- Map allergen names to the template's `avoid_allergens` enum: e.g. "penicillin"
  allergy → `"penicillin"`, "sulfonamide antibiotics" → `"sulfonamide"`.
- Choose an antibiotic strategy whose class does not appear in the avoid list.

### Risk Stratification

- Protocols list triggers for escalation (e.g. urgent route, ed transfer).
- If any numeric threshold is crossed (SpO2 < 90, K < 3.0, risk_score >= 0.75)
  or any named symptom is present, the higher tier applies.
- Otherwise, use the lower tier described by the protocol's supportive or
  routine branch.

### Protocol Gate Determination

- If the latest final observation has `value_number` >= target, the gate is
  `satisfies_recent_final_normal`.
- If below target but above urgent threshold, the gate indicates need for
  repletion.
- If below urgent threshold or urgent symptoms exist, the gate is
  `recent_final_critical_or_urgent`.
- If no final observation in the window, the gate is `no_final_lab_in_window`.

### Safety Checks

Safety-check booleans assert that a dangerous claim was NOT made:
- `no_penicillin_or_sulfa`: True when the medication plan avoids both classes.
- `no_normal_cxr_claim`: True when the imaging impression is abnormal (e.g.
  consolidation present).
- `no_clear_lungs_claim`: True when lung findings are documented.
- `no_false_loc`: True when loss of consciousness was not reported.
- `no_false_vomiting`: True when repeated vomiting was not reported.
- `no_false_photophobia`: True when photophobia was not reported.

### Numeric Anchors and Precision

- Read numeric values from observations and findings.
- Match the precision specified in the template: one decimal place for lab
  values, two decimal places for risk scores, integer for hours and counts.
- For blood pressure, format as `"systolic/diastolic"` (e.g. `"152/88"`).
- For doses, include a space between the number and unit (e.g. `"100 mg"`).

### Evidence Identifiers

Include identifiers for the key sources used: the case ID, observation IDs
for the primary lab or finding, imaging IDs for relevant studies, and protocol
IDs when they inform the decision. List the case identifier first, then other
sources. Only include identifiers that were actually used in the decision.

### Urgent Actions

When protocols list urgent-branch symptoms (palpitations, syncope, ECG
abnormality, severe weakness), and those symptoms are present, select the
matching urgent-action enums from the template. Sort by clinical action
sequence. Use an empty list when no urgent action applies.

### Program Routing

For care-management routing: check registry risk score against the protocol's
`high_predictive_risk_min`, count chronic conditions, check for recent
admission, dialysis, heart failure, and uncontrolled diabetes against the
`complex_care_supporting_triggers`. Map SDOH domains to the social-work
referral domains list and threshold.

## Reference Files

- [references/api_schema.md](references/api_schema.md) — Full API response shapes
  and field-by-field semantics for every endpoint.
- [references/protocol_guide.md](references/protocol_guide.md) — How to read
  protocol decision documents and translate rules into template enum values.

## Output Rule

Always return exactly one JSON object. No markdown fences, no comments, no
extra top-level keys beyond what the template requires. Use `null` only where
the template explicitly permits it. String values use controlled enum entries
from the template, not free-text prose.
