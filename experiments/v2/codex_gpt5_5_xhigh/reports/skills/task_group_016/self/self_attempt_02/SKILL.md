---
name: synthetic-clinic-protocol-json
description: Produce schema-constrained JSON for synthetic clinic protocol tasks. Use when a prompt asks Codex to review a task runtime with FHIR-like cases, patients, observations, medications, allergies, problems, imaging, care registry, SDOH, or protocol records, then return only a structured clinical decision-support, routing, observation-window, or safety-check JSON object.
---

# Synthetic Clinic Protocol JSON

## Core Workflow

1. Read the prompt and the provided answer template before querying the runtime.
2. Extract the target `case_id`, expected `task_id`, required top-level keys, enum domains, nullability, ordering rules, numeric precision, timestamp formats, and any required constants from the template.
3. Use only the runtime access file supplied with the task for network details. Do not use unlisted endpoints, credentials, or external clinical references.
4. Retrieve the target case with `GET /api/cases/{case_id}` first. This detail endpoint usually bundles the case, patient, findings, observations, medications, allergies, problems, imaging, care registry, and SDOH facts needed for the task.
5. Retrieve the protocol index with `GET /api/protocols`, choose the protocol whose title or scope matches the case type and prompt, then retrieve it with `GET /api/protocols/{protocol_id}`.
6. If the case detail is incomplete, use only the listed collection endpoints to cross-check case-linked or patient-linked records. Keep the target patient and case as the primary filter.
7. Build an evidence table before deciding: source id, record type, code/key, status, effective time, value, interpretation, and whether it qualifies.
8. Apply the protocol to qualifying evidence, then encode the result using only template-permitted keys, enums, nulls, precision, and ordering.
9. Return exactly one JSON object. Do not include markdown, explanatory prose, comments, or extra top-level keys unless the template explicitly allows them.

## Evidence Rules

- Treat the target case record as the anchor for `case_id`, `patient_id`, service date, case type, and current review time when present.
- Prefer stable source identifiers from observations, imaging, visit findings, registry rows, protocol records, and case records for `evidence_ids`.
- Use only `status=final` observations for clinical decisions unless the prompt or protocol says otherwise.
- Exclude preliminary, canceled, entered-in-error, wrong-code, wrong-patient, and out-of-window observations from protocol gates, but include their ids in excluded-observation fields when the schema asks for relevant distractors.
- For "latest" lab tasks, sort eligible observations by `effective_time`; use the latest final result that matches the target patient, target code, and allowed specimen/code family.
- For observation-window tasks, apply inclusive start and exclusive end boundaries unless the prompt or protocol says otherwise. Sort matched and excluded ids exactly as the template specifies.
- Do not infer normal findings from missing data. Only mark absent red flags or safety booleans true when the case evidence explicitly supports absence or when the boolean means "no unsupported claim was made."
- Map free-text findings into template enum codes conservatively. If evidence is ambiguous, choose the least assertive allowed enum that remains protocol-consistent.
- Preserve numeric precision from the template: round only as instructed and keep integer fields as integers.
- Preserve ISO-8601 UTC timestamps with trailing `Z` when requested.

## Protocol Family Rules

### Adult Respiratory Or CAP Assessment

- Use respiratory vitals, oxygen saturation and recheck values, viral PCR, chest imaging, symptoms, allergies, and the adult respiratory protocol.
- Classify pneumonia only when symptoms and imaging support consolidation; do not call the chest x-ray normal or lungs clear when imaging says otherwise.
- Escalate to emergency disposition when protocol thresholds or urgent red flags are met, especially severe hypoxemia, marked tachypnea, hypotension, confusion, sepsis concern, immunocompromise, or multilobar disease.
- For borderline oxygenation without emergency thresholds, include close outpatient follow-up and return precautions if the protocol permits outpatient care.
- Build the medication plan from active allergies and protocol options. Avoid active allergy classes and do not choose beta-lactam, sulfonamide, macrolide, or tetracycline options when the active allergy evidence rules them out.
- Include diagnostic tests that are recommended, pending, or already used as evidence only when their codes are allowed by the output schema.

### Pediatric Head Injury

- Use mechanism, symptoms, neurologic exam, GCS, loss of consciousness, vomiting count, headache course, seizure, focal deficits, basilar skull signs, and protocol triggers.
- Separate present red flags from explicitly absent red flags. Do not list absent findings as present red flags.
- Route to emergency evaluation and CT consideration when urgent triggers are present, such as repeated vomiting, severe or worsening headache, seizure, basilar skull signs, focal neurologic deficit, GCS below normal, or prolonged loss of consciousness.
- For mild symptoms with normal or near-normal exam and no urgent triggers, favor home observation, no immediate CT, concussion-style restrictions, and protocol follow-up.
- Include activity, school, sports, and driving restrictions only from the protocol and symptom evidence. Avoid claiming photophobia, vomiting, or loss of consciousness unless the evidence says they occurred.

### Potassium Repletion

- Use final serum potassium observations matching the protocol's serum potassium code. Ignore preliminary potassium results and non-serum potassium codes for the current potassium gate unless the protocol explicitly includes them.
- Evaluate urgent branches before routine replacement: severe low potassium, dialysis-dependent ESRD, severe renal contraindication, arrhythmia symptoms, or abnormal ECG should trigger urgent clinician handling rather than a routine oral order.
- Use renal function observations and case findings to populate contraindication fields. Keep eGFR numeric when present and `null` only when permitted and absent.
- When routine oral replacement applies, calculate the dose from the protocol target and dose rule, round as instructed, and use the protocol medication code/NDC.
- Schedule follow-up potassium labs from the protocol timing and current review time. Use the protocol follow-up lab code when the schema asks for an order-ready lab.

### Care-Management Routing

- Combine care registry facts, active problems, active medication count, observations, recent admissions, dialysis schedule, and SDOH/member-disclosed barriers.
- Classify risk from predictive score thresholds and supporting triggers such as multiple chronic conditions, recent admission, dialysis or advanced CKD, heart failure, uncontrolled diabetes, and polypharmacy.
- Route to complex care management when high risk and multiple complex-care triggers are present; otherwise choose the less intensive allowed program that matches the protocol.
- Keep chart-derived facts separate from member-disclosed facts in provenance fields. Transportation, financial, food, fatigue, access, and preference facts often require member disclosure provenance.
- Add referrals only when trigger evidence is present, such as pharmacist referral for high medication burden or insulin/electrolyte risk, social work for moderate or severe SDOH domains, and dialysis coordination for dialysis barriers.
- Use permission-based plain-language outreach when the member is reluctant, has requested timing constraints, or the protocol requires consent-oriented outreach.

### Observation-Window Protocol Gates

- Read the case findings for target patient, target code, window start, window end, and status rule.
- Match observations only when patient, code, status, and effective-time window all qualify.
- Include wrong patient, wrong code, wrong status, and date-excluded observations in excluded ids when they are relevant distractors requested by the schema.
- Select `latest_final` from matched observations only. If there are no matches, set nullable latest-final fields and lab-found fields according to the template.
- Choose the protocol gate from the latest eligible value and protocol thresholds or from the no-final-lab branch.
- Recommend repeat lab only when the protocol gate or template logic calls for it; otherwise use `false` and `null` where permitted.

## Output Checks

- Verify every required top-level key is present and no forbidden top-level key is present.
- Verify every enum value is copied exactly from the answer template.
- Verify nullable fields use `null` only where the template permits it.
- Verify arrays obey set semantics, uniqueness, and ordering rules from the template.
- Verify evidence identifiers correspond to records actually used for the decision.
- Verify safety-check booleans reflect unsupported-claim avoidance, not clinical reassurance.
- Verify the final response is valid JSON and contains no prose outside the object.
