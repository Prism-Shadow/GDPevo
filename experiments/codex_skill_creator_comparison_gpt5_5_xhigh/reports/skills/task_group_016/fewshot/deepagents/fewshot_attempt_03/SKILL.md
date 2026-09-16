---
name: synthetic-clinic-protocol-json
description: Solve synthetic clinic runtime tasks that require reviewing FHIR-like case data, protocol materials, and answer_template.json to return exact protocol-bound clinical decision-support JSON. Use for respiratory CAP assessment, pediatric head injury triage, potassium repletion, care-management routing, and observation-window protocol gate tasks against the allowed clinic API.
---

# Synthetic Clinic Protocol JSON

## Core Workflow

1. Read the user prompt and `input/payloads/answer_template.json` first. Treat the template as the output contract: required keys, enum spellings, nullability, numeric precision, and ordering rules override all heuristics below.
2. Resolve the runtime base URL from the task environment access file or from the prompt placeholder. Do not call external medical references; use only the runtime records, runtime protocols, prompt, and template.
3. Fetch the target case bundle before list endpoints:

   ```bash
   python skill/scripts/collect_context.py --base-url "$TASK_ENV_BASE_URL" --case-id "$CASE_ID"
   ```

   The script returns the `/api/cases/{case_id}` bundle plus the matching protocol for known synthetic case types.
4. If a bundle is incomplete, use the allowed GET endpoints and filter locally by both `case_id` and `patient_id`. Never use non-target cases to fill target fields.
5. Build the answer from source facts. Use stable IDs from case records, observations, imaging, registry entries, or protocol identifiers in `evidence_ids`; do not invent evidence IDs.
6. Return exactly one JSON object. Do not include markdown, comments, explanatory prose, extra top-level keys, or unavailable nulls.

## Runtime Data Rules

- Use `status: "final"` observations as authoritative unless the template explicitly asks for excluded or non-final observations.
- For observation matching, require the target `patient_id`. Also require the target `case_id` when case-scoped observations are supplied.
- Prefer coded fields over display text. Use protocol `controlled_codes` when present.
- Use case `findings` for current time, explicit symptoms, explicit absences, search windows, target codes, outreach posture, and other facts that may not be represented as observations.
- Use active allergies only. Inactive allergies can explain history but should not restrict medication plans unless the protocol or template says otherwise.
- Sort arrays only when the template says to sort. Otherwise sets may be returned in any stable, nonduplicated order.
- Round numeric fields to the precision required by the template, not by the raw API payload.

## Protocol Selection

Map `case.case_type` to protocol when the case does not name a protocol directly:

| case_type | protocol_id |
| --- | --- |
| `acute_respiratory` | `RESP-CAP-2026` |
| `pediatric_head_injury` | `PEDS-HEAD-2026` |
| `potassium_repletion` | `K-REPLETION-2026` |
| `care_management` | `CM-HIGH-RISK-2026` |
| `observation_window` | `OBS-WINDOW-2026` |

Always inspect the returned protocol body. The same answer template enum may appear in multiple tasks, but the protocol decides which branch is clinically supported.

## Respiratory CAP Tasks

Use adult respiratory case facts, vitals, imaging, allergies, medications, and `RESP-CAP-2026`.

- Assess `community_acquired_pneumonia` when infection symptoms plus final CXR/imaging show focal consolidation. Use `viral_upper_respiratory_infection` when protocol evidence supports viral illness without pneumonia. Use pending only when required diagnostic evidence is not final or not available.
- ED escalation applies for room-air oxygen saturation less than 90, respiratory rate at least 30, systolic BP less than 90, confusion, sepsis concern, immunocompromise, or multilobar disease. When escalated, disposition should be the ED option and stabilization actions should include urgent transfer and oxygen when supported by hypoxemia.
- Borderline hypoxemia around 92-93 percent and pleuritic chest pain are red flags but can still be outpatient close follow-up when ED triggers are absent.
- Recommended tests usually come from controlled codes: two-view CXR, respiratory viral PCR, pulse-ox recheck, and CBC/basic labs when protocol or case severity supports them. Include tests that are clinically relevant to the protocol even when final results are already present, if the template asks for recommended diagnostic tests.
- Medication strategy must avoid active allergy classes. For outpatient CAP with penicillin or sulfonamide allergy and no tetracycline allergy, use doxycycline outpatient fields (`doxycycline`, `100 mg`, `PO`, `BID`, `5`) unless the case protocol says otherwise. For ED escalation, defer antibiotic selection to ED. For viral URI, use supportive care with medication fields null if the template allows.
- Return precautions should use the template enum spellings. Map respiratory worsening and low oxygen language to the closest available enum values.
- Safety checks with names like `no_normal_cxr_claim` or `no_clear_lungs_claim` are true only when the answer avoids asserting those unsupported normal findings.

## Pediatric Head Injury Tasks

Use pediatric case findings, neuro observations, medications, and `PEDS-HEAD-2026`.

- Urgent route triggers are repeated vomiting, worsening severe headache, seizure, basilar skull signs, focal neurologic deficit, GCS below 15, or prolonged loss of consciousness. If any are present, choose the ED disposition and CT/urgent imaging branch allowed by the template.
- Mild TBI without loss of consciousness is supported by head impact plus symptoms such as nausea, headache, brief confusion, or mild coordination issues, with GCS 15 and no urgent trigger. This is typically intermediate risk, home observation with follow-up, and no immediate CT.
- Fill `red_flags` from present findings and observations using the template's enum names. Fill `absent_red_flags` only for high-risk findings explicitly documented absent; do not mark unmentioned findings absent.
- Restrictions for concussion features usually include relative cognitive/physical rest, return-to-learn accommodations, no high-risk sports until cleared, and no driving while symptomatic. Use `no_driving_until_cleared` instead of symptom-free when the case is routed to ED or has severe/high-risk features.
- Use 48-hour primary care or concussion follow-up for stable home observation unless the prompt/protocol supplies a shorter interval. For ED disposition, use the emergency route and the immediate or shortest template-compatible timing.
- Safety booleans such as `no_false_loc`, `no_false_vomiting`, and `no_false_photophobia` are true only if the answer does not claim those findings are present without support.

## Potassium Repletion Tasks

Use `K-REPLETION-2026`, serum potassium observations, eGFR, ECG summaries, symptoms, medications, and contraindication findings.

- The target serum potassium code is `K`. Do not use whole-blood potassium code `6298-4` as the latest serum potassium result.
- Select the latest eligible final serum potassium by `effective_time`; ignore preliminary, canceled, and entered-in-error observations for treatment decisions.
- Urgent branch applies for potassium less than 3.0 mmol/L, dialysis-dependent ESRD, ECG abnormality, severe renal contraindication, or symptoms such as palpitations, syncope, or weakness with arrhythmia concern.
- If urgent branch applies, use urgent escalation/defer-to-urgent-clinician fields, null oral dose, and urgent actions in clinical sequence: clinician notification, ECG now when not already adequately addressed, then telemetry or ED evaluation as supported by the template.
- If latest final serum potassium is at least the target 3.5 mmol/L, use no replacement, null medication/order fields where allowed, and no routine follow-up lab unless the protocol/template requests one.
- If below target and not urgent, use routine oral repletion. Dose rule: `(3.5 - latest_K) / 0.1 * 10 mEq`, rounded to the nearest 10 mEq. Use potassium chloride oral, NDC `40032-917-01`, route `PO`, frequency `once`, status `recommended`.
- Routine follow-up lab is next-morning final serum potassium. Use LOINC `2823-3`; when no exact time is supplied, schedule the next calendar morning at the clinic's evident morning lab time if available.
- Contraindication fields should reflect the record directly: dialysis-dependent from problems/registry, arrhythmia symptoms from findings, and eGFR from the latest final eGFR observation.

## Care-Management Routing Tasks

Use `CM-HIGH-RISK-2026`, the case bundle, registry data, active problems, final observations, medication count, SDOH, and member-call findings.

- High risk is supported by predictive risk at least 0.75 plus complex-care triggers such as at least 3 chronic conditions, recent admission, dialysis or advanced CKD, heart failure, or uncontrolled diabetes. Route high-risk qualifying cases to complex care management.
- Use routine case management when needs are present but high-risk/complex-care triggers are insufficient. Use not eligible only when protocol triggers are absent.
- Map priority problems from documented facts:
  - uncontrolled diabetes from high HbA1c or uncontrolled diabetes problem text.
  - ESRD on hemodialysis or CKD stage 4 from problem codes/text, dialysis schedule, registry, or eGFR.
  - heart-failure recent admission or HFpEF post-volume-overload from problem/admission facts.
  - hyperphosphatemia, hypertension, and polypharmacy from active problems, labs, BP, and medication count.
  - transportation, financial food/medication, dialysis fatigue, and behavioral health needs from SDOH and findings.
- Numeric anchors come from registry and final observations: risk score, HbA1c, phosphorus, blood pressure as systolic/diastolic string, and active medication count.
- Referral triggers: pharmacist for at least 10 active medications, insulin safety, or high-risk diuretic/electrolyte regimens; social worker for at least two moderate/severe social domains or financial/food barriers; transportation benefits for transportation barriers; dialysis care coordination for dialysis; behavioral health monitoring for relevant PHQ or behavioral findings.
- Use permission-based plain-language outreach when the member is reluctant, refusing, or the case explicitly calls for permission-based outreach. Otherwise use the standard outreach enum if available.
- Complex care-plan minima should include weekly initial contact, member-stated priority, multiple problem areas, and at least two disciplines when those fields exist.
- Source provenance separates chart/registry facts from member disclosures. Put SDOH barriers, fatigue, access barriers, and care-goal preferences under member disclosure when they come from calls, member reports, or SDOH records.

## Observation-Window Tasks

Use `OBS-WINDOW-2026`, case findings, and observations.

- Extract `window.from`, `window.to`, and `target_code` from case findings or prompt. Treat the start as inclusive and the end as exclusive unless the template says otherwise.
- `lab_found` is true only when at least one observation for the target patient has the target code, `status: "final"`, and an effective time inside the window.
- Sort matching observations by `effective_time` ascending, then `observation_id` ascending. `latest_final` is the last sorted match; use null only when `lab_found` is false and the template permits null.
- `excluded_observation_ids` should include reviewed observations for the target patient that are relevant but fail because of date, code, or status. Do not include wrong-patient observations unless the template explicitly asks for patient-mismatch exclusions.
- For potassium windows, choose protocol gates by latest final value: no final lab in window, recent final critical/urgent for less than 3.0, recent final low/repletion needed for 3.0 to less than 3.5, and recent final normal for at least 3.5.
- Repeat-lab recommendation follows the protocol gate and template: no repeat when the latest final satisfies the recent-normal gate; schedule per protocol when no final, low, or urgent gates require follow-up.

## Final JSON Checklist

- Required top-level keys exactly match the template.
- Enum values exactly match the template spelling, even when protocol wording differs.
- Nulls appear only in fields whose type allows null.
- Arrays contain no duplicates.
- Evidence IDs are source identifiers actually used for the decision.
- Safety booleans are not generic affirmations; they confirm the answer avoided the named unsupported or contraindicated claim.
