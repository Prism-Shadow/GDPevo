# Protocol Workflow Reference

This reference captures reusable patterns for synthetic clinic protocol JSON tasks. It intentionally avoids case-specific answer values.

## Evidence Collection

Start from the target case id. A useful case bundle usually contains:

- `case`: case id, case type, patient id, service date, summary, status.
- `patient`: demographics and stable patient id.
- `findings`: narrative or keyed facts with `source_id`.
- `observations`: FHIR-like records with `observation_id`, `patient_id`, `case_id`, `code`, `display`, `status`, `effective_time`, `value_number`, `value_text`, and `interpretation`.
- `imaging`: imaging ids, studies, impressions, status, and performed time.
- `medications`: active medication list and codes.
- `allergies`: allergen, reaction, patient id, and active/inactive status.
- `problems`: problem names/codes and active status.
- `care_registry` and `sdoh`: registry risk, utilization, care-management hints, and member-disclosed social barriers.

When broad list endpoints are needed, filter back to the target `case_id` and `patient_id`. Treat records for another patient, another code, an excluded status, or an out-of-window timestamp as non-matching even when they look clinically related.

## Protocol Binding

Select protocols by matching case type and prompt intent to protocol title/scope and controlled codes. The protocol is the authoritative rule set. Outside clinical knowledge can help interpret common terms, but it must not override synthetic protocol thresholds, controlled codes, statuses, or follow-up timing.

Use protocol ids and controlled codes as evidence when the template asks for source provenance. Use source ids from case findings or clinical records when the output field depends on a patient-specific fact.

## Respiratory Infection And CAP

Useful evidence:

- Chest imaging status and impression.
- Oxygen saturation, respiratory rate, systolic blood pressure, temperature, viral PCR, and pulse-ox recheck observations.
- Symptoms and red flags from findings.
- Active allergies and active medications.

Reusable rules:

- A final focal consolidation supports community-acquired pneumonia when symptoms fit.
- ED transfer is driven by protocol thresholds such as severe hypoxemia, very high respiratory rate, hypotension, confusion, sepsis concern, immunocompromise, or multilobar disease.
- Borderline oxygen saturation or pleuritic pain can raise risk without automatically requiring ED transfer when urgent thresholds are absent.
- Antibiotic plans must be allergy-aware. Use active allergies only, and avoid medication classes implicated by those allergies.
- Safety booleans should confirm that the answer avoided unsupported claims, such as calling an abnormal chest x-ray normal or claiming clear lungs without evidence.

## Pediatric Head Injury

Useful evidence:

- Mechanism, helmet use, loss of consciousness, vomiting count, headache course, nausea, photophobia, seizure, basilar skull signs, focal neurologic deficit, GCS, and neurologic exam.
- Final exam observations and keyed findings with explicit absent/present statements.

Reusable rules:

- Urgent route or CT consideration follows protocol triggers such as repeated vomiting, worsening severe headache, seizure, basilar skull signs, focal neurologic deficit, GCS below normal, or prolonged loss of consciousness.
- Mild traumatic brain injury can be supported by symptoms with normal or near-normal neurologic findings and no urgent trigger.
- Stable symptoms with no urgent trigger generally support home observation with close follow-up rather than immediate CT.
- Restrictions should map protocol text to template enum values for cognitive/physical rest, return-to-learn, sports clearance, and driving avoidance while symptomatic or impaired.
- Put explicitly present findings in `red_flags` and explicitly absent urgent findings in `absent_red_flags`. Do not infer absent negatives from silence.

## Potassium Replacement

Useful evidence:

- Final serum potassium observations, excluding preliminary results and non-serum potassium codes when the task asks for serum potassium.
- Current clinical review time from case findings.
- ECG observations, symptoms, dialysis or ESRD problem status, eGFR/renal function, and active medications that affect potassium.
- Protocol controlled codes for serum potassium, eGFR, ECG summary, follow-up lab, and medication identifiers.

Reusable rules:

- Choose the latest eligible final serum potassium by `effective_time`; break ties deterministically by id if needed.
- Urgent escalation takes precedence over routine replacement when protocol urgent triggers are present, such as very low potassium, dialysis-dependent ESRD, abnormal ECG, severe renal contraindication, or arrhythmia-concern symptoms.
- Routine oral replacement applies only when the urgent branch is false and potassium is below the protocol target.
- Dose calculations should follow the protocol formula and rounding rule, then populate medication order fields from protocol-controlled medication details.
- If no replacement is needed, use `null` only for medication and lab fields that permit it, and set status/action enums to their controlled no-treatment values.
- Follow-up lab timing should be derived from the protocol and case clock. If the protocol gives a relative time, anchor it to the runtime clinical review time rather than the current real-world date.

## Care-Management Routing

Useful evidence:

- Registry risk score, chronic condition count, recent admission, dialysis schedule, medication count, and program hints.
- Active problems for ESRD/advanced CKD, heart failure, diabetes, hypertension, hyperphosphatemia, and related conditions.
- Observations for A1c, phosphorus, blood pressure, PHQ-9, and other numeric anchors.
- Active medications and SDOH/member-disclosed barriers.

Reusable rules:

- High predictive risk plus multiple supporting triggers points to complex care management when the protocol threshold is met.
- Priority problems should be selected from active problems, abnormal numeric anchors, polypharmacy, dialysis/volume-overload facts, and member-disclosed barriers.
- Pharmacist referral is supported by polypharmacy, insulin safety, or high-risk electrolyte/diuretic regimens.
- Social-worker or transportation referrals require member-disclosed or care-management evidence, not just assumptions.
- Use permission-based outreach when the protocol or member context indicates reluctance, preference-sensitive contact, or a need for plain-language engagement.
- Split source provenance between chart facts and member-disclosed facts according to the template.

## Observation Window Tasks

Useful evidence:

- Target patient id, target code, inclusive start timestamp, exclusive end timestamp, and status rule from the case findings or protocol.
- All observations that are plausible matches or distractors for the case.

Reusable rules:

- A matching observation must have the target patient, target code, eligible status, and `effective_time` within `[window_start, window_end)`.
- Exclude relevant distractors for wrong date, wrong code, wrong status, or wrong patient according to the template's requested exclusion semantics.
- Sort matched observations by `effective_time` ascending, then id ascending, unless the template says otherwise.
- Select the latest final from matched observations for downstream protocol gates.
- Gate values should reflect the protocol: no final lab in window, recent final normal, recent final low requiring repletion, or critical/urgent.
- Repeat-lab recommendations should follow the gate and protocol timing, using `null` for scheduled time only when no repeat is recommended or the template permits it.

## Final Assembly Checklist

Before final response:

- Required keys are present and no unsupported extra keys are included.
- Enum strings exactly match the template.
- Every included clinical decision has source evidence.
- No excluded observation was accidentally used as a match.
- Latest means latest among eligible records, not simply the last record returned by the API.
- Safety checks are true only when the answer actually avoided the unsupported claim.
- The final message contains only the JSON object.
