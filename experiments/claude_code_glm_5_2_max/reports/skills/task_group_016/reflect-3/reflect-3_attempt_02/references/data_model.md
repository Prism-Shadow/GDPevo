# Runtime Data Model

The clinic runtime is FHIR-like. The runtime access (base URL, endpoints, credentials) is
provided **separately for each run** — read that file to learn how to call it. What is stable
across runs is the *shape* of the data, described here so you know what to extract.

## Case record (fetch by target case id)

A single case record bundles everything you usually need:

- `case`: `{case_id, case_type, patient_id, service_date, status, summary}`
- `patient`: `{patient_id, name, birth_date, age, sex, fhir_id}`
- `findings`: list of `{finding_key, finding_value, source_id}` — the curated clinical facts
  for this case. `source_id` is the evidence identifier to cite. Common keys include
  `current_time`, `chief_complaint`, `oxygen_room_air_range`, `mechanism`, `loss_of_consciousness`,
  `vomiting`, `headache`, `window_start`, `window_end`, `target_code`, `registry_risk_score`,
  `dialysis_schedule`, `recent_admission`, `hba1c`, `phosphorus`, `blood_pressure`,
  `active_medications`, `sdoh_barriers`, `dialysis_fatigue`, `outreach_posture`,
  `allergy_constraint`, `renal_contraindication`, etc.
- `observations`: list of FHIR-like Observation resources:
  `{observation_id, patient_id, case_id, code, display, category, value_number, value_text,
  unit, interpretation, status, effective_time, source}`. `status` is one of
  `final`, `preliminary`, `canceled`, `entered-in-error` (treat only `final` as authoritative
  unless a protocol says otherwise). `code` is the LOINC/concept code that the protocol's
  `controlled_codes` map to.
- `imaging`: list of `{imaging_id, case_id, patient_id, study, impression, performed_at, status}`.
- `medications`: list of `{medication_id, patient_id, name, code, dose, route, frequency,
  start_date, end_date, status, source}`. `code` is typically RxNorm-style.
- `allergies`: list of `{id, patient_id, allergen, reaction, status}`. Use `status: "active"`
  only.
- `problems`: list of `{id, patient_id, code, name, onset_date, status}` (ICD-10-coded).
- `sdoh`: list of `{id, patient_id, domain, evidence, severity, source}`. `source` is
  `member-disclosed` vs `care-manager note` — this distinction drives
  `source_provenance.member_disclosure_needed`.
- `care_registry`: nullable; present for care-management cases. Contains
  `{case_id, patient_id, risk_score, chronic_condition_count, medication_count,
  dialysis_schedule, recent_admission_date, program_hint}`.

## Protocol (list available protocols, then fetch the detail for the matching one)

A protocol body carries the authoritative rules:

- `authoritative_statuses`: which observation statuses satisfy gates (almost always `["final"]`).
- `controlled_codes`: maps concept → code (e.g. `serum_potassium: "K"`,
  `chest_xray: "CXR-2V"`, `follow_up_lab: "2823-3"`, `routine_oral_potassium_ndc: "..."`).
- `excluded_statuses`: observation statuses to discard.
- Thresholds: e.g. `ed_escalation` (SpO2/RR/SBP cutoffs + other red flags),
  `urgent_branch` (K cutoff, ECG, dialysis, symptoms), `high_predictive_risk_min`,
  `target_potassium_mmol_l`.
- `routine_dose_rule`: dosing formula and rounding.
- Timing: `outpatient_follow_up_hours`, `follow_up_hours`, `routine_follow_up` ("next morning…").
- Enum sources: `return_precaution_codes`, `urgent_route_triggers`, `mild_tbi_support`,
  `complex_care_supporting_triggers`, `pharmacist_referral_triggers`,
  `social_work_referral` (domains + minimum moderate/severe count).
- `ordering`: how to sort matched/excluded observations.

## Distractors

Global list endpoints and other cases contain **synthetic distractor** records
(patient ids like `PAT-D2xxx`, case ids like `CASE-D3xxx`, "mixed source quality"). They exist
to test filtering. Always scope retrieval to the target `case_id` / `patient_id`; do not let
distractor records influence the answer.
