---
name: clinic-protocol-decision-support
description: Solve synthetic ClinicProtocol clinical decision-support tasks by querying the remote protocol/patient API, applying local protocol cards, and returning schema-exact JSON for head injury, acute respiratory, potassium repletion, FHIR lab retrieval, and complex-care cases.
---

# ClinicProtocol Decision Support

Use this skill for synthetic protocol-bound clinical decision-support tasks that provide a ClinicProtocol API base URL, target patient/encounter/case identifiers, and an `answer_template.json`.

## Core Workflow

1. Read the prompt and `input/payloads/answer_template.json` first. Treat the template as the output contract: required keys, allowed enum values, list ordering, precision, and date formats all come from it.
2. Replace `<TASK_ENV_BASE_URL>` with the base URL from the task access file. Query the API for the exact target patient, encounter, care case, observations, medication requests, and protocol card.
3. Use current resources tied to the target patient and current encounter/case. Ignore stale, inactive, wrong-code, wrong-month, preliminary, cancelled, entered-in-error, panel-header, and different-patient records unless the template asks to list exclusions.
4. Return exactly one JSON object. Use only template keys and allowed enum strings. Sort every list lexicographically when the template says so.
5. Include stable evidence IDs for the resources that directly support the decision, usually encounter/case IDs and current final observation IDs. Do not include unrelated vitals, inactive problems, cancelled medication requests, or stale observations as evidence.

## API Habits

Useful endpoints:

- `GET /api/protocols` to discover protocol IDs and brief local rules.
- `GET /api/protocols/{protocol_id}` for the active card to apply.
- `GET /api/patients?identifier={patient_id}` can resolve a prompt identifier, but `GET /api/patients/{patient_id}` is needed for full chart details such as allergies, active problems, and medication summary.
- `GET /api/encounters?patient_id={patient_id}&encounter_id={encounter_id}` for visit facts, vitals, symptoms, exam, timezone, and stale-conflict notes.
- `GET /api/observations?patient_id={patient_id}` first when exclusions matter; then narrow with `code`, `status`, `category`, `date_from`, and `date_to` if useful.
- `GET /api/medication_requests?patient_id={patient_id}` for active/cancelled medications, antibiotic conflicts, QT-risk drugs, and medication burden evidence.
- `GET /api/care_cases?case_id={case_id}` or `?patient_id={patient_id}&status={status}` for care-management referrals, risk scores, SDoH flags, and service context.

Query broadly enough to see exclusions. For lab retrieval and potassium tasks, a too-narrow `status=final` query can hide preliminary or entered-in-error records that belong in `excluded_observation_ids` or `ignored_observation_ids`.

## Output Conventions

- `case_id`, `patient_id`: copy the target API identifiers exactly.
- `primary_protocol`: use the protocol ID from the matching local card, not the protocol title.
- Decision enums: pick only strings allowed by the template. Do not invent clinical phrasing.
- Lists: include each qualifying code once and sort lexicographically unless the template explicitly asks for chronology.
- Dates/times: preserve timezone offsets from the task or source resources. For date-only fields, derive `YYYY-MM-DD` from `effectiveDateTime`.
- Numeric values: preserve the template precision, especially potassium `value_meq_l` to one decimal.
- Evidence IDs: use API resource IDs, not display names. Include the smallest set that proves the route/result. Encounter/case IDs support encounter/case fact decisions; final observations support lab/vital/imaging findings. Patient demographics rarely belong in evidence.
- Exclusion/ignored IDs: include resources that were considered but rejected for a protocol reason, such as wrong code, stale date, preliminary status, panel header, entered-in-error, cancelled status, or old final result superseded by a newer final result.

## Protocol Rules

### Head Injury (`HEAD_INJURY_2026`)

- Route `urgent_ed` for current red flags: repeated vomiting, worsening headache, seizure, focal weakness, slurred speech, increasing drowsiness, confusion, amnesia over 30 minutes, anticoagulant use, abnormal gait/coordination, or deteriorating mental status.
- Use `same_day_clinic` for symptoms needing clinician review without urgent red flags.
- Use `home_observation` only when there are no red flags, neuro exam is normal, and reliable adult observation is documented.
- CT is `urgent` for `urgent_ed`, `consider` for same-day clinic with persistent symptoms or unreliable observation, otherwise `not_required`.
- Activity restrictions: no same-day return to play after head injury; no high-risk sports until symptom-free and cleared; no driving when symptoms or neurologic concerns remain.
- Follow-up is typically 24 hours for urgent/red-flag cases, 48-72 hours for same-day clinic, and 72 hours for home observation.
- Common contraindicated actions: driving self home, same-day return to play, and unsupervised home observation when red flags or unreliable observation are present.

### Acute Respiratory (`RESP_ACUTE_2026`)

- `community_acquired_pneumonia` fits fever/cough with focal crackles, infiltrate, or consolidation.
- `ed_evaluation` is required for oxygen saturation below 92% on room air, confusion, hypotension, respiratory rate at least 24, or pleuritic pain with hypoxia.
- `outpatient_treatment` is for stable patients with O2 at least 92% and no ED criteria; `supportive_care` fits viral/non-pneumonia patterns.
- Severity factors usually map directly from current exam, vitals, symptoms, and final imaging observations: focal crackles, lobar consolidation, O2 92-94 or below 92, tachypnea, pleuritic pain, confusion, hypotension.
- Required tests commonly include chest x-ray, pulse-ox recheck, COVID/flu testing, BMP, and blood culture when ED evaluation is selected.
- Antibiotic choices are limited to template enums. Avoid penicillin with active penicillin allergy, sulfonamide with sulfa allergy, and macrolide/fluoroquinolone with active QT-risk medication unless an ED/no-outpatient-antibiotic route supersedes selection.
- `no_antibiotic_protocol` is appropriate when the protocol route requires ED evaluation rather than local outpatient antibiotic selection.

### Potassium Repletion (`POTASSIUM_REPLETION_2026`)

- Select the most recent `final` serum potassium observation using local code `K`; do not use older LOINC-coded potassium results for dose selection if the card specifies code `K`.
- Ignore preliminary, entered-in-error, wrong-code, and older superseded potassium observations.
- Target is 3.5 mEq/L. If latest final value is below target, order oral potassium chloride with NDC `40032-917-01`; otherwise no replacement is required and dose is zero if the template permits.
- Dose rule: 10 mEq for each 0.1 mEq/L below target, rounded up to the next 10 mEq.
- Follow-up lab is serum potassium LOINC `2823-3`, display `Serum potassium`, priority `routine_next_morning`.
- Follow-up occurrence is the next calendar day at 08:00 in the local clinical/encounter timezone, preserving the offset.

### FHIR Lab Retrieval (`FHIR_LAB_RETRIEVAL_2026`)

- Match Observation resources by exact patient ID, exact code, `status = final`, `panel_header = false`, and `effectiveDateTime` inside the requested window.
- Month windows include every instant from the first day at 00:00:00 through the final day at 23:59:59 in the local offset.
- Exclude panel headers, preliminary/cancelled/entered-in-error records, wrong-code observations, records outside the month, and linked but different patients.
- `matched_count` must equal the length of `matched_observation_ids`.
- `has_matching_lab` is true iff `matched_count > 0`.
- `first_match_date` and `last_match_date` are chronological date-only bounds of matched observations, even when IDs are sorted lexicographically.
- `query.resourceType`, `resource_type`, and `code_checked` should mirror the requested Observation/code target.

### Complex Care (`COMPLEX_CARE_2026`)

- `complex_care` applies when registry risk score is at least 0.75 or there is recent high-acuity admission plus uncontrolled chronic disease.
- Risk is usually `high` for high risk score with multiple recent high-acuity admissions, uncontrolled disease metrics, medication burden, and SDoH barriers.
- Chart concerns come from active problems, observations, referral text, recent admissions, medication burden, and SDoH flags. Do not include inactive or unsupported conditions.
- Required assessment domains must be grounded in chart/referral cues or stated barriers, not a generic checklist.
- Initial refusal is not final when the persona indicates it; use consent strategies for voluntary, permission-based, plain-language, bounded process help.
- Always avoid unsupported guarantees about cost reduction, ride availability, dialysis schedule flexibility, or assistance approval.
- Complex-care plans need at least three problem areas, at least two disciplines, weekly follow-up, and escalation triggers covering clinical risk plus behavioral health or SDoH risk when indicated.
- Map team names to template enum codes, e.g. RN/care manager to `care_manager`, pharmacist to `clinical_pharmacist`, social work to `social_worker`, behavioral health to `behavioral_health_consultant`, PCP to `primary_care_provider`, and respiratory therapist to `respiratory_therapist`.

## JSON Pitfalls

- Do not output prose, Markdown, code fences, comments, or extra keys.
- Do not copy old/inactive chart problems into current decisions when the encounter explicitly marks them stale or inactive.
- Do not miss patient allergies and medication-summary conflicts by relying only on encounter data.
- Do not use cancelled medication requests as active treatment, but do consider them if the task asks for contraindicated or excluded items.
- Do not include panel headers as matched labs even if code and month match.
- Do not choose the newest observation unless it also satisfies status/code/category rules.
- Do not use display labels where enum codes are required.
- Do not let `matched_count`, booleans, first/last dates, and ID arrays disagree.
