---
name: clinical-protocol-decision-support
description: Solve synthetic ClinicProtocol clinical decision-support tasks using the remote ClinicProtocol API and the task's answer_template.json. Use when a prompt asks Codex to review patient, encounter, observation, medication, or care-management records and return strict JSON for protocol-bound triage, respiratory assessment, potassium repletion, FHIR lab retrieval, or complex-care escalation.
---

# Clinical Protocol Decision Support SOP

## First Pass

1. Read the task prompt and `input/payloads/answer_template.json` before querying records. The template is the contract: output exactly one JSON object, include only the required top-level keys, use allowed enum strings exactly, and sort every list whose template says `sort_lexicographic`.
2. Read `environment_access.md` in the task workspace and replace `<TASK_ENV_BASE_URL>` with `GDPEVO_ENV_BASE_URL`. Do not use real medical judgment outside the local protocol cards.
3. Extract the patient id, encounter id, care case id, code, date window, and synthetic current time from the prompt. Prefer prompt time over wall-clock time; otherwise check `/api/status` for `synthetic_clock` and timezone.
4. Fetch the relevant protocol card with `/api/protocols` or `/api/protocols/{protocol_id}` and treat `local_rules` as authoritative.
5. Fetch only the records needed to fill the template, then map facts to template fields and stable API ids.

## API Habits

Useful GET patterns:

```bash
BASE="$(awk -F= '/GDPEVO_ENV_BASE_URL/ {print $2}' environment_access.md)"
curl -sS "$BASE/api/status"
curl -sS "$BASE/api/protocols"
curl -sS "$BASE/api/protocols/HEAD_INJURY_2026"
curl -sS "$BASE/api/patients?identifier=<PATIENT_ID_OR_MRN>"
curl -sS "$BASE/api/patients/<PATIENT_ID>"
curl -sS "$BASE/api/encounters?patient_id=<PATIENT_ID>&encounter_id=<ENCOUNTER_ID>"
curl -sS "$BASE/api/observations?patient_id=<PATIENT_ID>&code=<CODE>&status=final&category=laboratory"
curl -sS "$BASE/api/observations?patient_id=<PATIENT_ID>&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD"
curl -sS "$BASE/api/medication_requests?patient_id=<PATIENT_ID>&status=active"
curl -sS "$BASE/api/care_cases?case_id=<CASE_ID>"
```

Use `/patients/<patient_id>` for rich demographics, active problems, allergies, and medication summaries. Use encounters for current visit facts and observations for objective evidence. Pull unfiltered observations when the answer asks for ignored or excluded ids, because preliminary, entered-in-error, panel-header, wrong-code, or stale records often need to be named as exclusions.

## Output Conventions

- `case_id`: the encounter id for encounter-based tasks or the care-management case id for care-management tasks.
- `patient_id`: exact API patient id, not MRN or name.
- `primary_protocol`: exact `protocol_id` from the matching protocol card.
- `current_time`: synthetic prompt/API time, preserving timezone offset.
- Clinical enum fields: choose only from the template. Do not invent synonyms.
- List fields: sort lexicographically by string unless the template explicitly says otherwise.
- Date fields: preserve ISO timestamps for `effectiveDateTime` and `occurrenceDateTime`; use `YYYY-MM-DD` only when the template requests a date.
- Evidence ids: use stable API ids (`encounter_id`, observation `id`, medication request `id`, care `case_id`) that directly support the selected decision. Keep the list minimal and sorted. If a fact comes from encounter narrative, the encounter id is valid evidence; if it comes from labs/imaging/vitals, include the decisive observation ids. Do not include excluded or stale records in `evidence_ids`; put them in the template's excluded/ignored field when requested.
- Required objects: preserve the template shape. If no action is needed, do not omit required keys; use only representations allowed by the template or explicitly requested by the prompt.

## Protocol Rules

### Head Injury: `HEAD_INJURY_2026`

Route to `urgent_ed` if the current encounter includes any red flag: repeated vomiting, worsening headache, seizure, focal weakness, slurred speech, increasing drowsiness, confusion, amnesia over 30 minutes, anticoagulant use, abnormal gait or coordination, or deteriorating mental status. Map concrete chart facts to enum names, such as vomiting count >= 2 to `repeated_vomiting` and hard-to-keep-awake/drowsiness to `increasing_drowsiness`.

Use `home_observation` only when there are no red flags, the neurologic exam is normal, and reliable adult observation is available. Use `same_day_clinic` for symptoms needing clinician review without urgent red flags.

Set CT/disposition from route: urgent route gives `urgent` CT and `send_to_ed_now`; same-day route usually gives `consider` CT and `same_day_clinic_followup`; uncomplicated home observation gives `not_required` CT and `home_with_observation`. Follow-up is 24 hours for urgent or red-flag cases, 72 hours for home observation, and a single integer in the 48-72 hour range for same-day clinic when forced by the template.

Activity restrictions should be conservative for symptomatic or neurologic cases: no sports until cleared, no driving until symptom-free/cleared, and no school until evaluated for urgent cases or reduced 24-48h for lower-risk symptomatic cases. `same_day_return_to_play` is contraindicated for current head injury. Add `unsupervised_home_observation` when observation is unreliable or unsafe, and `drive_self_home` when symptoms, neurologic concerns, or ED routing make self-transport unsafe.

### Respiratory: `RESP_ACUTE_2026`

Assess `community_acquired_pneumonia` when fever/cough is accompanied by focal crackles or chest x-ray infiltrate/consolidation. Use `viral_upper_respiratory_infection` when there is no pneumonia evidence and supportive care is appropriate. Use `copd_asthma_exacerbation` only for an active/current obstructive-airway exacerbation, not an inactive problem-list label.

Choose `ed_evaluation` for oxygen saturation below 92 percent on room air, confusion, hypotension, respiratory rate >= 24, or pleuritic pain with hypoxia. Stable pneumonia without ED criteria is outpatient; viral illness is supportive care.

Severity factors map directly from encounter/vital/imaging facts: `oxygen_below_92`, `oxygen_92_to_94`, `tachypnea`, `focal_crackles`, `lobar_consolidation`, `pleuritic_pain`, `confusion`, `hypotension`. ED pneumonia usually needs `chest_xray`, `pulse_ox_recheck`, `covid_flu_testing`, `basic_metabolic_panel`, and `blood_culture_if_ed`.

Allergy/QT exclusions matter. Active penicillin allergy contraindicates `penicillin`; sulfonamide allergy contraindicates `sulfonamide`; active QT-risk medication contraindicates `macrolide_qt_risk` and `fluoroquinolone_qt_risk`. If ED route supersedes outpatient prescribing, use `no_antibiotic_protocol` and `ed_now` precautions rather than forcing an outpatient antibiotic.

### Potassium Repletion: `POTASSIUM_REPLETION_2026`

Use the most recent final serum potassium Observation with local code `K` for dose selection. Exclude preliminary, entered-in-error, cancelled, panel-header, wrong-code, and older final potassium-like observations from the selected result. If the answer asks for ignored ids, include relevant near-miss potassium observations sorted lexicographically.

Target potassium is 3.5 mEq/L. If the selected value is below target, replacement is required with oral potassium chloride, NDC `40032-917-01`, route `oral`, intent `order`. Dose is 10 mEq per 0.1 mEq/L below target, rounded up to the next 10 mEq. Follow-up lab is serum potassium LOINC `2823-3`, display `Serum potassium`, priority `routine_next_morning`, scheduled for the next calendar day at 08:00 in the local clinical timezone.

### FHIR Lab Retrieval: `FHIR_LAB_RETRIEVAL_2026`

Match Observations by exact patient id, exact code, `status=final`, not a panel header, and `effectiveDateTime` within the requested window. Month windows include the first day at 00:00:00 through the last day at 23:59:59 in the record timezone. Return matched observation ids sorted lexicographically, `matched_count`, and first/last matched dates chronologically.

For exclusions, include same-patient same-code near misses that fail the month/status/panel criteria. Do not list unrelated codes just because they occurred in the same month.

### Complex Care: `COMPLEX_CARE_2026`

Use `/api/care_cases?case_id=...` first, then the linked patient, observations, medication requests, and active problem list. `complex_care` applies when registry risk score is at least 0.75 or there is recent high-acuity admission plus uncontrolled chronic disease. High-risk complex care normally has `weekly` follow-up, at least three problem areas, and at least two disciplines.

Ground `chart_concerns` in explicit case/referral cues, active disease metrics, recent admissions, medication burden, and SDoH flags. Do not promote stale or incidental problems unless the case narrative makes them relevant.

Map care-plan and assessment domains from concrete barriers:

- uncontrolled diabetes or insulin access: diabetes medication access, clinical pharmacist, glucose escalation trigger.
- CKD or missed nephrology: kidney follow-up and nephrology assessment.
- heart failure admission: heart failure self-monitoring and dyspnea/weight-gain/ED trigger.
- food, utility, housing, or transportation flags: social worker, resource problems, transportation follow-up, and SDoH escalation triggers.
- behavioral-health history or refusal concerns: permission-based consent, behavioral-health consultant when safety/mood escalation is indicated.
- COPD/inhaler/pulmonary rehab cues: respiratory therapist, inhaler affordability, pulmonary rehab transport, rescue-inhaler or SpO2 trigger.

For an `initially_refuses` persona, refusal is not final. Use consent strategies such as `reflect_first_refusal`, `clear_voluntary_consent`, `permission_before_sensitive_topics`, `bounded_process_help`, and plain-language scheduling. Set `avoid_unsupported_guarantees` true when the protocol warns not to guarantee lower costs, rides, dialysis-slot flexibility, or assistance approval.

## Common Exclusions And Pitfalls

- Do not use inactive/stale problem-list items to override current encounter facts.
- Do not use preliminary, entered-in-error, cancelled, or panel-header observations as matches.
- Do not use a linked but different patient, MRN, or name when the protocol requires exact patient id.
- Do not confuse local potassium code `K` for selecting the current result with LOINC `2823-3` for the ordered follow-up lab.
- Do not let an old normal vital/lab override a current abnormal result tied to the encounter.
- Do not prescribe a contraindicated antibiotic class when allergies or active QT-risk medication are present.
- Do not include non-template keys, comments, markdown fences, or explanatory text in the final answer.
