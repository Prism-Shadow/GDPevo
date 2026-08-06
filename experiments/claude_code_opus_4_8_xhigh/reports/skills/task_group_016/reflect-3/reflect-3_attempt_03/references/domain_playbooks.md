# Domain playbooks

Generalized checklists for the recurring case domains. They describe *how to reason*
and *which template fields depend on what*; read the concrete thresholds, codes, and
formulas from the case's protocol at runtime. Do not assume fixed numbers — protocol
versions and case data vary.

## Adult respiratory / CAP assessment
- Gather: oxygenation (and any recheck), respiratory rate, blood pressure,
  temperature, mental status, imaging impression, viral panel, active allergies.
- Escalation check: compare oxygenation / respiratory rate / systolic BP / mental
  status / multilobar-or-severity flags against the protocol's ED-escalation set. If
  none are met → outpatient with close follow-up; else → transfer with stabilization.
- Assessment enum: consolidation on final imaging + infective picture (± negative
  viral panel) points to bacterial pneumonia; otherwise the viral/URI or
  pending-protocol label per the findings.
- Red flags / return precautions: select from the template's enums only the findings
  actually present (red flags) and the protocol's listed warning signs (return
  precautions), mapping protocol phrasing to the nearest allowed enum value.
- Medication plan: allergy-aware regimen; report drug, dose, route, frequency,
  duration, and the **active** allergen classes avoided. Keep the antibiotic-strategy
  enum consistent with the allergy profile.
- Safety booleans: assert no contraindicated (e.g. penicillin/sulfa) drug is used,
  and never claim normal imaging / clear exam when the record shows otherwise.

## Pediatric head-injury triage
- Gather: mechanism, loss-of-consciousness duration, vomiting count, GCS, neuro/
  coordination exam, headache trajectory, other red-flag findings.
- Urgent-imaging triggers: repeated vomiting, worsening/severe headache, seizure,
  focal deficit, low GCS, prolonged LOC, basilar signs (per protocol). None present +
  near-normal exam + no urgent trigger → home observation, no immediate CT.
- Assessment enum: when the protocol's mild-TBI **support criteria** (brief symptoms,
  near-normal neuro exam, no urgent trigger) are met and there is no LOC, choose the
  mild-TBI-without-LOC label rather than a broader "with concussion features" label.
  This choice drives risk tier, disposition, and imaging — get it first.
- `red_flags` = concerning findings actually present; `absent_red_flags` = the serious
  red flags confirmed/observed **not** present (list the full confirmed-absent set).
- Restrictions: map the protocol's activity / return-to-play / school / driving
  guidance to the allowed enum values; include the driving restriction keyed to
  "while symptomatic" vs "until cleared" as the protocol states.
- Follow-up: pick a timeframe from the protocol's allowed window and the recheck
  route consistent with a home disposition.

## Electrolyte (e.g. potassium) repletion & follow-up
- Establish `current_time` from the findings clock, not "now."
- Latest value = latest **final**, **target-code (serum)**, **right-patient** result
  (exclude preliminary and wrong-specimen distractors).
- Urgent branch: critical value cutoff, ECG abnormality, dialysis/advanced-renal
  status, severe renal contraindication, or symptoms → urgent escalation + actions;
  otherwise routine oral repletion.
- Dose = (increments the value sits below target) × (amount per increment), rounded
  to the protocol's step. Report the medication order (code, drug, route, frequency,
  status) only when a routine plan applies.
- Follow-up lab: use the protocol's follow-up code; schedule at a **canonical morning
  hour (08:00Z) on the next calendar day** for a "next-morning" recheck.
- Contraindications object: dialysis flag, arrhythmia/symptom flag, and the eGFR
  value as an integer (or null if none on file).

## Care-management routing
- Sources: `care_registry` (risk score, chronic-condition and medication counts,
  dialysis schedule, recent admission), lab/vital observations (A1c, phosphorus,
  blood pressure), problem list, medications, and `sdoh` + call findings.
- Risk tier: registry risk score vs the protocol's high-risk cutoff.
- Program: count complex-care triggers met (multiple chronic conditions, recent
  admission, dialysis/advanced CKD, heart failure, uncontrolled diabetes) → complex
  vs routine vs not-eligible.
- Numeric anchors: echo exact chart values at required precision; active-medication
  count comes from the registry/active med list.
- Referrals / priority problems / escalation conditions are **sets**: include only
  well-supported items. A specialist referral or a "behavioral-health need" driven by
  only a **mild** screening score is over-inclusion — leave it out. Pharmacist and
  social-work referrals follow the protocol's explicit trigger rules.
- `care_plan_minima`: weekly-contact boolean from the protocol; a person-centered
  complex plan **requires a member-stated priority (true)** even if the bulleted
  minima omit it; set the minimum problem/discipline counts consistently and don't
  overwrite them with a blind guess once reasoned.
- `source_provenance`: split objective chart facts (labs, vitals, counts, admission,
  dialysis schedule — omit any not on file, e.g. eGFR) from member-disclosed facts
  (barriers, fatigue, care-goal preference).
- Outreach stance: choose permission-based/plain-language when the member wants
  permission-based contact.

## Observation-window retrieval & gate
- Read window bounds and target code from the findings/template (inclusive start,
  exclusive end). Echo them exactly with trailing `Z`.
- Build `matched` (four-filter eligible; sorted per template) and `excluded`
  (relevant distractors failing an **enumerated** reason — date/code/status; a
  wrong-patient record is neither). `lab_found` reflects the matched set.
- `latest_final` = latest matched value at one-decimal precision with its id and time.
- Gate enum from the latest matched interpretation (normal → satisfied; low →
  repletion needed; critical → urgent; none → no result in window). Repeat lab is
  typically not recommended (recommended=false, scheduled_time=null) when a normal
  final result already satisfies the gate.
