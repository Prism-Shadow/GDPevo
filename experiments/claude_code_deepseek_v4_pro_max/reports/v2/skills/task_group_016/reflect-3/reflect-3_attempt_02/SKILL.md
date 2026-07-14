# ClinicProtocol Decision-Support Skill

## Overview

This skill covers protocol-bound clinical decision-support tasks served through a ClinicProtocol HTTP API. Each task provides a patient or case identifier, references a primary protocol, and requires a structured JSON answer matching a provided template. All data — patients, encounters, observations, and protocol cards — is accessible through REST endpoints. The decision logic lives in the protocol's `local_rules` array, not in external guidelines.

---

## API Discovery

The environment provides a single base URL. Use these endpoints to gather data:

| Endpoint | Query Parameters | Notes |
|---|---|---|
| `GET /api/protocols` | none (returns all) | Protocol cards contain `protocol_id`, `local_rules`, `outputs`, `title`, `version`, `effective` date |
| `GET /api/patients` | `?patient_id=` | Returns patient list; filter client-side by `patient_id` |
| `GET /api/encounters` | `?encounter_id=` or `?patient_id=` | Encounter facts live under `facts`; includes `kind`, `status`, `start`, `timezone`, `reason`, `clinician` |
| `GET /api/observations` | `?patient_id=` | Returns all observations for that patient |

There is no separate case endpoint for care-management tasks — the case data is the patient record plus their linked observations.

**Query pattern**: The API supports only exact-match query parameters. Fetch the full collection when you need to scan broadly, or use a patient/encounter ID filter for targeted retrieval.

---

## Protocol Interpretation Workflow

1. **Identify the protocol** from the task prompt and answer template (the `primary_protocol` field is always a single enum value).
2. **Read every `local_rules` entry** in that protocol. These are the decision rules — treat each sentence as a branching condition.
3. **Cross-reference with encounter facts and observations**. Apply the rules strictly: if the rule says "X when Y", only trigger X when Y is explicitly present in the data.
4. **Check for override clauses**. Rules often contain exceptions like "unless ED route supersedes outpatient selection" or "when present" qualifiers on SDoH flags. Do not apply a sub-rule whose precondition is not met.

### Protocol Rule Patterns

- **Route/diagnosis rules**: Map clinical findings to risk routes or assessments. Handle conjunctive (AND) and disjunctive (OR) conditions explicitly.
- **Medication rules**: Allergy and drug-interaction rules constrain antibiotic/medication choices. A QT-risk medication contraindicates macrolide and fluoroquinolone classes unless an ED-route override applies.
- **Follow-up rules**: Specify timing in hours or a calendar-day+clock-time formula. Pay attention to the timezone of the encounter, not UTC.
- **Exclusion rules**: Define what observations to ignore (status ≠ final, panel headers, wrong code, different patient).

---

## Observation Data Handling

### Filtering Rules

When selecting observations for a protocol decision:

1. **Status**: Only `"final"` observations count. Exclude `"preliminary"`, `"cancelled"`, `"entered-in-error"`.
2. **Panel headers**: Observations with `"panel_header": true` are never clinical results — always exclude them.
3. **Code matching**: Match by the exact `code` field. A protocol that says "code K" means observations with `"code": "K"`, not LOINC `2823-3` even if both represent serum potassium.
4. **Patient matching**: Only observations whose `patient_id` matches the target patient. Ignore records for linked-but-different patients (e.g., `PAT-L-T01` vs `PAT-L-T001`).
5. **Temporal ordering**: When multiple final observations match, use the most recent by `effectiveDateTime`. Older values are not used but should be recorded in `ignored_observation_ids` (or `excluded_observation_ids` for retrieval tasks).
6. **Date windows**: Month windows span day 1 at 00:00:00 through the last day at 23:59:59 in the observation's local timezone. An observation on the last day at 23:30 is inside; one at 23:59 on the day before is outside.

### Stale / Conflict Annotations

Encounters and observations may carry `stale_conflict` or `notes` fields marking values as inactive, overridden, or from outside sources. When the current encounter or a more recent observation contradicts a stale value, use the current one. The stale annotation explains why an older value should not override a newer finding.

---

## Evidence ID Conventions

- **evidence_ids**: List the observation IDs that directly support the clinical decision. These are the observations whose values drove the protocol rule matching. Use the `id` field from the observation resource. Sort lexicographically.
- **ignored_observation_ids** (potassium/medication tasks): List every observation the protocol considered but rejected — wrong status, wrong code, older than the selected one, entered-in-error. Sort lexicographically.
- **excluded_observation_ids** (FHIR retrieval tasks): List every observation with the same code and patient that was excluded for any reason — wrong status, panel header, outside the date window. Observations with different codes (not matching the query code) are not "excluded", they are simply irrelevant to the query and should not appear here.
- **matched_observation_ids**: Only observations that pass all filters (correct patient, correct code, correct date window, status=final, not panel header). Sort lexicographically.

---

## Answer Construction

### General Rules

1. **Use the answer template** from `input/payloads/answer_template.json` as the authoritative schema. Every `required_top_level_key` must be present. Every field type, enum constraint, and ordering rule must be satisfied.
2. **String lists**: Sort lexicographically unless the template explicitly says otherwise (e.g., chronological ordering). This applies to `red_flags_present`, `contraindicated_actions`, `evidence_ids`, `severity_factors`, `required_tests`, `return_precautions`, `chart_concerns`, `consent_strategy_codes`, `care_plan_problem_set`, `disciplines`, `escalation_triggers`, and any other string array.
3. **Enums**: Use exactly the string values from the template's `allowed` arrays. Do not paraphrase, abbreviate, or invent values.
4. **ISO-8601 timestamps**: Include the timezone offset (e.g., `-05:00`). Derive from the encounter or observation timezone, not UTC.
5. **Numeric precision**: Match the template's specified precision. Potassium values use 1 decimal place (`3.2`, not `3.20`). Integers (counts, doses, hours) use no decimal.
6. **Booleans**: Use JSON `true`/`false`, not strings.

### Task-Specific Patterns

**Head-injury triage**:
- `case_id` = the encounter ID (e.g., `ENC-H-T001`)
- `risk_level` maps to the protocol route: `urgent_ed`, `same_day_clinic`, or `home_observation`
- `disposition` maps: `urgent_ed` → `send_to_ed_now`, `same_day_clinic` → `same_day_clinic_followup`, `home_observation` → `home_with_observation`
- `ct_recommendation`: `urgent` for urgent_ed, `consider` for same_day_clinic with persistent symptoms or unreliable observation, `not_required` for home_observation
- `follow_up_hours`: 24 for urgent/red-flag, 48–72 for same-day clinic, 72 for home observation
- Red flags: Only include flags directly evidenced in encounter facts. "Headache" alone does not equal "worsening_headache" — the encounter must document worsening.
- `activity_plan`: For ED-bound patients, use the most restrictive options (`no_school_until_evaluated`, `no_sports_until_cleared`, `no_driving_until_symptom_free_cleared`). For home observation, use less restrictive options.
- `contraindicated_actions`: Include all that apply — typically all three for ED cases, fewer for lower-acuity routes.

**Respiratory assessment**:
- `primary_assessment` is the clinical diagnosis (e.g., `community_acquired_pneumonia`), not the disposition. The `ed_evaluation_required` assessment value is distinct from the `site_of_care` value `ed_evaluation`.
- `site_of_care`: `ed_evaluation` when any ED criterion is met (O2 < 92%, hypotension, confusion, RR ≥ 24, pleuritic pain + hypoxia). `outpatient_treatment` when stable with O2 ≥ 92% and no ED criteria.
- `severity_factors`: Include every finding that matches an enum value. O2 of 90% matches `oxygen_below_92` (not `oxygen_92_to_94`). RR 26 matches `tachypnea`. CXR infiltrate matches `lobar_consolidation`.
- `antibiotic_plan`: When the patient is routed to ED, the answer is `no_antibiotic_protocol` — ED manages antibiotic selection. For outpatient CAP, select the antibiotic that avoids documented allergies and QT-risk interactions.
- `contraindicated_antibiotic_classes`: A QT-risk medication (e.g., sertraline) contraindicates both `fluoroquinolone_qt_risk` AND `macrolide_qt_risk`. Document allergies contraindicate their respective classes.
- `required_tests`: `blood_culture_if_ed` only when routed to ED. `chest_xray` and `pulse_ox_recheck` are baseline.

**Potassium replacement**:
- `latest_potassium`: The most recent `"final"` observation with `"code": "K"`. Do not use LOINC-coded (`2823-3`) observations even if they also represent potassium.
- `dose_meq`: Calculate as `10 × (deficit_in_0_1_mEq_L_units)`, then round UP to the next multiple of 10. For a value of 3.2 with target 3.5: deficit = 0.3, units = 3, dose = 30, rounded up = 30.
- `follow_up_lab.occurrenceDateTime`: Next calendar day at 08:00 in the encounter/local timezone. If current time is 2026-07-06T09:00:00-05:00, follow-up is 2026-07-07T08:00:00-05:00.
- `ignored_observation_ids`: Include all observations for this patient that were reviewed but not selected — wrong status, wrong code, or older timestamp. Sort lexicographically.
- `medication_order`: Every field is fully determined by the protocol (drug, NDC, route, intent are all single-allowed-value enums once the protocol is identified).

**FHIR lab retrieval**:
- `query.code`: The LOINC or local code being searched for, as a string.
- `query.month`: Format `YYYY-MM`.
- `has_matching_lab`: `true` if `matched_count > 0`.
- `first_match_date` / `last_match_date`: Format `YYYY-MM-DD`. Derived from the earliest and latest `effectiveDateTime` among matched observations.
- `code_checked`: Same as `query.code`.
- `excluded_observation_ids`: Include ALL observations with the matching code and patient that were filtered out for any reason (status, panel_header, outside date window). Do NOT include observations with different codes — those were never candidates.

**Complex care** (limited training data — apply with caution):
- The case data is the patient record plus observations. There is no separate case endpoint.
- `risk_level` and `program_type` depend on meeting protocol criteria: risk score threshold OR recent high-acuity admission + uncontrolled chronic disease.
- `chart_concerns`: Only include items directly evidenced by observation data or encounter facts. Do not infer SDoH flags or medication burden without explicit documentation.
- `required_assessment_domains`: Must be grounded in documented conditions, not speculative.
- Protocol mandates: ≥3 `care_plan_problem_set` items, ≥2 `disciplines`, `"weekly"` follow-up for complex care.
- `avoid_unsupported_guarantees`: Always `true` — the protocol explicitly forbids guaranteeing costs, rides, dialysis slots, or assistance approval.

---

## Common Pitfalls

1. **Using non-final observations**: Always check `status`. Preliminary, cancelled, and entered-in-error observations are never valid for clinical decisions.
2. **Panel headers mistaken for results**: Check `panel_header`. These group observations but carry no clinical value.
3. **Wrong code matching**: A protocol specifying code `"K"` does not match LOINC `"2823-3"`, even if both describe serum potassium. Match exact codes.
4. **Missing excluded observations**: For retrieval tasks, observations outside the date window but with the matching code and patient still belong in `excluded_observation_ids`.
5. **Confusing primary_assessment with site_of_care**: The assessment is the clinical diagnosis; site_of_care is the recommended care setting.
6. **Wrong antibiotic when QT-risk meds are active**: Both macrolides and fluoroquinolones are contraindicated. For ED-routed patients, use `no_antibiotic_protocol`.
7. **Dose rounding**: Round UP to the next 10 mEq, not to the nearest. A calculated dose of 30 stays 30; a calculated dose of 25 rounds to 30.
8. **Timezone handling**: Follow-up times use the encounter's local timezone, not UTC. The next calendar day at 08:00 means 08:00 in that timezone.
9. **Over-inferring undocumented concerns**: Do not add chart concerns, SDoH flags, or assessment domains that are not directly supported by the patient's observation or encounter data.
10. **Wrong case_id**: For encounter-based tasks, `case_id` equals the `encounter_id`. For case-management tasks, `case_id` is the explicitly provided case identifier.
11. **Boolean vs string**: `replacement_required`, `has_matching_lab`, and `avoid_unsupported_guarantees` are JSON booleans, not the strings `"true"`/`"false"`.
12. **Lexicographic sort on IDs**: Observation IDs like `OBS-K-T001-ERR` and `OBS-K-T001-FINAL` sort by character, so `ERR` < `FINAL` < `LOINC` < `OLD-FINAL` < `PRELIM`.

---

## Workflow Summary

1. Read the prompt to identify the task type, patient/case ID, encounter ID (if any), and the relevant protocol.
2. Fetch the protocol from `/api/protocols` and read all `local_rules`.
3. Fetch patient data from `/api/patients?patient_id=...`.
4. Fetch encounter data from `/api/encounters?encounter_id=...` (if encounter-based).
5. Fetch observations from `/api/observations?patient_id=...`.
6. Apply protocol rules to the clinical facts step by step.
7. Populate the answer template, ensuring every field type, enum constraint, sort order, and format rule is satisfied.
8. Submit the completed JSON answer.
