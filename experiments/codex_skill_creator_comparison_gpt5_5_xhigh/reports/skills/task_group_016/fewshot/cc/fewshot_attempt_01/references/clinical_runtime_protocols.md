# Clinical Runtime Protocol Reference

This reference captures reusable patterns for the synthetic clinic runtime. Use the live case record and live protocol content as the source of truth; these notes explain how to translate those facts into common answer templates.

## Runtime Access Pattern

- Read `environment_access.md` and use its `base_url`.
- Fetch `GET /api/cases/{case_id}` before broader endpoints. The case response usually contains `case`, `patient`, `findings`, `observations`, `imaging`, `allergies`, `medications`, `problems`, `care_registry`, and `sdoh`.
- Fetch `/api/protocols` and then the relevant `/api/protocols/{protocol_id}`:
  - acute respiratory/CAP: `RESP-CAP-2026`
  - pediatric head injury: `PEDS-HEAD-2026`
  - potassium replacement: `K-REPLETION-2026`
  - care-management routing: `CM-HIGH-RISK-2026`
  - observation-window interpretation: `OBS-WINDOW-2026`
- If a bundled case record is incomplete, use allowed list endpoints and filter by `case_id` and `patient_id`. Do not use records for other patients to support target-patient decisions.

## Template Discipline

- The answer template is binding for required keys, allowed enum strings, nullability, and precision.
- Prefer controlled enum codes over prose. Do not invent a new enum spelling even when it seems clearer.
- Keep evidence lists concise and source-grounded. Include only identifiers that support selected fields.
- For numeric anchors, copy the numeric value from observations or registry data and round only as requested by the template.

## Observation Rules

- A qualifying observation generally needs `status: "final"`.
- Sort window-matched observation ids by `effective_time` ascending, then `observation_id` ascending.
- Excluded observation lists should include same-patient, relevant distractors: wrong date, wrong code, or wrong status. Do not include wrong-patient observations unless the prompt explicitly asks for that category.
- For latest-result tasks, choose the latest eligible final observation by `effective_time`; ignore preliminary results and wrong specimen/code results.

## Respiratory/CAP Mapping

Use the adult respiratory protocol for acute cough, fever, hypoxemia, CXR, or pneumonia tasks.

- CAP assessment: focal airspace consolidation or equivalent CXR impression with infectious symptoms supports `community_acquired_pneumonia`. Viral symptoms without consolidation support `viral_upper_respiratory_infection`. Missing decisive protocol evidence supports a pending/protocol-pending enum when available.
- Escalate to ED when protocol urgent criteria are met, such as room-air oxygen saturation below the protocol threshold, respiratory rate at or above the urgent threshold, systolic blood pressure below the urgent threshold, confusion, sepsis concern, immunocompromise, or multilobar disease.
- Borderline oxygen saturation around 92-93% and pleuritic chest pain are outpatient red flags when no ED threshold is met.
- Recommended tests commonly include CXR, respiratory viral PCR, and pulse-ox recheck when pneumonia or hypoxemia is being assessed. Add CBC/basic labs only when the protocol or severity supports it.
- Medication plans must be allergy-aware. Use active allergy classes only. For outpatient CAP with active beta-lactam or sulfonamide constraints, doxycycline is the usual allergy-aware strategy if tetracycline allergy is absent. If ED transfer is selected, defer antibiotic choice to urgent clinicians when the template has that enum.
- Return precautions should use the template's allowed codes and cover worsening breathing, hypoxia, chest pain, confusion, persistent fever, and hemoptysis when available.
- Safety booleans should confirm you did not claim normal CXR, clear lungs, or use prohibited allergy classes unless supported.

## Pediatric Head Injury Mapping

Use the pediatric head-injury protocol for concussion, skateboard/fall, head impact, GCS, vomiting, LOC, seizure, neurologic findings, CT, restrictions, or return-to-learn tasks.

- High-risk/urgent route triggers include repeated vomiting, worsening severe headache, seizure, basilar skull signs, focal neurologic deficit, GCS below 15, and prolonged loss of consciousness.
- Mild symptoms with normal or near-normal neurologic exam and no urgent trigger support an intermediate or mild-TBI pathway with home observation and close follow-up.
- Do not mark absent red flags from silence. Use explicit findings such as no LOC, zero vomiting episodes, no focal weakness, or documented absence.
- Typical mild-TBI restrictions are relative cognitive/physical rest, return-to-learn accommodations, no high-risk sports until cleared, and no driving while symptomatic. Use stricter driving clearance enums when the record or risk tier warrants it.
- Imaging is generally `no_immediate_ct` when no urgent trigger is present; use CT/ED enums when urgent triggers are present.
- Evidence ids should include the case id plus key GCS, vomiting/LOC, and neurologic observation ids that drove the risk tier.

## Potassium Replacement Mapping

Use the potassium replacement protocol for serum potassium status, oral repletion, urgent escalation, contraindication screening, and follow-up potassium labs.

- Eligible potassium observations use the protocol serum potassium code, final status, target patient, and correct specimen. Ignore preliminary potassium and whole-blood potassium when the protocol asks for serum/plasma potassium.
- Choose the latest eligible final serum potassium observation.
- Compare to the protocol target potassium. If the value is at or above target, replacement is not required.
- If the value is below target and no urgent branch applies, use the routine oral pathway. Dose is based on the deficit from target using the protocol's mEq-per-0.1 rule and rounding rule.
- Urgent branch triggers include potassium below the urgent threshold, dialysis-dependent ESRD, severe renal contraindication, abnormal ECG, or symptoms such as palpitations, syncope, or arrhythmia-concern weakness.
- Use the protocol follow-up lab code for repeat serum potassium. Routine repletion generally schedules the next morning final serum potassium check.
- Contraindications should be explicit booleans or numeric values from problems, registry data, findings, ECG observation, and eGFR observation.
- Evidence ids should prioritize the potassium observation, renal-function/ECG evidence, then case or finding ids as needed.

## Care-Management Routing Mapping

Use the care-management protocol for registry risk, complex care, referrals, outreach stance, care-plan minima, and SDOH routing.

- High risk is supported by the protocol predictive-risk threshold and multiple supporting triggers such as chronic-condition count, recent admission, dialysis/advanced CKD, heart failure, and uncontrolled diabetes.
- `complex_care_management` is appropriate when high predictive risk and complex-care triggers are present. Use routine or not-eligible enums only when those criteria are not met.
- Clinical priority problems come from active problems, recent admissions, high-risk labs, blood pressure, and medication burden. Put social barriers primarily in referrals and member-disclosure provenance unless the prompt clearly asks to treat them as priority problem codes.
- Pharmacist referral is supported by high active-medication count, insulin safety, or high-risk diuretic/electrolyte regimen.
- Social-worker and transportation referrals are supported by moderate/severe SDOH domains and transportation evidence.
- Dialysis care coordination is supported by ESRD, dialysis schedule, or dialysis-related fatigue/admission.
- Use permission-based outreach when the member is reluctant, requests limits on calls, or the protocol says permission-based outreach is required.
- Care-plan minima usually include multiple problems, initial weekly follow-up, member-stated priority, and at least two disciplines when complex care is selected.
- Escalation conditions should be tied to concrete risks in the case, such as missed dialysis/volume overload, worsening dyspnea/weight gain/ED return, PHQ-9 worsening or item 9 concern, severe glycemic events, hypertensive urgency, or medication access failure.
- Source provenance should separate chart facts from facts requiring member disclosure. Keep chart facts to the core facts used for routing and numeric anchors; put SDOH barriers, fatigue, access barriers, and care-goal preference under member disclosure when applicable.

## Observation-Window Gate Mapping

Use the observation-window protocol for tasks that ask whether a target lab exists in a time window.

- Read the window start and end from case findings or the prompt. Treat start as inclusive and end as exclusive.
- Match observations only when patient id, target code, final status, and window membership all qualify.
- `lab_found` is true only when at least one qualifying observation exists.
- `latest_final` is the latest qualifying final observation, or `null` when none exist.
- For potassium windows, use the latest qualifying value to choose the protocol gate:
  - no qualifying final result: `no_final_lab_in_window`
  - final value below urgent/critical threshold: urgent/critical gate enum when present
  - final low but non-critical value: low/repletion-needed gate enum when present
  - final normal/recent value: normal/satisfies gate enum when present
- Repeat lab is usually not recommended when the latest final result satisfies the protocol gate; recommend it when no final qualifying lab exists or the gate indicates low/urgent follow-up is needed.
