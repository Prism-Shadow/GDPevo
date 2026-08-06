# Protocol playbook & case-family notes

Orientation only. **Always re-read the live protocol** via
`GET /api/protocols/{protocol_id}` at runtime — thresholds, codes, and statuses
can change between versions, and the live body wins over anything below. None of
the numbers here are answers; they are protocol constants retrievable from the
environment.

## Case type → protocol

| `case.case_type`        | protocol_id        | title                                      |
|-------------------------|--------------------|--------------------------------------------|
| `acute_respiratory`     | `RESP-CAP-2026`    | Adult Respiratory Infection & CAP          |
| `pediatric_head_injury` | `PEDS-HEAD-2026`   | Pediatric Head Injury Clinic Triage        |
| `potassium_repletion`   | `K-REPLETION-2026` | Potassium Replacement and Escalation       |
| `care_management`       | `CM-HIGH-RISK-2026`| High-Risk Care-Management Routing          |
| `observation_window`    | `OBS-WINDOW-2026`  | Observation Window Interpretation          |

## Data model reminders

- `GET /api/cases/{id}` bundle keys: `case, patient, findings[], observations[],
  imaging[], medications[], allergies[], problems[], care_registry, sdoh[]`.
- `findings[]`: `{finding_key, finding_value, source_id}`. Use `finding_value`
  for the clinical fact and `source_id` as an `evidence_ids` candidate.
- `observations[]`: `{observation_id, code, display, category, status,
  interpretation, value_number, value_text, unit, effective_time, patient_id,
  case_id}`. **Only `status == "final"` counts.**
- Allergies/problems/medications carry `status` (`active`/`inactive`) — filter.

## RESP-CAP-2026 (adult respiratory / CAP)

- `authoritative_statuses: [final]`; `outpatient_follow_up_hours: 48`.
- `controlled_codes`: chest_xray `CXR-2V`, respiratory_viral_pcr
  `SARS_FLU_RSV_PCR`, pulse_ox_recheck `PULSE_OX_RECHECK`, basic_cbc `CBC_BASIC`,
  oxygen_saturation `59408-5`, respiratory_rate `9279-1`, temperature `8310-5`.
- `ed_escalation` when: SpO2 room-air `< 90`, respiratory_rate `>= 30`,
  systolic_bp `< 90`, or an `other_red_flags` item (confusion, sepsis_concern,
  immunocompromise, multilobar_disease). Otherwise outpatient with close
  follow-up.
- `allergy_rule`: use active allergies, avoid the implicated medication classes;
  choose an antibiotic strategy consistent with them.
- Derivation notes: red flags come from findings/observations (e.g. borderline
  hypoxemia range, pleuritic chest pain) mapped to the template enum; recommended
  tests are the controlled codes actually indicated/performed; `safety_checks`
  assert you did not claim a normal CXR / clear lungs when imaging is abnormal and
  did not choose penicillin/sulfa against active allergies.

## PEDS-HEAD-2026 (pediatric head injury)

- `authoritative_statuses: [final]`; `follow_up_hours: [24, 48]`.
- `urgent_route_triggers`: repeated_vomiting, worsening_severe_headache, seizure,
  basilar_skull_signs, focal_neurologic_deficit, gcs_below_15,
  prolonged_loss_of_consciousness → ED / CT consideration when present.
- `mild_tbi_support`: brief confusion/symptoms, normal/near-normal neuro exam, no
  urgent trigger → home observation with follow-up, typically no immediate CT.
- `restrictions`: cognitive/physical rest + graded return-to-learn; no same-day
  return to play, graded return after clearance; no driving while symptomatic or
  on sedating meds. Map these to the template's restriction enums.
- Derivation notes: `red_flags` = triggers/symptoms present in findings;
  `absent_red_flags` = urgent-trigger enums the record explicitly documents as
  absent/normal (e.g. LOC "absent", vomiting "absent", GCS 15, no focal
  weakness); `safety_checks` attest no false LOC / vomiting / photophobia.

## K-REPLETION-2026 (potassium repletion)

- `authoritative_statuses: [final]`; `target_potassium_mmol_l: 3.5`.
- `controlled_codes`: serum_potassium `K`, egfr `33914-3`, follow_up_lab
  `2823-3`, ecg_summary `ECG-SUMMARY`, routine_oral_potassium_ndc
  `40032-917-01`.
- `routine_dose_rule` (applies only when the urgent branch is false):
  `10 mEq per 0.1 mmol/L below target`, rounded to the nearest `10 mEq`.
- `urgent_branch` triggers: potassium `< 3.0`, dialysis-dependent ESRD, ECG
  abnormality, severe renal contraindication, or symptoms (palpitations, syncope,
  weakness with arrhythmia concern) → escalation rather than routine oral.
- `routine_follow_up`: next-morning final serum potassium (LOINC `2823-3`).
- Derivation notes: pick the **latest eligible `final` serum-K** observation for
  `latest_potassium`; `replacement_required` true when below target; compute
  `oral_dose_mEq` from the dose rule only on the routine branch (else `null`);
  populate `medication_order` from controlled codes when recommending, else the
  `not_recommended`/`defer` status with nulls; screen contraditions
  (dialysis, arrhythmia symptoms, eGFR from `33914-3`).

## CM-HIGH-RISK-2026 (care-management routing)

- `high_predictive_risk_min: 0.75` → high risk / complex_care_management.
- `complex_care_supporting_triggers`: chronic_condition_count ≥ 3, recent
  admission, dialysis/advanced CKD, heart failure, uncontrolled diabetes.
- `pharmacist_referral_triggers`: active_medication_count ≥ 10, insulin safety,
  high-risk diuretic/electrolyte regimen.
- `social_work_referral`: ≥ 2 moderate/severe domains among transportation,
  financial, food, housing.
- `care_plan_minima`: weekly contact initially, medication reconciliation,
  barrier resolution, clear escalation conditions.
- `outreach`: permission-based when the member is reluctant/refusing.
- Derivation notes: numeric anchors come from `care_registry` + observations
  (risk_score, hba1c, phosphorus, blood_pressure, active_medication_count);
  `source_provenance` splits **chart facts** (verifiable in the record) from
  **member-disclosed** barriers (from sdoh/call findings). Priority problems,
  referrals, and escalation conditions are the enum codes supported by the
  registry, problems, and disclosed barriers.

## OBS-WINDOW-2026 (observation window retrieval)

- `status_rule`: only `status == "final"` satisfies gates.
- `excluded_statuses`: preliminary, entered-in-error, canceled.
- `controlled_codes`: serum_potassium `K`, respiratory_viral_pcr
  `SARS_FLU_RSV_PCR`, chest_xray `CXR-2V`.
- `same_code_selection`: choose the latest `final` `effective_time` within the
  target window.
- `ordering`: `effective_time` ascending, then `observation_id` ascending.
- Derivation notes: `matched_observation_ids` = final + correct target code +
  inside `[from, to)`, sorted per ordering. `excluded_observation_ids` = relevant
  distractors that fail on date, code, or status (group same-target-code
  exclusions before other-code ones, each ordered by the ordering key).
  `latest_final` = the last matched; `lab_found` true iff ≥1 match; set
  `protocol_gate`/`repeat_lab` from the latest final value vs. the protocol.
