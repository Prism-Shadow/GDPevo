---
name: clinic-protocol-json
description: Produce exact JSON answers for synthetic clinic protocol decision-support tasks that provide a runtime environment, a target case, patient clinical data, protocol material, and an answer_template.json schema. Use for respiratory, pediatric head injury, potassium replacement, observation-window, care-management, and similar clinic cases that require environment-backed facts, controlled enums, evidence identifiers, safety checks, and no prose outside JSON.
---

# Clinic Protocol JSON

## Core Workflow

Use the task's `answer_template.json` as the output contract before reasoning about the case.

1. Extract the required top-level keys, expected constants, allowed enum values, nullable fields, numeric precision, and ordering rules.
2. Read the runtime access file supplied with the task. Set `BASE_URL` from it and use only the listed endpoints.
3. Retrieve the target case with `GET $BASE_URL/api/cases/{case_id}`. Treat this detail endpoint as the primary bundle: case, patient, findings, observations, imaging, allergies, medications, problems, care registry, and SDOH.
4. Retrieve `GET $BASE_URL/api/protocols`, then read the protocol whose title or scope matches the case type. Use `GET $BASE_URL/api/protocols/{protocol_id}` for the body.
5. Fill only fields requested by the template. Do not add narrative, markdown, comments, or extra keys.
6. Validate the final object against the template manually: key presence, enum spelling, nullability, numeric precision, evidence IDs, and required safety booleans.

Prefer case-detail records over broad endpoint lists. Use broad endpoints only to recover missing linked data, then filter by target `patient_id`, `case_id`, code, status, and time window as the template requires.

## Evidence Discipline

- Use `status: "final"` observations for clinical decisions unless the template specifically asks for excluded or non-final observations.
- Ignore `preliminary`, `entered-in-error`, and `canceled` records for protocol gates, latest-result selection, and medication decisions.
- Filter to the target patient before deciding matched observations. Do not include wrong-patient rows in excluded lists unless the template explicitly asks for them.
- For latest-result fields, choose the latest eligible final observation by `effective_time`; use the exact observation ID and value from that row.
- For window tasks, use inclusive `from` and exclusive `to`. Sort matched and excluded observation IDs by `effective_time` ascending, then ID ascending, unless the template says otherwise.
- Evidence IDs should be stable source identifiers from the case bundle. Prefer the case ID first when the template asks for case-level provenance; prefer the decisive observation or registry IDs first when the template asks for descending relevance.
- Safety-check booleans usually mean "true if this answer did not make the unsupported claim." Verify the underlying fact instead of setting booleans mechanically.

## Protocol Patterns

### Respiratory Infection

Use the adult respiratory protocol and final vitals, respiratory testing, imaging, allergy, and medication data.

- Community-acquired pneumonia is supported by compatible respiratory symptoms plus final CXR/imaging consolidation. Viral URI is favored when imaging and protocol facts do not support pneumonia.
- ED escalation is driven by protocol thresholds such as room-air oxygen saturation below 90, respiratory rate at least 30, systolic blood pressure below 90, confusion, sepsis concern, immunocompromise, or multilobar disease.
- Oxygen saturation in the low 90s is a red flag but does not automatically force ED transfer unless an escalation threshold is met.
- Recommend diagnostic tests only from the template's allowed values and the protocol's controlled codes. Include tests already performed when the template asks for relevant diagnostic tests.
- Map active allergy names to medication classes: penicillin and amoxicillin to penicillin, sulfonamide antibiotics to sulfonamide, azithromycin to macrolide, doxycycline to tetracycline. Avoid active allergen classes in the medication plan.
- Do not claim normal CXR or clear lungs when the record contains consolidation or lacks support for those statements.

### Pediatric Head Injury

Use the pediatric head-injury protocol, findings, and final neuro observations.

- Classify mild TBI/concussion when there is head impact plus symptoms or mild exam findings, normal or near-normal neurologic status, and no urgent trigger.
- Urgent routing is supported by repeated vomiting, worsening severe headache, seizure, basilar skull signs, focal neurologic deficit, GCS below 15, or prolonged loss of consciousness.
- Record red flags that are present and absent red flags only when the case explicitly documents absence.
- Imaging recommendations follow the protocol branch: no immediate CT for stable non-urgent cases, CT or ED consideration for concerning intermediate cases, urgent CT for high-risk triggers.
- Restrictions should reflect cognitive and physical rest, return-to-learn accommodations, no high-risk sports until cleared, and driving limitations when symptoms, age, or sedating medications make them relevant.

### Potassium Replacement

Use the potassium protocol and final serum potassium observations.

- Serum potassium uses controlled code `K`. Do not substitute whole-blood potassium or preliminary serum results for the latest eligible serum result.
- Use the task/case clock from findings for `current_time`.
- Urgent escalation takes priority when potassium is below the protocol urgent threshold, dialysis-dependent ESRD is present, severe renal contraindication is present, ECG is abnormal, or symptoms suggest arrhythmia concern.
- When the routine branch applies, calculate oral dose from the protocol target: 10 mEq for each 0.1 mmol/L below target, rounded to the nearest 10 mEq.
- Use the protocol medication code for routine oral potassium. If the urgent branch applies, defer medication details and populate urgent actions from the template's allowed values.
- Follow-up potassium timing comes from the protocol; express scheduled times as ISO-8601 UTC timestamps when required.
- Contraindication fields must come from problems, registry data, findings, ECG summary, and eGFR observations, not assumptions.

### Observation Windows

Use the observation-window protocol plus the case findings that define target code and time bounds.

- A lab is found only when a final target-code observation belongs to the target patient and falls inside the window.
- Matched IDs include only qualifying observations.
- Excluded IDs should be relevant target-patient distractors that fail because of date, code, or status, following the template's scope and ordering rule.
- `latest_final` is null only when no qualifying final observation exists; otherwise it is the latest matched final observation.
- Derive the protocol gate from the latest eligible final value and the relevant protocol thresholds.

### Care Management

Use care registry, active problems, final observations, medications, SDOH, member-call findings, and the high-risk care-management protocol.

- High risk is supported by the protocol risk-score threshold plus complex triggers such as multiple chronic conditions, recent admission, dialysis or advanced CKD, heart failure, and uncontrolled diabetes.
- Priority problems come from active diagnosis/problem rows, abnormal final labs or vitals, registry facts, active medication burden, SDOH barriers, and member-disclosed needs.
- Pharmacist referral is supported by high active-medication count, insulin safety issues, or high-risk diuretic/electrolyte regimens.
- Social work and transportation referrals require SDOH or member-disclosed barriers at the severity/scope described by the protocol.
- Keep chart-derived facts separate from member-disclosed facts in provenance fields.
- Use permission-based outreach when the protocol or member context indicates reluctance, preference-sensitive contact, or social needs requiring consent.
- Care-plan minima should reflect the current protocol's required elements, including initial follow-up cadence, medication reconciliation, barrier resolution, member-stated priorities, interdisciplinary involvement, and clear escalation conditions.

## Final JSON Checks

Before finalizing:

- Compare every string value against the template's exact enum spelling.
- Use `null` only where the template permits it.
- Round numeric values to the template precision without converting units.
- Preserve required object shapes even when a branch is negative.
- Do not reuse identifiers or values from prior examples; every identifier, timestamp, value, and evidence list must come from the current task environment.
- Return exactly one JSON object and nothing else.
