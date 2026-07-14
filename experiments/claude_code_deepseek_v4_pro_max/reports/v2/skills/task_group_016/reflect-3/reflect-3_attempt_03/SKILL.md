# ClinicProtocol Decision Support Skill

## Overview

This skill covers structured clinical decision-support tasks backed by a FHIR-style ClinicProtocol API. Each task pairs a patient (and optionally an encounter or case) with a versioned protocol card. The API returns patients, encounters, observations, and protocol rule sets. Your job is to apply the protocol rules to the available data and produce a single JSON answer object matching the provided template.

---

## Workflow Rules

### 1. Protocol First
Always fetch and read the relevant protocol **before** making any decisions. The protocol defines:
- Decision thresholds and trigger conditions
- Output enumeration values (exact allowed strings)
- Exclusion and filtering rules
- Calculation formulas (e.g., dosing math)

Every protocol has `local_rules` (natural-language decision rules) and `outputs` (structured constraints). Use both.

### 2. Gather All Relevant Data
For each task, fetch in parallel or sequentially:
- **Patient detail** from `/api/patients/{patient_id}` — includes active problems, allergies, medication summaries, demographics
- **Encounter data** from `/api/encounters` filtered to the target encounter — includes vitals, exam findings, symptoms, mechanism, clinician notes
- **Observations** from `/api/observations?patient_id={id}` (and optionally `&encounter_id={id}`) — includes labs, vitals, imaging results
- **Protocol detail** from `/api/protocols/{protocol_id}` or the full list from `/api/protocols`

The patient **list** endpoint (`/api/patients`) returns only summary fields. Always fetch the detail endpoint (`/api/patients/{id}`) for allergies, problems, and medications — these drive contraindication and risk decisions.

### 3. Apply Protocol Rules Systematically
Work through each protocol rule in order:
1. Identify qualifying observations (correct code, correct patient, correct time window, status=final)
2. Apply thresholds from the protocol to the qualifying data
3. Map clinical findings to protocol-defined categories (red flags, severity factors, risk levels)
4. Derive downstream decisions (disposition, medications, follow-up) from the risk category
5. Cross-reference patient allergies and active medications against protocol contraindication tables

### 4. Validate Against the Template
Before submitting, verify every top-level key is present, every enum value is from the allowed set, and every list is sorted lexicographically.

---

## API Usage Habits

### Known Endpoints
| Endpoint | Method | Purpose |
|---|---|---|
| `/api/patients` | GET | List all patients (summary only) |
| `/api/patients/{id}` | GET | Patient detail with allergies, problems, medications |
| `/api/encounters` | GET | List all encounters with full facts |
| `/api/observations?patient_id={id}` | GET | Observations for a patient |
| `/api/observations?patient_id={id}&encounter_id={id}` | GET | Observations scoped to one encounter |
| `/api/protocols` | GET | List all protocol cards |
| `/api/protocols/{id}` | GET | Single protocol with local_rules and outputs |

The API is read-only. There are no write, create, update, or delete operations available to you.

### Query Conventions
- Observation queries accept `patient_id` and optionally `encounter_id` as query parameters
- All list responses include a `count` field
- Encounter facts are embedded in the encounter object, not in a separate endpoint
- There is no dedicated `/api/cases`, `/api/evidence`, or `/api/admissions` endpoint — case-level data, when needed, is embedded in patient detail or derived from protocol rules applied to observations

---

## Observation Filtering Rules

These rules apply to **every** task that uses Observation resources:

1. **Status filter**: Only `"status": "final"` observations are valid for clinical decisions.
   - Reject: `"preliminary"`, `"cancelled"`, `"entered-in-error"`
2. **Panel header filter**: Observations with `"panel_header": true` are structural containers, not clinical values. Always exclude them.
3. **Code matching**: Match by the exact `"code"` field, not the `"display"` name. A protocol may specify a local code (e.g., `"K"`) that differs from the standard LOINC code for the same analyte.
4. **Patient matching**: Only use observations where `patient_id` matches the target patient exactly.
5. **Staleness**: Observations with `"notes"` containing markers like "stale", "old", or "not the current event" should be ignored. Use the **most recent** qualifying observation.
6. **Time windows**: When a protocol specifies a month or date range, apply it to `effectiveDateTime`. Month windows are inclusive of the full calendar month in the observation's local timezone.

### Ignored Observation IDs
When a task asks for `ignored_observation_ids`, include **every** observation for that patient that was examined but disqualified — entered-in-error, preliminary, wrong code, older/stale finals, and panel headers. Sort lexicographically.

---

## Output Field Conventions

### Lexicographic Sorting
**Every** list field in the answer template must be sorted lexicographically (standard string sort). The template explicitly states `"ordering": "sort_lexicographic"` on list fields. This applies to:
- `red_flags_present`, `contraindicated_actions`, `evidence_ids`
- `severity_factors`, `required_tests`, `contraindicated_antibiotic_classes`, `return_precautions`
- `chart_concerns`, `required_assessment_domains`, `consent_strategy_codes`, `care_plan_problem_set`, `disciplines`, `escalation_triggers`
- `matched_observation_ids`, `excluded_observation_ids`, `ignored_observation_ids`

### Enum Values
Only use exact string values from the `"allowed"` arrays in the answer template. Never invent or approximate a value.

### Date/Time Formats
- `effectiveDateTime` and `occurrenceDateTime`: ISO-8601 with timezone offset (e.g., `"2026-07-06T08:05:00-05:00"`)
- Date-only fields (`first_match_date`, `last_match_date`): `"YYYY-MM-DD"` format
- Month fields: `"YYYY-MM"` format
- `current_time`: ISO-8601 with timezone offset

### Numeric Precision
When a template specifies `"precision": 1`, provide exactly one decimal place (e.g., `3.2` not `3.20` or `3`).

---

## Decision Rules by Domain

### Head Injury Triage
- Map encounter symptoms and findings to protocol red flags **exactly** — use only the terms listed in the red_flags_present enum
- `repeated_vomiting` requires 2+ episodes documented in the encounter
- `increasing_drowsiness` is triggered by observer reports of difficulty staying awake, not just patient-reported fatigue
- `worsening_headache` requires evidence of escalation, not just presence of headache
- Risk level determines CT recommendation: urgent_ed → urgent, same_day_clinic → consider (with qualifiers), home_observation → not_required
- Disposition maps directly from risk level: urgent_ed → send_to_ed_now, same_day_clinic → same_day_clinic_followup, home_observation → home_with_observation
- Follow-up hours: 24 for urgent/red-flag, 48-72 for same-day clinic, 72 for home observation
- Activity restrictions: always restrict sports (no_sports_until_cleared) and driving (no_driving_until_symptom_free_cleared) when symptoms or neurologic concerns exist; restrict school only for urgent cases
- Contraindicated actions: include all three (drive_self_home, same_day_return_to_play, unsupervised_home_observation) for urgent ED cases

### Respiratory Assessment
- Primary assessment and site of care are **separate concepts**: assessment is the clinical diagnosis (e.g., community_acquired_pneumonia), site of care is the recommended setting (e.g., ed_evaluation)
- ED criteria: O2 < 92% on room air, RR ≥ 24, confusion, hypotension, or pleuritic chest pain with hypoxia — any one triggers ed_evaluation
- `oxygen_below_92` and `oxygen_92_to_94` are mutually exclusive — use the one matching the actual SpO2 value
- `lobar_consolidation` maps to CXR findings of infiltrate or consolidation
- Antibiotic choice: cross-reference patient allergies AND active QT-risk medications against the protocol's antibiotic table
- The "ED route supersedes" clause in contraindication rules means QT-based restrictions may be waived when the patient is routed to ED — but true allergies (anaphylaxis, angioedema) are never superseded
- Return precautions: include all that are clinically relevant for the assessment, not just the most severe

### Potassium Replacement
- Find the **most recent** Observation where code equals the protocol's specified code (e.g., `"K"`) and status is `"final"`
- Ignore observations with a different code even if they measure the same analyte (e.g., LOINC `2823-3` vs local code `"K"`)
- Dose calculation: `dose = ceil((target - value) / 0.1) * 10`, rounding up to the next 10 mEq
- If value ≥ target, `replacement_required` is `false` and `dose_meq` should be `0`
- Follow-up lab timing: next calendar day at the hour specified by the protocol, in the local timezone from the encounter or `current_time`
- The medication_order fields are fixed by the protocol (drug, NDC, route, intent) — do not vary them
- All other observations for that patient go into `ignored_observation_ids`

### FHIR Lab Retrieval
- Match by: exact patient_id + exact code + month window
- Month window: from first day 00:00:00 to last day 23:59:59 in the observation's local timezone
- Count only final, non-panel observations that match all criteria
- `excluded_observation_ids`: include only observations that match patient + code + month but are disqualified by status (preliminary, cancelled, entered-in-error) or type (panel_header). Observations that don't match the code or fall outside the month window are not "excluded" — they were never candidates
- `code_checked` should match the `code` field from the query, not the display name
- `first_match_date` and `last_match_date` derive from the earliest and latest `effectiveDateTime` among matched observations (date portion only)

### Complex Care Escalation
- Risk level derives from the combination of disease severity (uncontrolled metrics, stage), behavioral health comorbidity, medication burden, and social determinants
- Chart concerns must be grounded in actual data from the patient record — do not flag concerns that lack supporting evidence
- Required assessment domains follow directly from chart concerns: each concern implies one or more assessment domains
- Consent strategy codes: always include `avoid_guarantees`, `clear_voluntary_consent`, and `permission_before_sensitive_topics` as baseline; add others based on specific patient circumstances
- Care plan problem set requires at least 3 items and must be traceable to chart concerns
- Disciplines: require at least 2, selected based on the problem areas (e.g., behavioral health → behavioral_health_consultant, polypharmacy → clinical_pharmacist, SDoH → social_worker)
- Follow-up cadence for complex_care is `weekly`
- `avoid_unsupported_guarantees` is always `true`
- Escalation triggers must match the patient's conditions — do not include triggers for conditions the patient doesn't have (e.g., no respiratory triggers for a patient without COPD/asthma)

---

## Evidence ID Handling

- Evidence IDs are the **Observation IDs** that support the clinical decision, not protocol IDs or encounter IDs
- Include the specific observations whose values drove the decision (e.g., the GCS score, the potassium result, the CXR finding)
- Sort evidence_ids lexicographically
- Do not include stale, preliminary, or error-status observations as evidence
- Do not include protocol IDs or encounter IDs as evidence

---

## Common Pitfalls

1. **Using stale data**: Always check observation dates and notes. A "stale" or "old" marker means ignore it for the current decision.
2. **Mixing up codes**: A LOINC code (e.g., `2823-3`) and a local code (e.g., `"K"`) may both measure potassium, but the protocol specifies which code to use. Match exactly.
3. **Ignoring the panel_header flag**: Panel headers have the same code as their members but are structural only. Always check `panel_header` before using an observation.
4. **Including non-matching observations in excluded lists**: Excluded means "matched the query criteria but disqualified." Observations that never matched the code or date window are simply not relevant.
5. **Forgetting lexicographic sort**: The template explicitly requires sorted lists. Unsorted lists are wrong even if the items are correct.
6. **Over-applying contraindications**: Read the full protocol rule including exceptions. QT-risk contraindications may be superseded by ED routing.
7. **Conflating assessment with site of care**: These are separate fields. A patient can have community_acquired_pneumonia (assessment) AND require ed_evaluation (site of care).
8. **Rounding errors in dose calculations**: Follow the protocol's rounding rule exactly — typically "round up to the next 10 mEq," not standard mathematical rounding.
9. **Wrong timezone for follow-up**: Follow-up times use the encounter's local timezone, not UTC. The offset matters.
10. **Including protocol IDs as evidence**: Evidence IDs should be observation IDs, not protocol identifiers.
