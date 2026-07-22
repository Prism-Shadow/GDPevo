# Synthetic Clinic Clinical Decision-Support Skill

## Purpose

This skill guides an agent through completing a structured clinical decision-support task against a synthetic clinic FHIR-like REST API. The agent reads a task prompt, retrieves structured clinic data from the runtime environment, and returns a single JSON object conforming to the provided answer template.

## When to Use

Invoke this skill when:
- A task directory under `train_tasks/train_NNN/input/` contains `prompt.txt` and `payloads/answer_template.json`.
- A file named `environment_access.md` is present at the workspace root providing the runtime base URL, credentials, and allowed endpoints.

## Step-by-Step Procedure

### Step 1 — Discover the Inputs

From the task directory (e.g., `train_tasks/train_001/input/`) read exactly two artifacts:

1. **`prompt.txt`** — Describes the clinical scenario, the target case identifier, and which clinical domains to review (e.g., observations, medications, allergies, imaging, protocols, care registry, social determinants of health). It references `<TASK_ENV_BASE_URL>` as a placeholder for the runtime API.
2. **`payloads/answer_template.json`** — Declares the required JSON output shape. It defines:
   - `required_top_level_keys` — every key that must appear in the response.
   - `fields` (or `field_specification`) — per-key types, allowed enum values, nullable rules, nested object schemas, ordering rules, and numeric precision constraints.
   - `output_rule` (or `output_rules`) — final formatting constraints (no markdown, no prose, no extra keys, null only where permitted).

### Step 2 — Configure the Runtime Connection

Read `environment_access.md` from the workspace root. It contains:

```
base_url: <string>
credentials:
  <header-name>: <token-value>
allowed_endpoints:
  - <METHOD> <path-template>
  ...
```

Resolve `<TASK_ENV_BASE_URL>` in the prompt to the `base_url` value. Use the listed credentials as HTTP headers on every request to the runtime. Only call endpoints listed under `allowed_endpoints`. The runtime is read-only — never attempt POST (except `/api/query` if listed), PUT, PATCH, or DELETE.

### Step 3 — Retrieve Clinical Data

Follow this retrieval order, using only the allowed endpoints:

1. **Retrieve the case record.** Use `GET /api/cases/{case_id}` with the case identifier from the prompt. The case resource links to a patient and may embed or reference encounters, observations, and other clinical resources.

2. **Retrieve the patient record.** Extract the patient identifier from the case and call `GET /api/patients/{patient_id}`. Note demographic anchors, problem-list entries, and any care-team or registry references.

3. **Pull domain-specific resources.** Based on what the prompt asks for and what endpoints are allowed, retrieve:
   - `GET /api/observations` — vital signs, lab results (serum potassium, HbA1c, phosphorus, etc.), clinical scores.
   - `GET /api/medications` — active and historical medication lists.
   - `GET /api/allergies` — documented allergies and intolerances (penicillin, sulfonamide, macrolide, tetracycline, etc.).
   - `GET /api/imaging` — radiology reports and impressions (CXR, CT head, etc.).
   - `GET /api/problems` — active and resolved problem-list entries.
   - `GET /api/protocols` or `GET /api/protocols/{protocol_id}` — clinical protocols referenced by the case or relevant to the decision.
   - `GET /api/care-registry` — risk scores, program enrollment flags, care-management eligibility data.
   - `GET /api/sdoh` — social determinants of health (transportation, food, financial barriers).

4. **Use the query endpoint when needed.** If `POST /api/query` is allowed, use it to search for observations by code, date range, status, or patient when direct GET scan is insufficient (e.g., "find all final serum potassium observations for this patient in March 2026").

### Step 4 — Determine Clinical Answers

For each required key in the answer template, derive the answer from the retrieved data:

- **Identifiers** (`task_id`, `case_id`, `patient_id`): Copy from the prompt or template's `expected_constant`/`required_value` annotations, or extract from the case/patient record.
- **Enumerated assessments** (`primary_assessment`, `risk_level`, `risk_tier`, `disposition`, `protocol_gate`, etc.): Map the clinical data (observations, protocol criteria, exam findings) to the allowed enum values listed in the template. Choose the value best supported by the clinical facts — do not guess.
- **Lists** (`red_flags`, `recommended_tests`, `priority_problems`, `referrals`, etc.): Include only values from the allowed set that are supported by the data. Omit unsupported values. Unless the template states an explicit ordering rule, list order is not semantically significant.
- **Booleans** (`replacement_required`, `lab_found`, safety-check fields, etc.): Assert based strictly on the retrieved data. A safety-check boolean such as `no_false_loc` must be `true` when the record does **not** contain a false claim (e.g., loss of consciousness was not claimed when it did not occur) and `false` when the record does contain a false claim.
- **Numeric values** (`latest_potassium`, `oral_dose_mEq`, `risk_score`, `hba1c_percent`, etc.): Copy from the corresponding observation resource with the precision specified in the template (e.g., one decimal place for mmol/L, two decimal places for probability). Use `null` only when the template explicitly allows it for that field.
- **Nested objects** (`medication_plan`, `follow_up`, `medication_order`, `contraindications`, `numeric_anchors`, etc.): Populate every required sub-key from the data. Leave nullable sub-keys as `null` only when the data is absent and the template permits it.
- **Timestamps** (`current_time`, `effective_time`, `scheduled_time`, `window.from`, `window.to`): Use ISO-8601 UTC format with a trailing `Z`. Derive window boundaries from the prompt narrative (e.g., "March 2026" → `"2026-03-01T00:00:00Z"` to `"2026-04-01T00:00:00Z"`).
- **Evidence IDs** (`evidence_ids`, `source_provenance`): Collect the resource identifiers (case, patient, observation, imaging, protocol, medication, allergy, registry) that were consulted to produce the answer. Order them as specified by the template (e.g., case identifier first, then clinical sources in descending relevance).

### Step 5 — Validate and Return

Before returning, verify:

1. Every key listed in `required_top_level_keys` is present in the response.
2. Every enum field uses only values from the `allowed_values` list.
3. Every boolean field is `true` or `false` (not a string, not 1/0).
4. Every numeric field matches the stated precision.
5. Every `required_keys` sub-key inside nested objects is present.
6. No extra top-level keys are included beyond those in the template.
7. The output is a single JSON object with no surrounding markdown fences, no comments, and no explanatory prose.
8. `null` appears only where the field specification explicitly permits it (`"type": ["string", "null"]`, `"type": "string_or_null"`, `"nullable": true`).
9. List items in `matched_observation_ids`, `excluded_observation_ids`, and `evidence_ids` follow any stated ordering rule (e.g., ascending by `effective_time`, then by `observation_id`).

Return the JSON object as the sole output.

## Common Clinical Decision Patterns

These patterns recur across task types and should guide interpretation of the retrieved data:

### Allergy-Aware Medication Planning

When the template includes fields like `avoid_allergens` or `medication_plan`, cross-reference the patient's allergy list against the medication plan. If the patient has a documented penicillin allergy, `avoid_allergens` should include `"penicillin"` and the antibiotic strategy must avoid beta-lactams. The corresponding safety-check boolean (`no_penicillin_or_sulfa`) must be `false` if a contraindicated medication class appears in the plan.

### Observation Window Retrieval

When the task requires finding observations within a time window:
- Use `POST /api/query` with code, patient, date range, and status filters if available.
- Distinguish **matched** observations (correct patient, correct code, correct status (final), inside the window) from **excluded** observations (wrong patient, wrong code, wrong status, or outside the window, but still clinically relevant to the case).
- The `latest_final` object should reference the most recent matching observation by `effective_time`.

### Protocol Gate Determination

When the template includes a `protocol_gate` field:
- Compare the latest relevant lab value against protocol-defined thresholds (e.g., normal range, low/critical thresholds).
- Map the comparison outcome to the appropriate gate enum value.
- Derive the `repeat_lab` recommendation from the protocol's follow-up rules.

### Risk Stratification

When `risk_level`, `risk_tier`, or `risk_score` are required:
- Use structured risk scores from the care registry or calculate from clinical factors (lab values, vital signs, comorbidity count, recent admissions).
- Map numeric scores to tier labels (`low`, `moderate`, `intermediate`, `high`) per the protocol or template's enum set.

### Care-Management Routing

When the task involves care-management decisions:
- Determine program eligibility (`complex_care_management`, `routine_case_management`, `not_eligible`) from registry data and clinical complexity.
- Select `priority_problems` from active problem-list entries and SDOH barriers.
- Select `referrals` based on identified gaps (pharmacy for polypharmacy, social work for barriers, specialist coordination for dialysis, etc.).
- Populate `source_provenance` by categorizing each data point as either a chart fact (observable in structured clinical data) or a member disclosure (requiring patient interview to confirm, such as transportation or financial barriers).

### Output Rule Compliance

All templates share these output constraints:
- Return exactly one JSON object.
- Do not wrap it in markdown code fences.
- Do not include comments, trailing commas, or explanatory prose.
- Use controlled enum values rather than free-text descriptions for scored status and action fields.
- Extra top-level keys beyond those in `required_top_level_keys` are either forbidden or ignored — prefer omitting them.
