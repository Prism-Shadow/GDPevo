---
name: clinical_protocol_decision_support
description: Solve synthetic ClinicProtocol API clinical decision-support tasks by retrieving the correct patient records, applying local protocol cards, and returning exact schema-matching JSON.
---

# Clinical Protocol Decision Support SOP

Use this skill for ClinicProtocol tasks that ask for protocol-bound clinical decisions, lab retrieval, medication repletion, respiratory triage, head-injury triage, or complex-care escalation. These are synthetic tasks, not real medical advice.

## Core Workflow

1. Read the prompt and `input/payloads/answer_template.json` first. The template is authoritative for required keys, allowed enum values, list ordering, date formats, and nested object fields.
2. Replace `<TASK_ENV_BASE_URL>` with the base URL from `environment_access.md`. Use only the remote ClinicProtocol API.
3. Retrieve the relevant protocol card with `/api/protocols` or `/api/protocols/{protocol_id}` and treat `local_rules` plus `outputs` as the clinical source of truth.
4. Retrieve only records needed for the patient, encounter, or care case named in the prompt.
5. Build exactly one JSON object. Do not add comments, markdown, extra keys, or explanatory text.

## API Habits

Useful GET patterns:

- `/api/status` for synthetic clock and timezone when the prompt gives no current time.
- `/api/protocols` to discover the five protocol cards and controlled outputs.
- `/api/protocols/{protocol_id}` for the local rule card.
- `/api/patients?identifier=<identifier>` when the prompt gives an MRN-like identifier; `/api/patients/{patient_id}` when it gives a patient id.
- `/api/encounters?patient_id=<patient_id>&encounter_id=<encounter_id>` for encounter-bound triage tasks.
- `/api/observations?patient_id=<patient_id>&code=<code>&status=<status>&category=<category>&date_from=<date>&date_to=<date>` for labs, vitals, imaging, and exclusion checks.
- `/api/medication_requests?patient_id=<patient_id>&status=<status>&category=<category>` for active QT-risk drugs, antibiotics, chronic medications, and cancelled orders.
- `/api/care_cases?case_id=<case_id>&patient_id=<patient_id>&status=<status>` for complex-care tasks.

Prefer specific filters, but if exclusions matter, also query broadly enough to see nearby wrong-status, wrong-code, panel-header, or stale observations that must be listed as ignored or excluded.

## Output Conventions

- `primary_protocol` must be the protocol id from the task family, such as `HEAD_INJURY_2026`, `RESP_ACUTE_2026`, `POTASSIUM_REPLETION_2026`, `FHIR_LAB_RETRIEVAL_2026`, or `COMPLEX_CARE_2026`.
- `case_id` is usually the encounter id for encounter tasks and the care case id for care-management tasks.
- `patient_id` must be the API `patient_id`, not the MRN identifier.
- List fields normally require lexicographic sorting when the template says so. Sort ids and enum codes exactly as strings.
- Evidence ids should be stable API resource ids that support the decision: encounter ids for encounter facts, observation ids for measured values or imaging, medication request ids for active medication evidence, and care case ids when the care case drives the decision.
- Include only evidence actually used for the final decision. Do not include stale distractors unless the schema has a dedicated ignored/excluded field.
- Preserve ISO-8601 timestamps with offsets when required. Date-only fields should be `YYYY-MM-DD`.
- Use template enum tokens exactly. Do not invent synonyms, change case, pluralize, or output prose in enum fields.

## Family Field Checklist

Head injury fields:

- `risk_level`: protocol route (`urgent_ed`, `same_day_clinic`, or `home_observation`).
- `ct_recommendation`: route-derived CT urgency (`urgent`, `consider`, or `not_required`).
- `disposition`: patient routing disposition matching the risk route.
- `red_flags_present`: only current red-flag codes supported by encounter facts.
- `activity_plan`: school, sports, and driving restrictions from symptom/red-flag status.
- `follow_up_hours`: numeric timing in hours from the protocol route.
- `contraindicated_actions`: actions the protocol forbids for the chosen route.

Respiratory fields:

- `primary_assessment`: best protocol diagnosis, such as pneumonia, viral URI, COPD/asthma exacerbation, or ED-required assessment.
- `site_of_care`: route based on ED criteria and stability.
- `severity_factors`: current findings from vitals, exam, symptoms, and imaging.
- `required_tests`: protocol test codes justified by assessment and route.
- `antibiotic_plan`: one controlled choice after applying route, allergy, and QT-risk constraints.
- `contraindicated_antibiotic_classes`: allergy and QT-risk exclusions.
- `return_precautions`: urgent or routine warning codes required by route.

Potassium fields:

- `current_time`: prompt time or API synthetic clock with timezone offset.
- `latest_potassium`: id, value, and timestamp of the most recent final local-code `K` serum potassium.
- `replacement_required`: true only when the selected final potassium is below target.
- `dose_meq`: rounded oral potassium chloride dose; use 0 if no replacement is required and the template allows an integer.
- `medication_order`: fixed protocol order fields when replacement is required.
- `follow_up_lab`: fixed LOINC/display/priority with next-day 08:00 local occurrence.
- `ignored_observation_ids`: potassium-like observations not used for dose selection.

FHIR lab retrieval fields:

- `query`: echo the requested resource type, exact code, and month.
- `has_matching_lab`: true when at least one exact final match exists.
- `matched_observation_ids`: ids of exact final matches.
- `matched_count`: count of matched ids.
- `first_match_date` and `last_match_date`: chronological date span of matches.
- `excluded_observation_ids`: nearby records intentionally rejected for status, panel header, code, patient, or date-window reasons.
- `resource_type` and `code_checked`: echo the exact resource type and code evaluated.

Complex-care fields:

- `risk_level`: low/moderate/high from risk score, admissions, disease control, medication burden, and SDoH.
- `program_type`: `complex_care`, `routine_care_management`, or `not_eligible` from protocol eligibility.
- `chart_concerns`: coded concerns grounded in documented chart facts.
- `required_assessment_domains`: barriers or clinical risks that intake must confirm.
- `consent_strategy_codes`: consent approach, especially for initial refusal or sensitive topics.
- `care_plan_problem_set`: problem areas to include in the care plan.
- `disciplines`: team roles needed for the selected problem set.
- `follow_up_cadence`: cadence required by risk/program type.
- `escalation_triggers`: conditions that should prompt escalation.
- `avoid_unsupported_guarantees`: true when the interaction must avoid promises beyond process help.

## Common Exclusions

Ignore or exclude records when they are:

- Not for the exact `patient_id`.
- Outside the requested encounter, month, or date window.
- `preliminary`, `cancelled`, or `entered-in-error` when the protocol requires final/current data.
- Panel headers rather than actual lab result observations.
- Inactive historical problem-list items when the current encounter contradicts or supersedes them.
- Cancelled medication requests when deciding current medication exposure or antibiotic plan.
- Older observations when a protocol asks for the most recent applicable final result.
- Coded differently from the local protocol requirement, even if the display text looks similar.

## Protocol Rules

### Head Injury: `HEAD_INJURY_2026`

Inputs usually include a current encounter and neuro/vital observations.

- Route `urgent_ed` for repeated vomiting, worsening headache, seizure, focal weakness, slurred speech, increasing drowsiness, confusion, amnesia over 30 minutes, anticoagulant use, abnormal gait or coordination, or deteriorating mental status.
- Use `same_day_clinic` for lower-risk symptoms needing clinician review but no urgent red flag.
- Use `home_observation` only when there are no red flags, neuro exam is normal, and reliable adult observation is available.
- CT recommendation follows route: `urgent` for `urgent_ed`, `consider` for same-day clinic with persistent symptoms or unreliable observation, otherwise `not_required`.
- Activity restrictions: no same-day return to play; no sports/high-risk activity until cleared; no driving if symptomatic or neurologic concerns are present.
- Follow-up timing: 24 hours for urgent or red-flag cases, 48-72 hours for same-day clinic, 72 hours for home observation. If the schema only accepts an integer, use the protocol/task convention for that route.
- Contraindicated actions commonly include self-driving, same-day return to play, and unsupervised home observation when red flags or reliability issues exist.

### Acute Respiratory: `RESP_ACUTE_2026`

Inputs usually include a same-day respiratory encounter, vitals, chest imaging, allergies, and active medication summary.

- Assess `community_acquired_pneumonia` when fever/cough is accompanied by focal crackles or chest x-ray infiltrate/consolidation.
- Route to `ed_evaluation` for room-air oxygen saturation below 92%, confusion, hypotension, respiratory rate at least 24, or pleuritic pain with hypoxia.
- Use outpatient/supportive routes only when stable and no ED criteria are present.
- Severity factors map directly from current encounter facts: hypoxia, tachypnea, focal crackles, lobar consolidation, pleuritic pain, hypotension, confusion.
- Required tests commonly include chest x-ray, pulse ox recheck, COVID/flu testing, BMP, and blood culture if ED evaluation is needed.
- Antibiotic plans must obey allergies and active QT-risk medications: avoid penicillin with penicillin allergy, sulfonamides with sulfa allergy, and macrolides or fluoroquinolones with active QT-risk drugs unless ED route means no outpatient antibiotic protocol is chosen.
- For ED route, the controlled antibiotic plan may be `no_antibiotic_protocol` even when pneumonia is present, because definitive antibiotics are deferred to ED protocol.

### Potassium Repletion: `POTASSIUM_REPLETION_2026`

Inputs usually include a patient id and current clinical time.

- Use the most recent final serum potassium Observation with local code `K`.
- Do not use preliminary, entered-in-error, older final, or differently coded potassium-like observations for dose selection.
- Target potassium is 3.5 mEq/L.
- If below target, order oral potassium chloride with NDC `40032-917-01`, route `oral`, intent `order`.
- Dose is 10 mEq per 0.1 mEq/L below target, rounded up to the next 10 mEq.
- Follow-up lab uses LOINC `2823-3`, display `Serum potassium`, priority `routine_next_morning`.
- Follow-up occurrence is the next calendar day at 08:00 in the local clinical timezone.
- Put non-applicable potassium observations in `ignored_observation_ids` when the schema asks for them.

### FHIR Lab Retrieval: `FHIR_LAB_RETRIEVAL_2026`

Inputs usually ask whether final Observation resources exist for an exact code and month.

- Match exact `patient_id`, exact Observation `code`, `resourceType` `Observation`, and `status` `final`.
- Use `effectiveDateTime` for date windows.
- Month windows include all instants from day 1 at 00:00:00 through the last day at 23:59:59 in the record timezone.
- Exclude panel headers, preliminary/cancelled/entered-in-error records, wrong codes, wrong patients, and records outside the month.
- `matched_count` must equal the number of ids in `matched_observation_ids`.
- `first_match_date` and `last_match_date` are chronological dates from matching observations, not lexicographic ids.
- `matched_observation_ids` and `excluded_observation_ids` are usually lexicographically sorted unless the prompt says otherwise.

### Complex Care: `COMPLEX_CARE_2026`

Inputs usually include a care case plus linked patient record, observations, medications, and SDoH flags.

- Use `complex_care` when registry risk score is at least 0.75 or recent high-acuity admission is paired with uncontrolled chronic disease.
- Risk level is high when multiple recent high-acuity admissions, uncontrolled chronic disease, advanced CKD/heart failure, medication burden, or major SDoH barriers cluster.
- Chart concerns should be grounded in the care case, active problems, recent admissions, active medications, observations, and SDoH flags.
- Required assessment domains must correspond to documented barriers or disease risks, not generic care-management topics.
- If the member persona initially refuses, refusal is not final; use voluntary, low-pressure, permission-based consent strategies.
- Always avoid unsupported guarantees about cost reduction, transportation availability, dialysis schedule flexibility, assistance approval, or clinical outcomes.
- A complex-care plan needs at least three problem areas, at least two disciplines, weekly follow-up, and escalation triggers covering clinical plus behavioral or SDoH risk when indicated.

## JSON Pitfalls

- Do not answer with a narrative. Output only the JSON object.
- Do not include train-case identifiers or values unless they are actually present in the current task records.
- Do not use display names where ids are required.
- Do not let stale inactive problems override current encounter facts.
- Do not miss active medication categories such as `qt_risk`, `anticoagulant`, or high medication burden.
- Do not count observations just because their display text matches; exact code, status, patient, date window, and panel-header status all matter.
- Do not forget to sort list fields lexicographically when required by the template.
- Do not add nulls for absent fields unless the template explicitly allows them; use the required enum/list/boolean shape.
