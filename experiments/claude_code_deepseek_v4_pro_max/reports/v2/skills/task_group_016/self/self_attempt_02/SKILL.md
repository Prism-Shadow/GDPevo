# ClinicProtocol Decision-Support Skill

## Overview

This skill covers protocol-bound clinical decision-support tasks served by the ClinicProtocol API. Each task requires fetching patient, encounter, observation, and protocol data from the API, applying protocol rules to the clinical facts, and returning a structured JSON answer that matches a provided answer template.

## Environment

The remote API base URL is provided by the environment variable `GDPEVO_ENV_BASE_URL`. All API calls use this base URL. Do not use localhost.

## API Reference

All endpoints are under the `/api/` prefix. The API returns JSON.

### Core Endpoints

| Endpoint | Query Parameters | Description |
|---|---|---|
| `GET /api/patients` | `?patient_id=` | List all patients or filter by ID |
| `GET /api/patients/{id}` | — | Single patient detail (includes active_problems, allergies, medication_summary, demographics) |
| `GET /api/encounters` | `?encounter_id=` or `?patient_id=` | List all encounters; use query params to find specific ones |
| `GET /api/protocols` | — | List all protocol summaries |
| `GET /api/protocols/{id}` | — | Single protocol detail with `local_rules` and `outputs` |
| `GET /api/observations` | `?patient_id=` | List observations; use patient_id filter per task |

**Important**: Individual resource paths like `/api/encounters/{id}` or `/api/observations/{id}` return `not_found`. Always use the list endpoint with query parameters to filter.

### Patient Record Shape

```
patient_id, name (family, given, text), birth_date, sex, identifier (MRN),
address, phone, allergies[] (substance, reaction, severity, status, category),
active_problems[] (code, display, status, recorded, notes),
medication_summary[] (medication, category, status)
```

### Encounter Record Shape

```
encounter_id, patient_id, clinician, kind, reason, start (ISO-8601),
status, timezone, facts{...}  — facts vary by encounter type
```

### Observation Record Shape

```
id, patient_id, resourceType ("Observation"), code, display, category,
status (final | preliminary | cancelled | entered-in-error),
effectiveDateTime (ISO-8601), value, unit, interpretation, notes,
panel_header (boolean), encounter_id
```

### Protocol Record Shape

```
protocol_id, title, version, effective, local_rules[] (natural-language rules),
outputs{} (enum options, thresholds, codes)
```

## General Workflow

### Step 1: Read the Answer Template

The answer template at `input/payloads/answer_template.json` defines every required key, its type, allowed enum values, list item constraints, and sort order. Treat this as the authoritative output schema. The `required_top_level_keys` array tells you exactly which keys must appear. List fields marked `"ordering": "sort_lexicographic"` must be sorted alphabetically.

### Step 2: Identify the Protocol

The prompt names the relevant patient, encounter, or case IDs. The protocol is either named directly or implied by the answer template's `primary_protocol` allowed value. Fetch the protocol by ID from `/api/protocols/{id}`.

### Step 3: Fetch Patient and Encounter Data

- Fetch the patient detail from `/api/patients/{patient_id}`.
- Fetch the encounter from `/api/encounters?encounter_id={id}`.
- If the task references a "case" ID (e.g., `CASE-CM-T001`), treat it as linked to the corresponding patient (the patient ID embeds the same letter code, e.g., `PAT-CM-T001`). There is no separate `/api/cases` endpoint — all case-level data comes from the patient record plus its observations and protocol rules.

### Step 4: Fetch Observations

Fetch observations with `GET /api/observations?patient_id={id}`. Apply filtering:

- **Status filter**: Only `"final"` observations count for clinical decisions. Exclude `preliminary`, `cancelled`, and `entered-in-error`.
- **Panel headers**: Exclude any observation where `panel_header: true`.
- **Patient identity**: Only use observations whose `patient_id` exactly matches the target patient. The system may include observations for linked-but-different patients (similar name, shared MRN prefix) — check the `patient_id` field, not the name.
- **Code matching**: Match on the exact `code` field. A LOINC code (e.g., `2823-3`) is different from a local code (e.g., `K`), even if both represent the same analyte. The protocol specifies which code to use.
- **Date windows**: When filtering by month, include all instants from the first day at 00:00:00 through the last day at 23:59:59 in the relevant timezone. An observation on the last day of the month at 23:30 is in range; one on the first day of the next month at 00:00 is not.

### Step 5: Apply Protocol Rules

Protocol `local_rules` are natural-language decision rules. Apply them systematically:

1. **Classify the patient** against each rule to determine the route/risk/assessment.
2. **Map clinical findings** to the enum values in the answer template.
3. **Resolve conflicts**: Prefer current encounter data over stale problem-list entries. An inactive problem from years ago should not override today's documented findings.
4. **Check allergies** before recommending any medication. Cross-reference patient `allergies` with medication choices.
5. **Check drug interactions**: When the protocol mentions QT-risk or other interaction concerns, check the patient's `medication_summary` for relevant categories.

### Step 6: Collect Evidence IDs

The `evidence_ids` field contains the Observation resource `id` values for the observations that directly support the clinical decision. Include only observations whose data was material to applying the protocol rules. Sort lexicographically.

### Step 7: Build the Answer JSON

- Every key from `required_top_level_keys` must be present.
- Enum fields: use exactly one of the allowed values.
- List fields: include only items from the allowed `items_enum`, sorted lexicographically.
- Nested objects: include every required sub-field.
- Do not invent values outside the allowed enums.
- ISO-8601 timestamps must include the timezone offset.

## Protocol-Specific Patterns

### Head Injury Triage (HEAD_INJURY_2026)

**Decision flow**: Encounter symptoms → red flags → risk route → CT recommendation → disposition → activity plan → follow-up timing.

**Red flag detection** is based on the encounter `facts`:
- `symptoms` array and specific fact fields (vomiting count, anticoagulant use, neuro exam, amnesia duration, waiting room observations) determine which red flags are present.
- A single red flag from the `urgent_ed` rule triggers the urgent route.
- "Increasing drowsiness" can be inferred from waiting-room observations like "hard to keep awake" or "drowsy in waiting room."
- "Repeated vomiting" means 2+ episodes or explicit notation of repeated vomiting.

**CT recommendation** follows from the risk route:
- `urgent_ed` → `urgent`
- `same_day_clinic` → `consider` (if persistent symptoms or unreliable observer) or `not_required`
- `home_observation` → `not_required`

**Activity restrictions** are always conservative for head injury:
- School: `no_school_until_evaluated` for urgent, `reduced_24_48h` for same-day, `routine_as_tolerated` for home
- Sports: `no_sports_until_cleared` for all except home observation
- Driving: `no_driving_until_symptom_free_cleared` for urgent/same-day, `routine_as_tolerated` for home

**Follow-up hours**: 24 for urgent/red-flag, 48–72 for same-day clinic, 72 for home observation.

**Contraindicated actions**: `drive_self_home` (urgent/same-day), `same_day_return_to_play` (always), `unsupervised_home_observation` (if red flags present).

### Respiratory Assessment (RESP_ACUTE_2026)

**Decision flow**: Symptoms + vitals + exam + imaging → primary assessment → site of care → antibiotic selection → required tests.

**Primary assessment**:
- `community_acquired_pneumonia` when fever + cough + (focal crackles OR CXR infiltrate/consolidation).
- `ed_evaluation_required` when O2 < 92%, confusion, hypotension, RR ≥ 24, or pleuritic chest pain with hypoxia.
- `viral_upper_respiratory_infection` or `copd_asthma_exacerbation` based on presentation without pneumonia signs.

**Site of care** maps from the assessment: `ed_evaluation` when ED criteria are met; `outpatient_treatment` when stable with O2 ≥ 92%; `supportive_care` for viral patterns.

**Antibiotic contraindication logic** (applied in order):
1. **Penicillin**: contraindicated if the patient has any penicillin-class allergy (regardless of severity).
2. **Sulfonamide**: contraindicated if the patient has a sulfa allergy.
3. **Macrolide / Fluoroquinolone**: contraindicated when the patient has an active QT-risk medication — **unless** the ED route supersedes outpatient selection. When the site of care is `ed_evaluation`, the ED monitoring capability overrides the outpatient QT concern; these classes are then NOT listed as contraindicated (though the antibiotic plan may still choose a safer option).

**Severity factors**: List all that apply from the encounter vitals, exam, and imaging. `oxygen_below_92` means O2 < 92%. `tachypnea` means RR ≥ 24.

**Return precautions**: Include all that apply from the allowed enum plus standard post-discharge warnings. `ed_now` is always included when sending to ED.

### Potassium Replacement (POTASSIUM_REPLETION_2026)

**Decision flow**: Filter observations → select latest → compare to target → calculate dose.

**Observation filtering rules**:
1. Code must be exactly the protocol's `potassium_code` (`"K"`), not the LOINC code `2823-3`.
2. Status must be `"final"`.
3. Take the single most recent by `effectiveDateTime`.
4. Note the observation `id`; this goes into `latest_potassium.observation_id`.

**Ignored observations**: Every observation returned for this patient that was NOT selected as the latest should be listed in `ignored_observation_ids` with a clear rationale:
- Wrong code (LOINC instead of local K)
- Non-final status (preliminary, entered-in-error, cancelled)
- Older timestamp (stale)

**Dose calculation**:
- Target: `protocol.outputs.target_mEq_per_L`
- Deficit = target − latest_potassium.value_meq_l (positive when below target)
- Dose = ceiling((deficit / 0.1) × 10, to nearest 10)
- In practice: round UP the raw mEq to the next multiple of 10.
- If potassium is at or above target, `replacement_required: false` and `dose_meq: 0`.

**Follow-up lab timing**:
- LOINC: `protocol.outputs.follow_up_loinc` (2823-3)
- Display: `"Serum potassium"`
- occurrenceDateTime: next calendar day at 08:00 in the encounter/local timezone.
- Priority: `routine_next_morning`

### FHIR Lab Retrieval (FHIR_LAB_RETRIEVAL_2026)

**Decision flow**: Query definition → filter observations → count matches → identify excluded.

**Query construction**: The `query` object comes from the task prompt. `resourceType` is always `"Observation"`. `code` is the LOINC or local code to search for. `month` is `YYYY-MM` format.

**Match criteria** (all must be true):
- `patient_id` exactly equals the target patient
- `code` exactly equals the query code
- `status` is `"final"`
- `panel_header` is falsy (false or absent)
- `effectiveDateTime` falls within the query month (inclusive boundaries)

**Excluded observations**: List every observation returned by the API for this patient that was considered but did NOT match. Common exclusion reasons:
- Wrong patient (`patient_id` points to a linked-but-different patient)
- Wrong code (different analyte)
- Non-final status
- Panel header
- Outside the month window
- Note observations that are just outside the window (e.g., April 30 at 23:59 for a May query) are excluded because the month boundary is strict.

**Date output**: `first_match_date` and `last_match_date` are `YYYY-MM-DD` (date only, no time component).

### Complex Care Escalation (COMPLEX_CARE_2026)

**Decision flow**: Patient chart + observations → risk level → program type → chart concerns → assessment domains → consent strategy → care plan → disciplines → follow-up → escalation triggers.

**Risk level and program type**:
- `high` + `complex_care` when the patient has high-acuity indicators: uncontrolled chronic disease with abnormal lab values (e.g., A1c > 9, eGFR < 30), multiple chronic conditions, polypharmacy (≥5 active medications), behavioral health comorbidity.
- `moderate` + `routine_care_management` when chronic conditions are present but controlled.
- `low` + `not_eligible` when no significant care-management needs.

**Chart concerns**: Map the patient's `active_problems`, observations, and `medication_summary` to the allowed enum values. Include:
- Every active chronic disease that matches an enum (e.g., `ckd_stage_4` from CKD4 problem, `uncontrolled_diabetes` from elevated A1c, `behavioral_health_history` from depression)
- Medication burden concerns (`polypharmacy` when ≥5 active medications)
- Admission history when noted in problems or referral context
- SDoH flags when address, medication costs, or access barriers are indicated

**Assessment domains**: Derived from chart concerns — each concern should map to a corresponding assessment domain that a care manager would need to confirm with the patient.

**Consent strategy codes**: These are communication protocols for care-management outreach:
- `clear_voluntary_consent` and `bounded_process_help` are baseline for all programs.
- `avoid_guarantees` when the program involves resource coordination (transportation, financial assistance, housing).
- `plain_language_*` codes apply when the patient has condition-specific scheduling needs.
- `permission_before_sensitive_topics` when behavioral health or SDoH topics are involved.
- `reflect_first_refusal` when the persona may initially decline services.

**Care plan problem areas**: At least 3 (per protocol `minimum_problem_areas`). Each problem area maps to an identified chart concern or assessment domain.

**Disciplines**: At least 2 (per protocol `minimum_disciplines`). Map to the patient's needs: `care_manager` for coordination, `clinical_pharmacist` for polypharmacy, `social_worker` for SDoH, `behavioral_health_consultant` for mental health, `primary_care_provider` for medical oversight, `respiratory_therapist` for pulmonary conditions.

**Follow-up cadence**: `weekly` for complex care (per protocol default), `biweekly` for routine care management, `monthly` for low-risk.

**Escalation triggers**: Pick the triggers that match the patient's actual risks — clinical deterioration indicators (dyspnea/weight gain, extreme glucose), access barriers (transportation, housing), and behavioral health safety (PHQ-9 item 9).

**`avoid_unsupported_guarantees`**: Always `true` for any program involving resource coordination per the protocol rule about never guaranteeing lower costs, ride availability, dialysis-slot flexibility, or assistance approval.

## Evidence ID Conventions

- Evidence IDs are always the `id` field from Observation resources (e.g., `"OBS-H-T001-GCS"`).
- Include only observations whose data was directly material to the protocol decision.
- Sort lexicographically.
- Do NOT include: encounter IDs, patient IDs, protocol IDs, or observation IDs that were examined but not relied upon.
- For the FHIR lab retrieval task, `evidence_ids` is NOT a required field — the task's answer template uses different key names.

## Common Pitfalls

1. **Stale vs. current data**: An inactive problem-list entry from years ago must not override current encounter findings. The encounter's `stale_conflict` field often explicitly warns about this. Trust the current encounter.

2. **Observation status matters**: Only `"final"` counts for clinical decisions. `"preliminary"` and `"entered-in-error"` values are traps — they often have values close to but different from the final result.

3. **Patient identity confusion**: Linked patients (e.g., `PAT-L-T01` for `PAT-L-T001`) share similar demographics and MRNs. Always match on the exact `patient_id` string, not by name or MRN prefix.

4. **Code vs. LOINC**: A local code (`"K"`) and a LOINC code (`"2823-3"`) are different identifiers even when they represent the same analyte. The protocol specifies which code system to use.

5. **ED route supersedes QT restrictions**: In the respiratory protocol, the macrolide and fluoroquinolone QT-risk contraindication is lifted when the patient is routed to ED — ED-based monitoring changes the risk calculus. But penicillin/sulfonamide allergies are never superseded.

6. **Month boundary inclusiveness**: A month window includes the last day at 23:59:59 but NOT the first day of the next month at 00:00:00. An observation timestamped April 30 at 23:59 is NOT in May.

7. **Lexicographic sort**: All list fields in answer templates specify `"sort_lexicographic"` — this is standard string sort, not numeric or chronological.

8. **Dose rounding**: Potassium replacement doses round UP to the next 10 mEq. A calculated dose of 30 stays 30; a calculated dose of 31 becomes 40.

9. **Missing case endpoint**: There is no `/api/cases` endpoint. Case-linked tasks use the patient endpoint and observations. The case ID (`CASE-*-T*`) maps to the patient with the matching letter code (`PAT-*-T*`).

10. **Encounter access pattern**: Do NOT use `/api/encounters/{id}` — it returns `not_found`. Use `GET /api/encounters?encounter_id={id}` instead.

11. **Active problem filtering**: Only `"active"` problems drive current clinical decisions. Problems with `"inactive"` status are historical context only.

12. **Answer template is the contract**: Every key must be present, every value must come from the allowed enum, and list items must be sorted. A missing key or an invented enum value is a schema violation.

## Step-by-Step Task Execution Pattern

1. Read `input/prompt.txt` and `input/payloads/answer_template.json`.
2. Identify the patient ID, encounter/case ID, and protocol from the prompt.
3. Fetch the protocol: `GET /api/protocols/{protocol_id}`.
4. Fetch the patient: `GET /api/patients/{patient_id}`.
5. Fetch the encounter: `GET /api/encounters?encounter_id={id}` (if applicable).
6. Fetch observations: `GET /api/observations?patient_id={patient_id}`.
7. Filter observations per protocol rules (status, code, date, patient identity).
8. Apply protocol `local_rules` to the clinical facts.
9. Map findings to answer template enum values.
10. Collect evidence observation IDs.
11. Build the JSON output, validating every field against the template.
12. Sort all list fields lexicographically.
13. Output the single JSON object.
