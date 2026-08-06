---
name: clinic-protocol-json
description: Build protocol-bound structured JSON answers for synthetic clinic runtime tasks. Use when Codex must inspect a provided clinical runtime environment and answer from a strict JSON template for respiratory assessment, pediatric head injury triage, potassium replacement or lab-window decisions, care-management routing, or similar FHIR-like case/protocol workflows.
---

# Clinic Protocol JSON

## Core Workflow

1. Read the user prompt and the answer template before retrieving data. Treat the template as the contract: required keys, enums, nullability, ordering, and numeric precision all matter.
2. Identify the target case ID from the prompt, then resolve the patient ID from the case record. Do not rely on patient names or case summaries alone.
3. Retrieve the target case, patient context, applicable protocol, and only the clinical domains needed by the template. Prefer targeted case/patient data when available, then use broader resource lists only to find distractors or confirm omissions.
4. Build a small evidence table while reading: source ID, resource type, status, code, time, patient ID, value, and whether it supports or excludes a template field.
5. Apply the protocol before filling disposition, treatment, routing, gate, or follow-up fields. Use protocol thresholds and controlled codes over general clinical intuition.
6. Fill the JSON from high-confidence identifiers and scalar fields first, then coded sets, then evidence IDs and safety checks. Return exactly one JSON object with no markdown or prose.

## Evidence Discipline

- Use only authoritative resource statuses unless the protocol says otherwise. Most observation tasks reward `final` results and exclude `preliminary`, `canceled`, and `entered-in-error`.
- Match observations by patient ID, target code, status, and time window. A case-linked observation for another patient is a distractor; do not include it unless the template explicitly asks for wrong-patient exclusions.
- For "latest" lab fields, sort eligible observations by effective time, not by listing order. Ignore non-target specimen/code variants when the protocol specifies a narrower code.
- For excluded observation lists, include relevant target-patient distractors excluded by date, code, or status. Keep the template's requested ordering exactly.
- Evidence IDs should be stable source/resource identifiers that directly support the answer. Avoid padding with loosely related IDs; include protocol IDs only when the task asks for protocol provenance.

## Coded Sets

- Do not over-code. Include a red flag, restriction, priority problem, referral, or escalation condition only when it is directly documented or is a protocol-mandated consequence of documented data.
- Distinguish documented absence from missing data. Numeric zero, normal exam text, or explicit "absent/none" can support absent-red-flag codes; mere silence usually should not.
- Preserve template vocabulary exactly. Map clinical wording to allowed enum values, but never invent synonyms.
- If a set is unordered, still use a stable order: case/source facts first when requested, otherwise clinical sequence or chronological order.

## Domain Patterns

### Respiratory Protocol Assessments

- Determine infection assessment from symptoms plus imaging and test results; do not claim normal imaging or clear lungs unless the record supports it.
- Use oxygen saturation, respiratory rate, blood pressure, confusion, imaging extent, and protocol thresholds to choose outpatient versus ED disposition.
- Keep borderline hypoxemia distinct from severe hypoxemia when both codes exist.
- Make medication plans allergy-aware. Avoid active allergy classes and choose the protocol's alternate outpatient strategy when needed.

### Pediatric Head Injury

- Separate urgent CT/ED triggers from mild symptoms that only require observation.
- Treat no loss of consciousness, no vomiting, normal GCS, stable headache, and no focal weakness as specific evidence; avoid marking undocumented symptoms as absent.
- Use protocol language for activity, school, sports, and driving restrictions. Driving restrictions can still be relevant if the template asks for them.

### Potassium Replacement

- Select the latest eligible final serum potassium result before assessing replacement.
- Evaluate urgent branch and contraindications before routine oral repletion. Check symptoms, ECG, dialysis/ESRD, severe renal impairment, and protocol critical thresholds.
- If routine repletion applies, calculate dose from the protocol formula and round rule. Use the protocol's medication code and follow-up lab code when present.
- Schedule repeat labs from the protocol's timing instruction and the task's clinical clock.

### Observation Window Gates

- Treat window start as inclusive and end as exclusive when the template says so.
- Matched observations must satisfy patient, code, status, and window together.
- Use the latest matched final result for downstream protocol gates. Normal final results usually satisfy "recent final normal" gates; low or critical values follow the protocol's branch.

### Care-Management Routing

- Combine registry risk, chronic conditions, recent admissions, active medication count, observations, and social-context records.
- High-risk complex care generally requires protocol risk threshold support plus multiple documented clinical or social triggers.
- Separate chart facts from member-disclosed facts in provenance fields. Put barriers in member-disclosure provenance only when the source is member disclosure or the template asks for member-stated priorities.
- Keep referrals tied to explicit triggers such as polypharmacy/insulin, dialysis coordination, transportation or financial barriers, and behavioral-health screens.

## Final Validation

- Confirm every required top-level key is present and no disallowed top-level key is present.
- Confirm every enum value appears exactly as allowed.
- Confirm nulls appear only where permitted.
- Confirm numbers meet requested precision and timestamps use the required ISO format.
- Confirm safety-check booleans are true only when the answer avoids the unsupported claim named by the check.
