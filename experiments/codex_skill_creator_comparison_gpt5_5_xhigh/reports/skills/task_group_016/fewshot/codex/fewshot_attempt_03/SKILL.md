---
name: synthetic-clinic-protocol-json
description: Build protocol-bound JSON answers for synthetic clinic runtime tasks. Use when a prompt asks Codex to query a clinic task environment and return a structured answer_template JSON for cases involving FHIR-like patients, cases, observations, medications, allergies, problems, imaging, SDOH, care registry, respiratory CAP assessment, pediatric head injury triage, potassium replacement, observation-window gates, or care-management routing.
---

# Synthetic Clinic Protocol JSON

## Core Workflow

1. Read the task prompt, `environment_access.md`, and `input/payloads/answer_template.json` completely.
2. Extract the base URL, target `case_id`, `task_id`, and any explicit observation window, target code, or protocol name from the prompt/template.
3. Fetch the case bundle first:

```bash
python scripts/fetch_clinic_bundle.py --base-url "$TASK_ENV_BASE_URL" --case-id "$CASE_ID"
```

The bundle endpoint usually contains `case`, `patient`, `findings`, `observations`, `medications`, `allergies`, `problems`, `imaging`, `sdoh`, and `care_registry`. If a field is absent or looks incomplete, cross-check the allowed list endpoints and filter by `case_id` and `patient_id`.
4. Fetch `/api/protocols` and the protocol matching `case.case_type`. Use `--all-protocols` with the helper when useful.
5. Derive every output field from the template's allowed values, the fetched case data, and the protocol. Return exactly one JSON object with no markdown, comments, narrative, or extra keys.

## Runtime Rules

- Prefer `GET /api/cases/{case_id}` over scanning global lists.
- Treat `patient_id` as a hard filter. Do not count a same-case observation for a different patient unless the template explicitly asks for wrong-patient exclusions.
- Use only authoritative observation statuses from the protocol, usually `final`. Exclude `preliminary`, `entered-in-error`, and `canceled` from satisfying gates.
- Match observation codes exactly unless the prompt/protocol explicitly allows aliases. For serum potassium, code `K` is serum/plasma; code `6298-4` is whole blood and is normally excluded from serum potassium logic.
- Use `findings` for narrative facts, absence statements, current review time, protocol windows, and provenance source ids. Use observations/imaging/registry/problems/SDOH for objective anchors.
- Make safety-check booleans true only after verifying the unsupported claim is not present in the answer. Do not infer absent red flags unless the case explicitly says absent or an objective observation proves absence.
- For set-like arrays, omit duplicates. If the template gives ordering, follow it. Otherwise use a stable order with the case id first when requested, then clinical source ids by relevance.
- Use `null` only when the template permits it. Preserve numeric precision requested by the template.

## Protocol Selection

Use these runtime protocol ids by `case_type`:

- `acute_respiratory`: `RESP-CAP-2026`
- `pediatric_head_injury`: `PEDS-HEAD-2026`
- `potassium_repletion`: `K-REPLETION-2026`
- `care_management`: `CM-HIGH-RISK-2026`
- `observation_window`: `OBS-WINDOW-2026`

## Respiratory CAP Pattern

- Diagnose community-acquired pneumonia when respiratory symptoms are paired with focal consolidation or abnormal CXR evidence. Use viral URI/supportive care when pneumonia evidence is absent and viral features dominate. Use pending only when the necessary pneumonia protocol evidence is not yet final.
- Escalate to ED when room-air SpO2 is below 90, respiratory rate is at least 30, systolic BP is below 90, or findings show confusion, sepsis concern, immunocompromise, or multilobar disease.
- Map red flags from evidence: SpO2 92-93 percent to `hypoxemia_92_93`, below 90 to `hypoxemia_below_90`, plus documented pleuritic chest pain, respiratory distress, confusion, hemoptysis, persistent fever, or worsening dyspnea.
- Include diagnostic tests that are protocol-relevant or still recommended: CXR, respiratory viral PCR, pulse-ox recheck, and CBC/basic labs when severity or uncertainty warrants them.
- Apply active allergies before choosing medication. For outpatient CAP with beta-lactam/sulfonamide constraints and no tetracycline allergy, doxycycline 100 mg PO BID for 5 days is the usual allergy-aware strategy. For ED escalation, defer antibiotic selection to the ED and use null medication details where allowed. For viral URI, use supportive care with no antibiotic.
- Stabilization actions are empty for outpatient close follow-up unless urgent oxygen/ED criteria are met.
- For outpatient pneumonia return precautions, map protocol language to template enums: worsening dyspnea to `worsening_shortness_of_breath`, oxygen below threshold to `hypoxia`, plus chest pain, confusion, persistent fever, and hemoptysis when the template includes those standard warning codes.

## Pediatric Head Injury Pattern

- Use urgent-route triggers from `PEDS-HEAD-2026`: repeated vomiting, worsening severe headache, seizure, basilar skull signs, focal neurologic deficit, GCS below 15, or prolonged loss of consciousness.
- Use mild TBI/concussion when there is head impact with symptoms, GCS 15, normal or near-normal neurologic exam, and no urgent trigger. Use minor head injury without concussion features when symptoms are absent/minimal and no concussion signs are supported.
- Choose `no_immediate_ct` for stable low/intermediate cases without urgent triggers. Use `ct_or_ed_per_protocol` or `urgent_ct` when urgent triggers or severe injury findings are present.
- Present red flags should be directly supported. Absent red flags should include only explicitly denied or objectively absent items.
- Apply restrictions from protocol: relative cognitive/physical rest, return-to-learn accommodations, no high-risk sports until cleared, and driving restriction while symptomatic. Use stricter driving clearance for more severe/ED cases.
- Use 24-hour follow-up for higher concern outpatient cases, 48-hour follow-up for stable intermediate cases, and emergency department route for urgent triggers.

## Potassium Replacement Pattern

- Use the latest eligible final serum potassium observation (`code: K`) at or before the review time unless the template defines a different window.
- Screen urgent branch before routine dosing. Urgent triggers include potassium below 3.0 mmol/L, dialysis-dependent ESRD, severe renal contraindication, ECG abnormality, or symptoms such as palpitations, syncope, or weakness with arrhythmia concern.
- If urgent branch applies, use urgent escalation/defer-to-urgent-clinician fields, null routine dose, and urgent actions in clinical sequence: clinician notification, ECG now, telemetry or ED evaluation when supported.
- If no urgent branch and potassium is below the target 3.5 mmol/L, use routine oral repletion. Dose is 10 mEq for each 0.1 mmol/L below target, rounded to the nearest 10 mEq. Use potassium chloride oral with the protocol NDC, PO route, and once frequency unless the template/protocol states otherwise.
- If potassium is at or above target, choose no replacement and null medication/follow-up fields where permitted.
- For routine replacement, schedule the follow-up serum potassium (`2823-3`) the next morning; when no exact time is supplied, use 08:00:00Z on the next calendar day after `current_time`.
- Populate contraindications from problems, findings, care registry, ECG observations, symptom findings, and latest final eGFR (`33914-3`).

## Observation Window Pattern

- Extract `window.from`, `window.to`, and `target_code` from findings, prompt, protocol, or template. Treat the start as inclusive and the end as exclusive.
- Matched observations must have the target patient id, exact target code, `status: final`, and `from <= effective_time < to`.
- Excluded observations are relevant target-patient distractors from the case review that fail because of date, code, or status. Sort matched and excluded ids by `effective_time` ascending, then `observation_id` ascending.
- `latest_final` is the matched final observation with the latest effective time, or null when there is no match.
- For serum potassium gates: final value at or above 3.5 satisfies recent final normal; 3.0-3.4 means low repletion is needed; below 3.0 means critical/urgent; no match means no final lab in window.
- Recommend repeat lab when no final lab is found or the protocol gate requires recheck. Do not recommend repeat lab when a recent final normal result satisfies the gate.

## Care-Management Routing Pattern

- Use registry risk score, chronic condition count, recent admission, dialysis/advanced CKD, heart failure, uncontrolled diabetes, medication count, SDOH, and findings.
- Risk is high when predictive risk is at least 0.75 or multiple complex-care triggers are present. Route high-risk complex cases to complex care management; route lower-risk cases according to the template enums and protocol support.
- Map priority problems from active problems, observations, registry, and findings: uncontrolled diabetes, ESRD/hemodialysis, CKD stage 4, heart failure/recent admission or HFpEF volume overload, hyperphosphatemia, hypertension, polypharmacy, transportation/financial/food barriers, dialysis fatigue, and behavioral health needs.
- Numeric anchors should come from objective sources: risk score and medication count from registry, HbA1c and phosphorus from final labs, blood pressure from paired systolic/diastolic final vitals.
- Add pharmacist referral for active medication count at least 10, insulin safety issues, or high-risk diuretic/electrolyte regimens. Add social work when at least two moderate/severe social domains are present. Add dialysis care coordination, transportation benefits, primary care, or behavioral health monitoring only when supported.
- Use permission-based plain-language outreach when the member is reluctant, refusing, or requires consent-sensitive contact.
- For complex care plans, require at least 3 problems, weekly initial follow-up, member-stated priority, and at least 2 disciplines.
- Escalation conditions should be supported by the chart or disclosure; common mappings include missed dialysis/volume overload, dyspnea/weight gain/ED return, PHQ-9 worsening or item 9 positive, severe glucose events, hypertensive urgency, and medication access failure.
- For source provenance, put objective registry/observation/problem facts in `chart_facts`; put barriers, fatigue, medication access, and care-goal preference facts in member-disclosure arrays only when disclosure is needed or member-reported.

## Final JSON Check

Before final output, compare against `answer_template.json`:

- All required top-level keys are present and no prohibited keys are present.
- Every enum value is copied exactly from the template.
- Arrays use the required ordering or a stable set order.
- Evidence ids point to the specific case, observation, imaging, registry, finding source, or protocol records actually used.
- Safety booleans match the answer content and do not hide unsupported claims.
