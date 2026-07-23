---
name: synthetic-clinic-protocol-json
description: Complete protocol-bound synthetic clinic decision-support tasks that require querying a local clinic runtime and returning an exact JSON object. Use for respiratory/CAP assessment, pediatric head-injury triage, potassium replacement support, care-management routing, and observation-window or lab-gate tasks when prompts provide environment_access.md plus an answer_template.json schema.
---

# Synthetic Clinic Protocol JSON

## Core Workflow

1. Read the task prompt, `environment_access.md`, and the full `input/payloads/answer_template.json` before querying or answering.
2. Extract the target `case_id`, expected `task_id`, required top-level keys, allowed enum values, required nested keys, numeric precision, ordering rules, and nullability rules.
3. Use only the runtime base URL and endpoints listed in `environment_access.md`. Do not use external web sources. Do not mutate the runtime or place orders; treat any POST endpoint as read-only querying support only if the environment documents it as safe.
4. Retrieve `GET /api/cases/{case_id}` first. It usually bundles the case, patient, findings, observations, imaging, allergies, medications, problems, care registry, and SDOH records. Use list endpoints only to resolve missing context or compare distractors.
5. Retrieve the matching protocol with `GET /api/protocols/{protocol_id}`. Map case types as:
   - `acute_respiratory` -> `RESP-CAP-2026`
   - `pediatric_head_injury` -> `PEDS-HEAD-2026`
   - `potassium_repletion` -> `K-REPLETION-2026`
   - `care_management` -> `CM-HIGH-RISK-2026`
   - `observation_window` -> `OBS-WINDOW-2026`
6. Build a private evidence table: source id, patient id, case id, fact, value/time/status, and whether it supports or excludes a schema field. Prefer stable identifiers such as case ids, visit/source ids, observation ids, imaging ids, registry ids, medication ids, allergy ids, and protocol ids.
7. Fill the JSON from evidence and protocol rules only. Never hard-code values from earlier tasks. Never include narrative text, markdown, comments, or extra top-level keys unless the template explicitly permits them.
8. Validate the final object against the answer template: required keys present, enums exact, booleans meaningful, arrays de-duplicated, ordering followed, nulls used only where allowed, and numeric/time precision preserved.

## Evidence Rules

- Filter clinical records to the target `patient_id` and `case_id` unless the task explicitly asks for excluded or distractor records.
- Treat `status: "final"` as authoritative when the protocol names final statuses. Exclude preliminary, canceled, entered-in-error, wrong-code, wrong-patient, and out-of-window observations from positive matches.
- Use `current_time` from case findings or task runtime evidence, not the system clock.
- Use active allergies only for medication avoidance; inactive allergies do not drive avoidance unless the template says otherwise.
- Do not infer normal findings from silence. Mark a safety check true only when the response avoids the unsupported claim named by that check.
- Use the template's exact wording for controlled outputs. Translate clinical facts into allowed enum codes rather than prose.
- For evidence ids, include the records that directly determine the decision. Use a stable order when requested; otherwise keep a logical source order such as case/visit, key observations, imaging, registry, protocol.

## Case-Type Playbooks

### Adult Respiratory / CAP

- Review symptoms, oxygen saturation, respiratory rate, blood pressure, temperature, viral PCR, chest imaging, active problems, active allergies, and respiratory protocol thresholds.
- Use protocol controlled codes for CXR, viral PCR, pulse-ox recheck, CBC/basic labs, oxygen saturation, respiratory rate, and temperature.
- Escalate to ED-level disposition when protocol urgent thresholds or red flags are present, such as oxygen saturation below the stated threshold, respiratory distress, confusion/sepsis concern, hypotension, immunocompromise, or multilobar disease.
- Borderline hypoxemia, pleuritic chest pain, persistent fever, or worsening dyspnea can be red flags without necessarily meeting urgent-transfer criteria; tie risk and disposition to the protocol threshold and total picture.
- Select allergy-aware antibiotics. Avoid active allergy classes and do not recommend beta-lactams, sulfonamides, macrolides, or tetracyclines when the active allergy evidence implicates that class. If urgent transfer is indicated, defer antibiotic selection when the schema provides that option.
- Do not claim a normal chest x-ray or clear lungs unless the record directly supports that claim.

### Pediatric Head Injury

- Review mechanism, age, GCS, loss of consciousness, vomiting count, seizure, headache trajectory, basilar skull signs, focal neurologic findings, coordination findings, photophobia, and protocol urgent triggers.
- Separate present red flags from absent red flags. Include absent values only when the chart explicitly says they are absent or a final observation proves absence.
- Use urgent CT or ED evaluation when protocol urgent-route triggers are present. Otherwise choose no immediate CT or observation/follow-up options supported by the template and protocol.
- Apply concussion restrictions when symptoms or exam findings support mild TBI: cognitive/physical rest, return-to-learn accommodations, no high-risk sports until cleared, and driving restriction while symptomatic or until cleared as the template allows.
- Keep safety booleans aligned with unsupported-claim avoidance, especially false loss of consciousness, vomiting, or photophobia.

### Potassium Replacement Support

- Identify the latest eligible final serum potassium observation using protocol code `K`; do not use preliminary results or whole-blood potassium codes as the serum value.
- Screen urgent branch before routine replacement: dialysis-dependent ESRD, severe renal contraindication, abnormal ECG, potassium below the urgent threshold, or symptoms such as palpitations, syncope, or weakness with arrhythmia concern.
- If urgent branch is true, use urgent escalation actions and defer medication details when the schema provides defer/null options.
- If nonurgent serum potassium is below the protocol target, compute routine oral replacement from the protocol dose rule: deficit below target divided by 0.1 mmol/L, multiplied by the mEq-per-step value, rounded as specified. Use the protocol's medication code/NDC, route, frequency, and follow-up lab code.
- If no replacement is needed or contraindicated, set dose/order/lab fields to null only where the schema permits and choose the corresponding controlled plan/status.
- Capture contraindications from problems, registry, symptoms, ECG observation, eGFR observation, dialysis status, and case findings.

### Care-Management Routing

- Combine case, registry, active problems, final observations, active medication count, SDOH records, and protocol routing triggers.
- Use high predictive risk, multiple chronic conditions, recent admission, dialysis/advanced CKD, heart failure, uncontrolled diabetes, and protocol thresholds to choose risk tier and program.
- Translate clinical/social facts into allowed priority problem codes, referral codes, and escalation condition codes. De-duplicate arrays.
- Use pharmacist referral triggers for polypharmacy, insulin safety, and high-risk diuretic/electrolyte regimens. Use social-work or transportation/benefit referrals for qualifying social domains.
- Use permission-based plain-language outreach when the member is reluctant, refusing, or requests contact boundaries.
- Separate `source_provenance.chart_facts` from `member_disclosure_needed`: chart facts come from records/registry/observations; member disclosure covers barriers, fatigue, access issues, and preferences that require or came from member report.
- Preserve numeric anchors exactly with requested precision, including risk score, A1c, phosphorus, blood pressure, and medication count.

### Observation Window / Lab Gate

- Extract target patient, target code, inclusive window start, and exclusive window end from case findings, prompt, template, or protocol.
- A positive match requires the target patient, target code, final status, and effective time within `[from, to)`.
- Sort matched observations by effective time ascending, then observation id ascending. Sort excluded relevant distractors by effective time ascending when available, then observation id ascending.
- Include relevant exclusions for wrong date, wrong code, wrong status, or wrong patient when they are part of the case review.
- Choose `latest_final` as the latest matched final observation, or null only when the template allows and no match exists.
- Set the protocol gate from the latest eligible result and protocol thresholds: recent normal satisfies the gate, low results route to repletion, critical/urgent results route to urgent handling, and no final in-window lab routes to repeat-lab recommendation.

## Final JSON Checklist

- Required top-level keys match the template exactly.
- Nested required keys are present even when values are null.
- All enum strings are copied exactly from the template.
- Lists contain no duplicates and obey any stated ordering.
- Times are ISO-8601 UTC with trailing `Z` when required.
- Numeric values use requested precision and units are not embedded unless the schema expects strings.
- `null` appears only in fields whose type permits null.
- Evidence ids support every major decision and do not include unrelated distractors unless the field asks for excluded evidence.
