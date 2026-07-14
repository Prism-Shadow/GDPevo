---
name: clinic-protocol-decision-support
description: Use for ClinicProtocol API tasks that require deriving structured JSON clinical protocol decisions from synthetic patient, encounter, observation, medication, and care-management records, including head injury triage, acute respiratory assessment, potassium repletion, FHIR lab retrieval, and complex-care escalation.
---

# ClinicProtocol Decision Support SOP

These tasks are synthetic protocol-bound exercises, not medical advice. Return exactly one JSON object matching the prompt's `answer_template.json`; do not add prose, comments, or extra keys.

## API Workflow

1. Read the prompt and answer template first. Copy the required key names, enum spellings, booleans, date formats, and list ordering rules exactly.
2. Replace `<TASK_ENV_BASE_URL>` with the base URL from `environment_access.md`.
3. Fetch protocol cards before deciding:
   - `GET /api/protocols` for the protocol list and available ids.
   - `GET /api/protocols/{protocol_id}` for local rules and controlled outputs.
4. Fetch only records tied to the prompt's stable ids:
   - Patient lookup: `/api/patients?identifier=<identifier>` if the prompt gives an identifier-like value, or `/api/patients/{patient_id}` for a known patient id.
   - Encounter task: `/api/encounters?patient_id=<patient_id>&encounter_id=<encounter_id>`.
   - Observation task: `/api/observations?patient_id=<patient_id>&code=<code>&status=<status>&category=<category>&date_from=<YYYY-MM-DD>&date_to=<YYYY-MM-DD>`.
   - Medication/allergy task: `/api/medication_requests?patient_id=<patient_id>&status=active` plus the patient's `allergies` and `medication_summary`.
   - Care-management task: `/api/care_cases?case_id=<case_id>` then `/api/patients/{linked_patient_id}`.
5. Use filters to narrow results, but query broadly enough to populate explicit exclusion fields such as `ignored_observation_ids` or `excluded_observation_ids`.

## Output Conventions

- `primary_protocol` is the exact protocol id, such as `HEAD_INJURY_2026`.
- `patient_id`, `case_id`, `encounter_id`, observation `id`, medication request `id`, and care case `case_id` must be copied exactly. For encounter-based templates with a `case_id` field and no separate case resource, use the encounter id.
- Evidence ids are stable API identifiers for records actually used to justify the answer. Include the protocol id when the protocol rule itself is part of the cited support; include patient, encounter, observation, medication request, or care-case ids only when that resource materially supports a selected field. Do not include names, free-text snippets, display strings, or invented ids.
- Sort all fields marked `sort_lexicographic` using simple lexicographic string order. Sort evidence and exclusion id lists unless the template explicitly requests chronological order.
- Dates:
  - Preserve full ISO-8601 timestamps where requested.
  - For `YYYY-MM-DD` fields, strip the date from `effectiveDateTime` after applying the record's timestamp.
  - Month windows include every instant from the first day 00:00:00 through the last day 23:59:59.
- Empty lists are valid when no enum item is supported. Do not add uncertain findings just to avoid an empty list.

## Shared Fact Rules

- Current encounter facts outrank stale problem-list conflicts. Ignore inactive problems unless the task asks for history.
- Use active allergies and active/current medications for contraindications. Cancelled medication requests do not count as active treatment, but their ids can be evidence for why an option was rejected if the task asks.
- For observations, match exact `patient_id` and exact `code`. Count only `status: final`, non-panel laboratory observations unless the prompt says otherwise. Exclude `preliminary`, `cancelled`, `entered-in-error`, panel headers, wrong codes, wrong patients, and outside-window observations.
- When choosing "latest" observations, use `effectiveDateTime`, not API result order. Do not let a newer entered-in-error or preliminary result override the latest final valid result.

## Protocol Rules

### Head Injury: `HEAD_INJURY_2026`

- Red flags route to `urgent_ed`: repeated vomiting, worsening headache, seizure, focal weakness, slurred speech, increasing drowsiness, confusion, amnesia over 30 minutes, anticoagulant use, abnormal gait/coordination, or deteriorating mental status.
- `home_observation` requires no red flags, normal neurologic exam, and reliable adult observation. Low-risk symptoms needing review but no urgent red flag route to `same_day_clinic`.
- CT recommendation follows route: `urgent` for `urgent_ed`, `consider` for same-day clinic with persistent symptoms or unreliable observation, otherwise `not_required`.
- Disposition follows route: `send_to_ed_now`, `same_day_clinic_followup`, or `home_with_observation`.
- Activity restrictions: no same-day return to play after a head injury; no sports/high-risk activity until symptom-free and medically cleared. Restrict driving when symptoms or neurologic concerns are present. Use stricter school restriction when ED evaluation is needed; otherwise use reduced 24-48 hours for symptomatic low-risk cases.
- Follow-up timing: 24 hours for urgent/red-flag cases, 48-72 hours for same-day clinic, 72 hours for home observation.
- Common contraindicated actions: `same_day_return_to_play`; `unsupervised_home_observation` when observation is needed; `drive_self_home` when symptomatic, neurologically concerning, or being sent for urgent evaluation.

### Acute Respiratory: `RESP_ACUTE_2026`

- `community_acquired_pneumonia` requires fever/cough plus focal crackles or chest x-ray infiltrate/consolidation.
- `ed_evaluation_required` / `ed_evaluation` is triggered by room-air O2 below 92%, confusion, hypotension, respiratory rate at least 24, or pleuritic chest pain with hypoxia.
- Use `outpatient_treatment` for stable pneumonia with O2 at least 92% and no ED criteria; use `supportive_care` and `no_antibiotic_protocol` for viral URI without pneumonia evidence.
- Severity factor mapping:
  - SpO2 below 92 -> `oxygen_below_92`; 92-94 -> `oxygen_92_to_94`.
  - RR >= 24 -> `tachypnea`.
  - Crackles -> `focal_crackles`; infiltrate/consolidation -> `lobar_consolidation`.
  - Include `pleuritic_pain`, `confusion`, or `hypotension` only when documented.
- Required tests commonly include `pulse_ox_recheck` for abnormal oxygenation, `chest_xray` for suspected pneumonia or infiltrate confirmation, `covid_flu_testing` for acute respiratory syndrome, and `basic_metabolic_panel`/`blood_culture_if_ed` for ED-level illness.
- Antibiotics: choose an outpatient antibiotic only when the site of care remains outpatient. Avoid `penicillin` with active penicillin allergy, `sulfonamide` with sulfa allergy, and `macrolide_qt_risk`/`fluoroquinolone_qt_risk` with active QT-risk medication. `doxycycline` is the usual allergy/QT-compatible outpatient CAP option. If ED evaluation supersedes outpatient prescribing, use `no_antibiotic_protocol` unless the prompt/card explicitly asks for an ED antibiotic.
- Return precautions should reflect the route and symptoms: worsening shortness of breath, hypoxia, chest pain, confusion, hemoptysis, persistent fever after 48-72 hours, and `ed_now` for ED-level criteria.

### Potassium Repletion: `POTASSIUM_REPLETION_2026`

- Select the most recent final serum potassium observation with local code `K`; do not select the follow-up LOINC `2823-3` as the current potassium unless the protocol says so.
- Target potassium is 3.5 mEq/L. If the selected value is below target, `replacement_required` is true.
- Dose formula: `ceil((3.5 - value_meq_l) / 0.1) * 10` mEq, rounded up to the next 10 mEq. Use careful decimal arithmetic so one-decimal lab values produce exact one-decimal deficits, not floating-point artifacts.
- Medication order for required replacement:
  - `drug`: `potassium chloride oral repletion`
  - `ndc`: `40032-917-01`
  - `route`: `oral`
  - `intent`: `order`
- Follow-up lab:
  - `loinc`: `2823-3`
  - `display`: `Serum potassium`
  - `priority`: `routine_next_morning`
  - `occurrenceDateTime`: next calendar day at 08:00 in the local clinical timezone/current-time offset.
- `ignored_observation_ids` should include observations considered but not selected because they are non-final, entered-in-error, wrong code for dose selection, panel headers, or older/stale alternatives. Do not include the selected latest valid observation.
- If no replacement is needed, set `replacement_required:false` and `dose_meq:0`; still satisfy required object fields only if the template does not allow null/omission.

### FHIR Lab Retrieval: `FHIR_LAB_RETRIEVAL_2026`

- Match exact patient id, exact observation code, final status, laboratory category, non-panel resource, and requested month/date window.
- `query.resourceType` and `resource_type` are usually `Observation`; `query.code` and `code_checked` are the exact code used.
- `matched_observation_ids` are the valid matched Observation ids sorted lexicographically; `matched_count` is their count; `has_matching_lab` is `true` iff count > 0.
- `first_match_date` and `last_match_date` are chronological date bounds of matched records, not lexicographic id bounds.
- `excluded_observation_ids` should capture near misses relevant to the query: same patient/code but outside the month, non-final status, panel header, wrong category, wrong code in the target window, or other explicitly noted exclusions. Keep the list sorted.

### Complex Care: `COMPLEX_CARE_2026`

- `complex_care` program applies when registry risk score is at least 0.75, or when recent high-acuity admission combines with uncontrolled chronic disease. Otherwise choose routine or not eligible based on the card/template.
- Chart concerns must be grounded in case/patient data:
  - Diabetes metrics/refill gaps -> `uncontrolled_diabetes`, `diabetes_medication_access`.
  - CKD stage 4 or missed nephrology -> `ckd_stage_4`, `missed_nephrology_followup`, `kidney_followup`, `nephrology_followup`.
  - Heart-failure admission -> `heart_failure_recent_admission`, `heart_failure_self_monitoring`, `heart_failure_symptoms`.
  - COPD/inhaler/pulmonary rehab cues -> COPD/inhaler/pulmonary rehab enums.
  - Medication burden/refill gaps -> `polypharmacy`, `medication_costs`, `clinical_pharmacist`.
  - SDoH flags -> food, housing, utility, transportation assessment and care-plan enums as applicable.
  - Behavioral-health history -> behavioral-health concern/domain/discipline and behavioral escalation trigger only when documented.
- Initial refusal is not final when `member_persona` indicates initial refusal. Use consent strategies such as `reflect_first_refusal`, `clear_voluntary_consent`, `bounded_process_help`, `permission_before_sensitive_topics`, and condition-specific plain-language scheduling. Include `avoid_guarantees` when benefits, transportation, cost, housing, utilities, dialysis slots, or assistance approvals are uncertain.
- Complex-care plans require at least three problem areas, at least two disciplines, `weekly` follow-up, and escalation triggers spanning clinical risk plus behavioral or SDoH risk when indicated.
- `avoid_unsupported_guarantees` should be true whenever the plan discusses assistance, costs, rides, placement, utilities, scheduling flexibility, or approvals that cannot be guaranteed.

## JSON Pitfalls

- Never output enum labels not present in the template, even if clinically natural.
- Do not include stale/inactive conflict facts as positive findings.
- Do not count a panel header as a lab result.
- Do not let `date_to=YYYY-MM-DD` accidentally exclude late-night records on that day.
- Do not confuse local potassium code `K` for current-dose selection with follow-up LOINC `2823-3`.
- Do not overinclude contraindications: active allergy/medication risk must support each contraindicated class.
- Do not omit required keys when a decision is negative; use `false`, `0`, or `[]` when appropriate and allowed by the template.
- Validate the final JSON for parseability, exact key spelling, exact enum spelling, sorted lists, and no trailing commentary.
