---
name: clinical-protocol-decision-support
description: Solve synthetic ClinicProtocol clinical decision-support tasks by querying scoped protocol, patient, encounter, observation, medication, and care-case records and returning exact template-shaped JSON.
---

# Clinical Protocol Decision Support

Use this SOP for synthetic ClinicProtocol tasks that ask for a structured JSON decision from protocol cards plus scoped clinical records. This is not real medical advice; follow the task's local protocol and answer template exactly.

## Workflow

1. Read the prompt and `input/payloads/answer_template.json` before querying. Copy the required top-level keys, nested object keys, enum spellings, primitive types, date formats, and list ordering rules.
2. Replace `<TASK_ENV_BASE_URL>` with the base URL provided by the task environment. Query only identifiers present in the prompt/template/protocol: patient id, encounter id, case id, protocol id, code, status/category, and date windows.
3. Fetch the protocol card with `GET /api/protocols/{protocol_id}`. Treat `local_rules` and `outputs` as binding over general clinical knowledge.
4. Fetch records with filtered endpoints:
   - Patient: `/api/patients?identifier=<PAT...>` then `/api/patients/{patient_id}` when details are needed.
   - Encounter: `/api/encounters?patient_id=<id>&encounter_id=<id>`; add `kind` only if the task supplies it.
   - Observations: `/api/observations?patient_id=<id>&code=<code>&status=<status>&category=<category>&date_from=<YYYY-MM-DD>&date_to=<YYYY-MM-DD>`.
   - Medication requests: `/api/medication_requests?patient_id=<id>&status=<status>&category=<category>` when medication/allergy/QT/current therapy affects the protocol.
   - Care cases: `/api/care_cases?case_id=<id>` or `/api/care_cases?patient_id=<id>&status=<status>` when the task asks for case management.
5. Build the answer from the template, not from prose preferences. Sort all lists lexicographically when the template says so. Do not add extra keys.

## Identifier And Evidence Conventions

- Use the stable API ids exactly: `patient_id`, `encounter_id`, `case_id`, Observation `id`, MedicationRequest `id`.
- If a template field is named `observation_id` but the API object uses `id`, return the API `id`.
- For encounter-only tasks requiring `case_id` with no care case record, use the encounter id as the case identifier.
- Put the protocol id only in `primary_protocol`; do not duplicate it in `evidence_ids` unless the template explicitly asks for protocol evidence.
- `evidence_ids` should name source records that support the decision, usually relevant Observation ids and encounter/case ids. Keep ignored/excluded ids in their dedicated fields instead.

## Transferable Protocol Rules

- Head injury: urgent ED route for red flags such as repeated vomiting, worsening headache, seizure, focal weakness, slurred speech, confusion/deteriorating mental status, increasing drowsiness, abnormal gait/coordination, anticoagulant use, or amnesia over 30 minutes. Home observation requires no red flags, normal neuro exam, and reliable adult observation. Urgent ED implies urgent CT, ED disposition, no same-day return to play, no driving while symptomatic/not cleared, and short follow-up.
- Respiratory: community-acquired pneumonia is supported by fever/cough plus focal crackles, infiltrate, or consolidation. ED evaluation is triggered by O2 below 92%, confusion, hypotension, RR at least 24, or pleuritic chest pain with hypoxia. Respect allergies and QT-risk medications: avoid penicillin with penicillin allergy, sulfonamides with sulfa allergy, and outpatient macrolide/fluoroquinolone use when QT-risk therapy is active. Doxycycline is often the safer CAP option when beta-lactam and QT constraints apply.
- Potassium repletion: use the protocol's current potassium code for the latest final serum potassium result; the follow-up LOINC may be different. Ignore preliminary and entered-in-error observations. Dose from the target deficit using the protocol's rounding rule. Schedule follow-up serum potassium for the next calendar day at 08:00 in the local timezone when required.
- FHIR-style lab retrieval: match exact patient id, exact code, final status, lab category, and `effectiveDateTime` inside the inclusive month window. Return matched Observation ids sorted lexicographically unless the template says chronological. First/last dates are chronological dates, not lexicographic ids.
- Complex care: complex-care eligibility commonly follows risk score at least 0.75 or recent high-acuity admissions plus uncontrolled chronic disease. Map chart concerns, assessment domains, care-plan problems, disciplines, and escalation triggers only from chart/referral/SDoH/persona cues. Initial refusal calls for voluntary, permission-based, plain-language consent strategies. Do not guarantee lower costs, ride availability, dialysis scheduling flexibility, or assistance approval.

## Common Exclusions And Pitfalls

- Exclude stale, inactive, preliminary, cancelled, entered-in-error, wrong-patient, wrong-code, and out-of-window records from current clinical decisions.
- Do not let an inactive historical diagnosis override current encounter facts.
- Do not use the follow-up lab code as the current-result query code unless the protocol says they are the same.
- Preserve booleans as booleans, numeric dose/count fields as numbers, and ISO timestamps with the correct timezone offset.
- `first_match_date` and `last_match_date` should reflect chronological effective dates; matched id lists usually remain lexicographic.
- For list enums, missing one indicated item or adding one unsupported item usually invalidates the whole field. When uncertain, prefer chart-grounded evidence over broad inference.
