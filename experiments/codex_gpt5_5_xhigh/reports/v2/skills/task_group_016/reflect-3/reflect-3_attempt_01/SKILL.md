---
name: clinical-protocol-decision-support
description: Solve ClinicProtocol clinical decision-support tasks by retrieving narrowly scoped patient/case data, applying local protocol cards, and returning exact schema-matching JSON.
---

# Clinical Protocol Decision Support SOP

## Core Workflow

1. Read the prompt and `input/payloads/answer_template.json` first. Copy the required top-level keys, nested keys, enum spellings, boolean types, numeric precision, date formats, and list ordering rules exactly.
2. Replace `<TASK_ENV_BASE_URL>` with the provided ClinicProtocol API base URL. Fetch only records named or logically required by the prompt/template/protocol.
3. Fetch the relevant protocol card before interpreting clinical facts:
   - `GET /api/protocols/{protocol_id}`
   - Use `local_rules` for thresholds, route logic, exclusions, timing, dose rules, and output conventions.
4. Retrieve data narrowly:
   - Patient by prompt identifier: `/api/patients?identifier=<patient_id_or_identifier>`.
   - Encounter by exact patient and encounter: `/api/encounters?patient_id=<patient_id>&encounter_id=<encounter_id>`.
   - Case by exact case id: `/api/care_cases?case_id=<case_id>`; use linked `patient_id` from the case.
   - Observations by exact patient, code, and date window: `/api/observations?patient_id=<patient_id>&code=<code>&date_from=<start>&date_to=<end>`.
   - Medications by exact patient and relevant status/category: `/api/medication_requests?patient_id=<patient_id>&status=active`.
5. Inspect response keys before assuming field names. Observation ids may be in `id`, not `observation_id`; patient records use `patient_id`.

## Output Conventions

- Return one JSON object only; no prose, markdown, or extra keys.
- Sort lists lexicographically when the template says so.
- Use stable source identifiers from API resources. Prefer actual `id`, `encounter_id`, `case_id`, or medication/request ids over invented fact-path strings.
- `case_id`: use the care case id when a case exists. For encounter-only tasks with no care case returned, the encounter id may be the safest case identifier.
- Evidence ids should support the decision without becoming a dump of every related record. For lab-selection decisions, evidence usually centers on the selected applicable observation. Retrieval tasks often separate `matched_*` ids from `excluded_*` ids, so do not duplicate those concepts unless the template asks for evidence separately.
- Preserve prompt timezones in ISO timestamps. Month windows use `effectiveDateTime` from the first day at `00:00:00` through the last day at `23:59:59`.

## Transferable Protocol Rules

- Head injury:
  - Any current red flag routes to `urgent_ed`, `urgent` CT, and `send_to_ed_now`.
  - Red flags include repeated vomiting, worsening headache, seizure, focal weakness, slurred speech, increasing drowsiness, confusion, amnesia over 30 minutes, anticoagulant use, abnormal gait/coordination, and deteriorating mental status.
  - Red-flag cases need no same-day return to play, no self-driving when symptomatic or neurologically concerning, supervised observation, and short follow-up such as 24 hours.

- Acute respiratory:
  - Keep `primary_assessment` as the clinical syndrome when supported, such as community-acquired pneumonia from fever/cough plus focal crackles or infiltrate; use `site_of_care` for ED routing.
  - ED criteria include room-air O2 below 92%, confusion, hypotension, respiratory rate at least 24, or pleuritic pain with hypoxia.
  - Active QT-risk medications contraindicate macrolide and fluoroquinolone outpatient choices. ED-routed cases may call for `no_antibiotic_protocol` rather than choosing an outpatient antibiotic.

- Potassium repletion:
  - Use the protocol's source potassium code for current results; the follow-up lab LOINC may be different.
  - Select the most recent `final` potassium observation at or before current time.
  - Ignore `preliminary`, `entered-in-error`, and other non-final/non-applicable observations.
  - Target potassium is 3.5 mEq/L. If below target, dose oral potassium chloride at 10 mEq per 0.1 mEq/L deficit, rounded up to the next 10 mEq.
  - Follow-up serum potassium is next local calendar day at 08:00 when the protocol says `routine_next_morning`.

- FHIR-style lab retrieval:
  - Match exact patient id, exact code, resource type `Observation`, and target month using `effectiveDateTime`.
  - Count only final, non-panel Observation resources.
  - Exclude panel headers, preliminary/cancelled/entered-in-error records, linked different-patient records, and same-code nearby records outside the target month when the output asks for excluded ids.
  - Return first/last match as date-only strings when requested.

- Complex care:
  - High registry risk or recent high-acuity admissions plus uncontrolled chronic disease supports `high` risk and `complex_care`.
  - Map only documented cues to chart concerns, assessment domains, care-plan problems, disciplines, and escalation triggers.
  - Medication burden/refill gaps support pharmacist and medication-cost/access domains. Food, utility, and transportation flags support social-work/resource and transportation follow-up.
  - Initial refusal calls for voluntary, low-pressure consent: reflect the refusal, ask permission before sensitive topics, explain bounded process help, avoid guarantees, and use plain-language scheduling/condition explanations.
  - Do not guarantee lower costs, ride availability, dialysis-slot flexibility, or assistance approval.

## Common Pitfalls

- Do not use inactive, stale, outside, preliminary, cancelled, entered-in-error, or panel-header records as current clinical evidence.
- Do not let severe route labels replace a supported diagnosis unless the protocol explicitly says the primary assessment should be route-only.
- Do not add enum items just because they are plausible. Every concern/domain/discipline/trigger should trace to an explicit chart, case, observation, medication, or protocol cue.
- Do not include unsupported dialysis, COPD, housing, behavioral-health, or allergy constraints unless the retrieved record actually documents them.
- Do not round potassium deficits down; round the total dose up to the next 10 mEq.
- Do not omit nearby out-of-window same-code observations from `excluded_observation_ids` when a retrieval template asks for nearby exclusions.
