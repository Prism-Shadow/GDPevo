---
name: clinic-protocol-json
description: Use for synthetic clinic tasks that require protocol-bound clinical decision-support JSON from a runtime environment, especially respiratory/CAP, pediatric head injury, potassium repletion, care-management routing, and observation-window retrieval cases.
---

# Clinic Protocol JSON

Use this skill when the user asks for a structured JSON answer for a synthetic clinic case using a runtime environment and an `answer_template.json`.

## Core Workflow

1. Read the user prompt and the full `input/payloads/answer_template.json`. The template is the output contract; preserve required keys, enum spellings, nullability, numeric precision, and ordering rules.
2. Read `environment_access.md` for the base URL and allowed endpoints. Use only those endpoints. Do not mutate the environment or place orders.
3. Extract the target `case_id` and `task_id`. Fetch `GET /api/cases/{case_id}` first; it usually returns the case, patient, findings, observations, medications, allergies, problems, imaging, care registry, and SDOH facts.
4. Fetch `GET /api/protocols` and the protocol matching the case type or prompt. Use aggregate endpoints only when the case detail is incomplete.
5. Build the answer from source data and protocol rules, not from prior examples. Include only stable identifiers that support selected facts.
6. Return exactly one JSON object. No markdown, comments, prose, or extra top-level keys.

Useful protocol mapping:

| Case type / prompt | Protocol |
| --- | --- |
| adult respiratory infection, CAP | `RESP-CAP-2026` |
| pediatric head injury, concussion triage | `PEDS-HEAD-2026` |
| potassium replacement / repletion | `K-REPLETION-2026` |
| care-management routing | `CM-HIGH-RISK-2026` |
| observation window / protocol gate | `OBS-WINDOW-2026` |

## Source Handling Rules

- Treat observations as authoritative only when `status` is `final`, unless the template or protocol explicitly says otherwise.
- For observation-window tasks, filter by target patient, target code, status, and `from <= effective_time < to`. Sort matches by `effective_time` ascending, then identifier ascending when requested.
- Exclude `preliminary`, `entered-in-error`, and `canceled` observations from positive protocol decisions. List them as exclusions only when the template asks for excluded distractors.
- Prefer case-specific bundled data from `/api/cases/{case_id}` over broad endpoint lists because broad lists include distractors.
- Use active medications, active allergies, and active problems unless the task asks for historical context.
- Evidence IDs should be identifiers for facts actually used. Follow template ordering; if no rule exists, put the case ID first, then observations/imaging/protocol sources by relevance.
- Set safety-check booleans to `true` only when the answer avoids the unsupported claim named by that check. Do not claim absent findings unless the record explicitly documents absence or a protocol permits the inference.

## Respiratory / CAP

Use final vitals, respiratory tests, imaging, active allergies, active respiratory problems, and the respiratory protocol.

- Assess community-acquired pneumonia when the record has focal consolidation/infiltrate or a pneumonia-compatible final CXR impression plus respiratory symptoms.
- Assess viral URI/supportive care when protocol evidence does not support pneumonia and bacterial treatment is not indicated.
- Escalate to ED when protocol triggers are present: room-air oxygen saturation below the protocol threshold, respiratory rate at or above the protocol threshold, hypotension, confusion, sepsis concern, immunocompromise, or multilobar disease.
- Use outpatient close follow-up for pneumonia without ED triggers; use the protocol follow-up interval.
- Red flags should reflect documented facts: borderline hypoxemia, severe hypoxemia, pleuritic chest pain, respiratory distress, confusion, hemoptysis, persistent fever, or worsening shortness of breath.
- Recommended tests should be protocol-indicated and case-supported: chest x-ray, viral PCR, pulse-ox recheck, and basic CBC only when indicated by the case/template.
- Medication strategy must respect active allergy classes. Avoid beta-lactam/penicillin, sulfonamide, macrolide, or tetracycline classes when active allergies implicate them. For ED disposition, defer antibiotic selection to ED if the template supports that strategy. For outpatient CAP, use the protocol-supported outpatient antibiotic strategy and populate drug details from case/protocol/order information; if none is supplied, rely on standard adult outpatient CAP conventions without inventing an allergy conflict.
- Stabilization actions are only for immediate needs such as supplemental oxygen or urgent ED transfer.
- Return precautions should cover worsening dyspnea/shortness of breath, hypoxia, confusion, persistent fever, chest pain, hemoptysis when available in the template.

## Pediatric Head Injury

Use final neurologic observations, history findings, the head-injury protocol, and the template's red-flag vocabulary.

- High risk / ED route: repeated vomiting, worsening severe headache, seizure, basilar skull signs, focal neurologic deficit, GCS below 15, prolonged loss of consciousness, or other urgent route trigger from protocol.
- Intermediate risk: concussion or mild TBI features without urgent triggers, such as head impact with nausea, headache, brief symptoms, or mild coordination abnormality without focal weakness.
- Low risk: minor head injury with normal exam and no concussion features.
- Imaging recommendation should match risk: no immediate CT for non-urgent low/intermediate clinic observation; CT/ED consideration or urgent CT for urgent triggers.
- `red_flags` are present findings only. `absent_red_flags` should include only explicitly negated urgent features, such as no loss of consciousness, no repeated vomiting, no seizure, or no focal weakness.
- Restrictions generally include short cognitive/physical rest, return-to-learn accommodations, no high-risk sports until cleared, and symptom-appropriate driving restriction. Use stricter clearance wording for ED/high-risk or provider-clearance scenarios.
- Use the protocol follow-up interval: later follow-up for stable outpatient mild TBI, earlier/ED route for urgent triggers.

## Potassium Repletion

Use final serum potassium observations with code `K`, final eGFR observations, ECG findings, symptoms, medications, active renal problems, and the potassium protocol.

- Ignore whole-blood potassium and preliminary potassium results for serum-potassium protocol decisions unless the template explicitly asks to list exclusions.
- Choose the latest final serum potassium by `effective_time`.
- Replacement is needed when latest final serum potassium is below the protocol target and no urgent/contraindication branch applies.
- Urgent branch applies for potassium below the protocol urgent threshold, dialysis-dependent ESRD, severe renal contraindication, ECG abnormality, or arrhythmia-concern symptoms such as palpitations, syncope, or severe weakness.
- Routine oral dose follows the protocol rule: difference below target times the per-0.1 mmol/L dose increment, rounded to the nearest protocol dose increment.
- For routine replacement, use the protocol's oral potassium medication code and route/frequency/status values when the template asks for an order-ready recommendation.
- For no replacement, urgent escalation, or contraindication hold, set nullable medication and dose fields to `null` where allowed and use the template's defer/not-recommended status.
- Schedule follow-up serum potassium for the next morning when routine replacement applies, using case/protocol timing if provided; otherwise use a conventional morning UTC timestamp after the review time.
- Contraindication booleans must come from active problems, case findings, and renal-function observations.

## Care-Management Routing

Use care registry, active problems, final labs/vitals, active medication count, SDOH, member-call findings, and the care-management protocol.

- High risk generally requires predictive risk at or above the protocol threshold plus complex-care triggers such as at least three chronic conditions, recent admission, dialysis/advanced CKD, heart failure, or uncontrolled diabetes.
- Route to complex care when high-risk complex-care triggers are present; route to routine case management for lower-risk cases with needs; use not eligible only when the protocol criteria are absent.
- Map priority problems from active diagnoses, abnormal observations, registry fields, medication burden, and member-disclosed barriers. Do not include a code unless a source fact supports it.
- Numeric anchors should come directly from registry, final labs/vitals, or active medication counts. Format blood pressure as systolic/diastolic when both are available.
- Referrals: pharmacist for polypharmacy, insulin safety, or high-risk electrolyte/diuretic regimens; social worker for multiple moderate/severe social domains; dialysis care coordination for dialysis; transportation benefits for transportation barriers; behavioral health monitoring for positive behavioral health screens or protocol triggers.
- Outreach should be permission-based plain language when the member is reluctant, wants control over contact, or protocol requires permission. Use standard scripted outreach only when no preference/reluctance is documented.
- Care plan minima for complex cases should include multiple prioritized problems, weekly initial follow-up, member-stated priority, medication reconciliation, barrier work, escalation conditions, and at least two disciplines when the template asks numerically.
- Separate source provenance into chart-derived facts and member-disclosed facts. Transportation, financial/food/medication barriers, dialysis fatigue, and care-goal preference usually require member disclosure.

## Observation-Window Tasks

Use case findings to identify the target code, target patient, inclusive window start, exclusive window end, and protocol gate.

- Matching observations must satisfy patient, code, final status, and time window.
- Excluded observations are relevant distractors from the case review that fail because of date, target code, or status. Include wrong-patient observations only if the template explicitly asks for them.
- `latest_final` is the latest qualifying match when any exists; otherwise it is `null` if the template allows it.
- For potassium windows, apply the potassium gate vocabulary from the template: recent final normal when the latest final is at or above target, low repletion needed when below target but not urgent, critical/urgent when below urgent threshold, and no final lab when no qualifying observation exists.
- For respiratory or imaging windows, use the same filter mechanics and map the downstream gate to the template/protocol vocabulary rather than inventing a potassium-specific result.
- Repeat-lab or repeat-test timing must come from the case/protocol/template. If a repeat is recommended and no exact time is provided, use the next reasonable clinic-morning timestamp after the review or window end.

## Final Checks

- Validate every enum against the template before responding.
- Confirm each selected ID exists in the fetched case or protocol data.
- Confirm numeric precision: integer hours/days/counts, one-decimal lab values, two-decimal risk probabilities when requested.
- Confirm no unsupported normal findings, no contradicted allergy medication, and no use of preliminary/canceled/entered-in-error data for positive decisions.
