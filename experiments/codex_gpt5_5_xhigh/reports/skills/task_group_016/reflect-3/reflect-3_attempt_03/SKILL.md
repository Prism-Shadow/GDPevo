---
name: clinical-protocol-decision-support
description: Solve synthetic ClinicProtocol decision-support tasks by using scoped API retrieval, protocol-card rules, and exact schema-conformant JSON outputs.
---

# Clinical Protocol Decision Support SOP

Use this skill for ClinicProtocol tasks that ask for a protocol-bound clinical decision, retrieval result, medication/lab order, or care-management escalation. These tasks are synthetic and require protocol compliance, not free-form medical advice.

## Workflow

1. Read the prompt and `input/payloads/answer_template.json` before querying records. Treat the template as the output contract: required keys, enums, booleans, date formats, numeric precision, and lexicographic list ordering are mandatory.
2. Extract only identifiers named by the prompt/template: patient identifier, encounter id, case id, current time, target month/date window, protocol id, and relevant codes.
3. Fetch the protocol card by id from the template enum, then use its local rules to decide which API records and codes are needed.
4. Query only scoped records. Avoid broad unfiltered record endpoints.
5. Build the answer with exact enum strings from the template, sorted lists, no extra keys, no explanatory text, and stable source identifiers.

## API Habits

Prefer these scoped patterns:

- `/api/protocols/{protocol_id}` for the protocol in `primary_protocol`.
- `/api/patients?identifier=<prompt_patient_identifier>` to resolve the patient, then use the API `patient_id` in answers.
- `/api/patients/{patient_id}` only for a linked patient returned by a scoped case record.
- `/api/encounters?patient_id=<patient_id>&encounter_id=<encounter_id>` for encounter tasks.
- `/api/care_cases?case_id=<case_id>` for care-management tasks.
- `/api/observations?patient_id=<patient_id>&code=<code>&status=<status>&date_from=<YYYY-MM-DD>&date_to=<YYYY-MM-DD>` for labs. Omit `status` only when identifying excluded non-final records, and keep patient/code/date filters.
- `/api/medication_requests?patient_id=<patient_id>&status=<status>&category=<category>` only when the prompt/protocol requires medication context.

Do not assume a common clinical code when the protocol defines a task-local code. A protocol may use one code for existing observations and a different LOINC for a follow-up order.

## Output Conventions

- Use API `patient_id`, not MRN/identifier, unless the template explicitly asks otherwise.
- For `case_id`, use the case id from the prompt/case record. In encounter-only tasks with no separate case record, use the stable encounter/case identifier named by the prompt if the template requires `case_id`.
- `evidence_ids` should be stable API ids or stable fact keys that directly support the decision or material exclusions. Do not invent prose identifiers.
- `ignored_observation_ids` and `excluded_observation_ids` should contain same-patient/same-code records rejected by protocol rules, such as non-final, entered-in-error, panel headers, stale/superseded, or out-of-window resources.
- Preserve ISO timestamps and time zones from source records. For date-only fields, derive `YYYY-MM-DD` from `effectiveDateTime`.
- Sort every list lexicographically when the template says so, including enum lists and id lists.

## Transferable Rules

Head injury:
- Urgent ED route applies for current red flags such as repeated vomiting, increasing drowsiness, confusion, seizure, focal weakness, slurred speech, worsening headache, anticoagulant use, or amnesia over the protocol threshold.
- Urgent ED implies urgent CT recommendation, ED disposition, no same-day return to play, no unsupervised home observation, and restricted driving/activity until evaluated or cleared.
- Ignore inactive/stale historical concussion facts unless the protocol says they affect the current event.

Respiratory:
- Fever/cough with focal crackles or infiltrate supports pneumonia, but oxygen below 92%, tachypnea, hypotension, confusion, or pleuritic pain with hypoxia should drive ED evaluation when the protocol says so.
- Include severity factors that match template labels exactly, such as `oxygen_below_92`, `tachypnea`, `pleuritic_pain`, `focal_crackles`, and `lobar_consolidation`.
- For outpatient antibiotic planning, honor allergy/QT exclusions. Active QT-risk medication generally contraindicates macrolide and fluoroquinolone outpatient choices unless the protocol explicitly routes antibiotic selection to ED care.

Potassium:
- Select the most recent final applicable potassium observation using the protocol-defined result code.
- Ignore preliminary, entered-in-error, and superseded observations when choosing the latest applicable result.
- If below target, dose oral potassium chloride using the protocol NDC/route/intent. Compute dose as 10 mEq per 0.1 mEq/L below target, rounded up to a 10 mEq increment.
- Schedule follow-up serum potassium for the next calendar day at 08:00 in the local clinical timezone when the protocol says next morning.

FHIR-style lab retrieval:
- Match exact patient id, exact code, final status, and the requested month using `effectiveDateTime`.
- Month windows include the first day 00:00:00 through the last day 23:59:59 in the record timezone.
- Count only actual laboratory Observation resources. Exclude panel headers, preliminary/cancelled/entered-in-error records, nearby out-of-window records, and linked records for other patients.
- Return matched ids sorted lexicographically unless the template explicitly asks for chronological order.

Complex care:
- High registry risk or recent high-acuity admission plus uncontrolled chronic disease supports complex-care program selection when the protocol threshold is met.
- Map chart concerns from both the care case and linked patient record: active disease metrics, recent admissions, medication burden/refill gaps, behavioral-health history, and documented SDoH flags.
- Required assessment domains and care-plan problem areas must be grounded in case/referral cues; include social work, pharmacist, care manager, PCP, and behavioral-health disciplines when supported.
- For initial refusal, use voluntary, permission-based, bounded-help consent strategies. Avoid unsupported guarantees about costs, transportation, assistance approval, or scheduling flexibility.

## Pitfalls

- Do not submit free text, extra keys, wrong enum strings, or unsorted lists.
- Do not use final-order LOINCs as historical-result codes unless the protocol says they are the same.
- Do not count panel headers as lab matches even when they share the requested code and final status.
- Do not let stale conflicts, inactive problems, or old observations override current encounter/case facts.
- Do not broaden record retrieval beyond the named patient/case/encounter/code/date scope.
