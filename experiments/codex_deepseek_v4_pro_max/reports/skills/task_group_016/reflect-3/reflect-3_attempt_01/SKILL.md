# Synthetic Clinic Protocol Decision Support

## Overview
This skill covers solving structured clinical decision-support tasks against a synthetic FHIR-like clinic API. Tasks require querying patient records, cases, observations, medications, allergies, imaging, protocols, and social-determinant data, then producing a JSON answer conforming to a strict template with controlled enum values.

## Core Workflow

### 1. Retrieve the Case Record
Query the case endpoint with the target case identifier. The case response bundles the case metadata, patient demographics, findings, observations, medications, allergies, problems, imaging, care-registry data, and SDOH entries in a single call. Use this as the primary data source.

### 2. Retrieve the Applicable Protocol
List available protocols, then fetch the one relevant to the case type. Protocols define clinical thresholds, escalation rules, medication codes, follow-up timing, and status-authority rules. Every clinical decision must be derived from protocol rules applied to case data — not from general clinical knowledge.

### 3. Map Findings to Template Enums
Answer templates define allowed enum values for each field. Map clinical findings to these controlled vocabularies:
- Match finding keys and observation interpretations to the closest allowed enum.
- When a template field has an "allowed_values" list, choose only from that list.
- For list-typed fields like red_flags, include only findings actually present; omit absent findings unless the template has a separate absent-findings list.

### 4. Handle Status Filtering
Protocols typically declare authoritative statuses (e.g., "final" only). Never use preliminary, entered-in-error, or canceled observations for clinical decisions. When a protocol says "authoritative_statuses": ["final"], exclude all non-final observations from decision inputs.

### 5. Apply Protocol Rules to Enums
For each scored decision field, trace the protocol rule to the case data:
- **Risk/disposition**: Compare numeric values against protocol thresholds (e.g., oxygen saturation below a cutoff, risk score above a minimum).
- **Medication plans**: Check allergy constraints against medication classes; use protocol-specified NDC codes and dosing rules.
- **Follow-up timing**: Use protocol-specified hours, not general guidelines.
- **Escalation/urgent actions**: Check each protocol trigger condition against case data; if none fire, use empty lists or appropriate null/negative values.

### 6. Handle Observation Windows
When a task defines a time window for observations:
- Use the window bounds exactly as specified (typically inclusive start, exclusive end).
- Filter observations by patient_id, code, status, and effective_time.
- Sort matched observations by effective_time ascending, then observation_id ascending.
- Exclude observations that fall outside the window, have the wrong code, wrong patient, or non-authoritative status.
- The latest final observation (by effective_time) in the window drives the protocol gate.

### 7. Avoid Common Pitfalls
- **Wrong-patient observations**: Check patient_id on every observation; observations belonging to other patients are distractors, not clinical inputs.
- **Wrong specimen type**: A whole-blood potassium (code 6298-4) is not the same as serum potassium (code "K"). Match on the exact target code.
- **Preliminary results**: Never treat preliminary-status observations as final even if they have a more recent timestamp.
- **Protocol code mismatches**: Return-precaution codes in protocols may use different labels than template enums. Map by meaning, not by exact string.
- **Over-inclusion**: Do not add enum values for findings that are absent or not supported by the data. The evaluator penalizes false positives.
- **Medication allergies**: When a patient has active allergies to a drug class, the medication plan must avoid that class and list it in avoid_allergens.
- **Pediatric driving restrictions**: Evaluate age-appropriateness; driving restrictions may not apply to patients below driving age.
- **Referral over-selection**: Include only referrals triggered by protocol rules or clearly supported findings. Adding unsupported referrals reduces the score.

### 8. Build and Validate the Answer
- Include every required top-level key from the answer template.
- Use null only where the field specification explicitly permits it.
- Use controlled enum values for all scored status and action fields — never free-text prose.
- For numeric fields, match the template's precision (e.g., one decimal place for mmol/L, two decimal places for risk scores).
- For timestamps, use ISO-8601 UTC with trailing Z.
- Do not include extra top-level keys, markdown, comments, or explanatory text outside the JSON object.
