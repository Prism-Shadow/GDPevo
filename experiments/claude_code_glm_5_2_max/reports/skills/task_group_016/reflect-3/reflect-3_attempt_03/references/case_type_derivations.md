# Case-Type Derivation Reference

For each case type, the protocol body defines the rules. Apply them to the case
record to derive the template fields. This is a method reference — derive the
actual values from the live case + protocol; do not assume any specific answer.

## acute_respiratory (CAP) — protocol `RESP-CAP-2026`-style

- Primary assessment from imaging + vitals + PCR: focal consolidation + fever +
  productive cough ⇒ CAP; negative respiratory viral PCR rules out viral URI.
- ED-escalation red flags are numeric thresholds (SpO2 < 90, RR ≥ 30, SBP < 90)
  plus other red flags (confusion, sepsis concern, immunocompromise, multilobar).
  Meeting none ⇒ outpatient disposition, not ED transfer.
- Risk level reflects the present red-flag band (e.g. SpO2 92–93 ⇒ the
  92–93 hypoxemia flag ⇒ moderate), not the absence of escalation.
- `recommended_tests` = controlled-code tests with results in the case.
- Allergy-aware antibiotic strategy: avoid the patient's active allergen classes;
  pick the enum strategy that is cross-reactivity-safe.
- `stabilization_actions`: empty unless an escalation threshold is met.
- `follow_up.timeframe_hours` and `return_precautions` come from the protocol
  (return-precaution codes map 1:1 to the template's precaution enum).

## pediatric_head_injury — protocol `PEDS-HEAD-2026`-style

- authoritative status = final; GCS, LOC duration, vomiting count, coordination
  are exam observations.
- Urgent-route triggers (repeated vomiting, worsening/severe headache, seizure,
  basilar skull signs, focal neuro deficit, GCS < 15, prolonged LOC) drive
  disposition/imaging. None met + GCS 15 ⇒ home observation, no immediate CT.
- `red_flags` holds the *present* mild/observe findings (head impact, mild
  nausea, coordination-to-observe); `absent_red_flags` holds the severe triggers
  that are explicitly absent (include an absent flag only when the record states
  absence or is silent on a safety-relevant item the template asks about).
- Restrictions derive from the protocol's driving / return-to-play / school rules.
- `follow_up` timeframe ∈ the protocol's listed hours; route = primary-care /
  concussion recheck for non-urgent cases.
- Risk tier aligns with disposition + imaging (home obs + no CT ⇒ not high).

## potassium_repletion — protocol `K-REPLETION-2026`-style

- `latest_potassium` = latest **final**, **serum** (code `K`) result for the
  patient; exclude preliminary and non-serum (whole-blood / different LOINC)
  results even if newer/lower.
- Urgent branch triggers: dialysis-dependent ESRD, ECG abnormality, K < threshold,
  severe renal contraindication, or arrhythmia symptoms. Any met ⇒ urgent plan,
  empty routine dose, defer medication to urgent clinician.
- No urgent trigger ⇒ `routine_oral_repletion`; oral dose = protocol formula
  (target − current, per-0.1 multiplier, round to nearest increment).
- `medication_order.ndc` = protocol's routine oral potassium NDC; route PO;
  status `recommended`.
- `follow_up_lab.loinc` = protocol's follow-up lab code; `scheduled_time` =
  next morning (next day `08:00:00Z`).
- `contraindications`: dialysis-dependent bool, arrhythmia-symptom bool, eGFR
  integer from the renal-function observation (null if absent).

## care_management — protocol `CM-HIGH-RISK-2026`-style

- `risk_tier` from predictive risk score vs. protocol minimum; `program` from
  supporting triggers (chronic-condition count, recent admission, dialysis/CKD,
  heart failure, uncontrolled diabetes).
- `priority_problems`: map each problem-list entry + SDOH + registry fact to its
  enum code; include behavioral-health need when a behavioral-health screen is
  documented; include dialysis fatigue when member-reported.
- `numeric_anchors`: copy exact registry/lab values at template precision.
- `referrals`: pharmacist (med-count/insulin/high-risk-diuretic triggers),
  social_work (≥ protocol-count moderate-or-severe SDOH domains),
  dialysis/transportation/behavioral-health services when the need is evidenced.
- `outreach_stance` from the member-engagement finding (permission-based when
  member is reluctant or states contact preferences).
- `care_plan_minima`: weekly follow-up from protocol; min-disciplines = the
  protocol-defined discipline triggers (pharmacist + social work at minimum);
  requires_member_stated_priority true when member disclosed preferences/barriers.
- `escalation_conditions`: one per active clinical risk (missed dialysis/volume
  overload, dyspnea/weight-gain/ED return, PHQ-9 increase, hypo/hyperglycemia,
  hypertensive urgency, medication-access failure).
- `source_provenance`: chart_facts = registry/lab/vital facts present in the
  record (exclude facts with no data, e.g. eGFR if unmeasured);
  member_disclosure_needed = member-disclosed barriers/preferences (transportation,
  food/medication financial barriers, dialysis fatigue, care-goal preference).

## observation_window — protocol `OBS-WINDOW-2026`-style

- `window` from/to and `target_code` from the case findings (ISO-8601 UTC).
- `lab_found` = any final, target-code, target-patient obs inside the window.
- `matched_observation_ids` = all such obs, sorted effective_time asc then id asc.
- `excluded_observation_ids` = relevant distractors failing for a reason the
  template lists (date / code / status). A wrong-patient distractor is excluded
  from `matched` but is **not** listed in `excluded` unless the template lists
  "patient" as an exclusion reason.
- `latest_final` = greatest effective_time among matched (null if none).
- `protocol_gate` from the latest final value vs. protocol thresholds.
- `repeat_lab`: not recommended (false/null) when the gate is satisfied by a
  recent normal final; recommended with a scheduled time otherwise.
