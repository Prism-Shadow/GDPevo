---
name: clinic-protocol-json
description: Create strict JSON responses for synthetic clinic runtime decision-support tasks. Use when a prompt asks Codex to review a clinic case via runtime endpoints and return a protocol-bound answer template for adult respiratory/CAP assessment, pediatric head injury triage, potassium replacement, care-management routing, or observation-window lab retrieval.
---

# Clinic Protocol JSON

## Workflow

1. Read the user prompt and the provided `input/payloads/answer_template.json` first. Treat the template as the output contract for required keys, constants, enum values, nullability, precision, and ordering.
2. Read the runtime access file supplied with the task to get the base URL and allowed endpoints. Use only that runtime for case data. Prefer read-only `GET` endpoints; use `POST /api/query` only as a read-only retrieval helper when needed.
3. Fetch the target bundle with `GET /api/cases/{case_id}`. The bundle may contain `case`, `patient`, `findings`, `observations`, `imaging`, `medications`, `allergies`, `problems`, `care_registry`, and `sdoh`.
4. Fetch the relevant protocol from `GET /api/protocols` and `GET /api/protocols/{protocol_id}`. Map case types to protocol families:
   - `acute_respiratory`: adult respiratory infection/CAP protocol.
   - `pediatric_head_injury`: pediatric head injury clinic triage protocol.
   - `potassium_repletion`: potassium replacement and escalation protocol.
   - `care_management`: high-risk care-management routing protocol.
   - `observation_window`: observation-window interpretation protocol.
5. Derive every output field from the current case bundle, protocol, and answer template. Do not reuse identifiers, selected findings, or numeric answer values from prior examples.

## Evidence Rules

- Match the target `case_id` and `patient_id`. Watch for distractor observations with the same case but wrong patient, wrong code, wrong date, or non-final status.
- Use only protocol-authoritative statuses for clinical decisions, usually `status: "final"`. Non-final records can appear in excluded-observation lists when the template asks for them.
- For time-based fields, compare ISO timestamps directly after confirming the window rule. Observation-window tasks use inclusive `from` and exclusive `to` unless the case/protocol says otherwise.
- For latest-lab decisions, sort eligible observations by `effective_time`, then use `observation_id` as the tie-breaker when the template specifies it.
- Use stable source identifiers in `evidence_ids`: observation IDs, imaging IDs, registry/source IDs, and sometimes the case ID when the template or task asks for it. Do not cite a source unless it supports a selected field.

## Domain Patterns

### Adult Respiratory/CAP

- Assess CAP when final imaging or observation text supports focal consolidation with compatible respiratory symptoms; assess viral URI/supportive care only when pneumonia evidence is absent.
- Identify red flags from oxygen saturation, respiratory distress/rate, blood pressure, confusion, chest pain, hemoptysis, persistent fever, worsening dyspnea, and imaging extent according to the protocol and template enums.
- Escalate to ED when protocol thresholds or high-risk red flags are met; otherwise use outpatient close follow-up when the protocol supports it.
- Build allergy-aware medication plans from active allergies. Avoid implicated antibiotic classes and keep `avoid_allergens` aligned to template enum values.
- Set safety booleans to confirm unsupported claims were avoided, such as normal chest x-ray or clear lungs when those facts are not supported.

### Pediatric Head Injury

- Use final neurologic observations and visit findings for GCS, loss of consciousness, vomiting count, headache course, seizure, focal weakness/deficit, basilar skull signs, photophobia, and coordination symptoms.
- Urgent or CT/ED routing is driven by protocol triggers such as repeated vomiting, worsening severe headache, seizure, basilar skull signs, focal neurologic deficit, GCS below normal, or prolonged loss of consciousness.
- Mild TBI/concussion routing applies when symptoms are present with no urgent trigger and neurologic exam is normal or near-normal.
- Populate present and absent red flags separately; absence must be explicitly supported by findings or observations.
- Add restrictions for cognitive/physical rest, return-to-learn, high-risk sports, and driving only when compatible with the current symptoms and template enums.

### Potassium Replacement

- Use the latest final serum potassium observation with the protocol's serum-potassium code. Exclude preliminary results and non-serum potassium codes from the replacement decision unless the template asks to list them as excluded evidence.
- Screen urgent branch before routine repletion: critically low potassium, ECG abnormality, arrhythmia symptoms, dialysis-dependent ESRD, or severe renal contraindication.
- If urgent branch is false and potassium is below the protocol target, calculate routine oral replacement from the protocol dose rule and round as specified. If urgent branch is true, defer to urgent clinician workflow and do not create routine oral-order details.
- Use current review time from the case findings when the template requires `current_time`.
- Schedule follow-up serum potassium according to the protocol/case timing, and use the protocol's lab code and medication code when the template asks for order-ready details. Never mutate the runtime or place an order.

### Care-Management Routing

- Use care-registry fields, active problems, final observations, active medication count, SDOH entries, and call/member-disclosure findings.
- High-risk complex-care routing is supported by high predictive risk plus triggers such as multiple chronic conditions, recent admission, dialysis or advanced CKD, heart failure, and uncontrolled diabetes.
- Identify priority problems from active diagnoses, abnormal observations, registry facts, medication burden, and member-disclosed barriers. Use only template enum codes.
- Add pharmacist referral for polypharmacy, insulin safety, or high-risk diuretic/electrolyte regimens. Add social-work or transportation referrals when SDOH domains and severity meet protocol criteria.
- Use permission-based outreach when the member is reluctant, refusing, or requests control over contact timing.
- Separate chart facts from member-disclosed facts in source provenance.

### Observation-Window Retrieval

- Pull target code, patient, and window boundaries from case findings and protocol materials.
- Matched observations must belong to the target patient, have the target code, be final, and fall inside the window.
- Sort matched IDs by `effective_time` ascending, then `observation_id` ascending. Use the same ordering for excluded relevant distractors when requested.
- Excluded observations are relevant records that fail because of date, code, or status. Include wrong-patient records only when the template or prompt explicitly asks for that exclusion class.
- Set `latest_final` to the latest matched final observation, or `null` only if the template allows it and no qualifying lab exists.
- Set protocol-gate and repeat-lab fields from the latest eligible value and protocol thresholds, not from non-final or out-of-window distractors.

## Output Checks

- Return one JSON object only. Do not include markdown, comments, explanations, or extra top-level keys unless the template explicitly allows them.
- Preserve required constants from the template and prompt, such as `task_id` and `case_id`.
- Use enum strings exactly as listed in the template; translate protocol wording into template enum values.
- Use `null` only where the template permits it. Use empty arrays for no selected items when lists are required.
- Respect array ordering rules. Treat unordered enum lists as sets with no duplicates.
- Check numeric precision and units before finalizing.
- Re-read the completed JSON against the template: every required key present, no unsupported claims, all identifiers from the current case, and every safety-check boolean logically satisfied.
