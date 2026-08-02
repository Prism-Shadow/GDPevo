# Task families → protocol → template mapping

Five recurring case types have been observed. Each maps a protocol (matched by
title / `case_type`) onto its answer template. Numbers below are illustrative of
version `2026.1`; **always re-read the live protocol body** and apply its values.

General mapping that holds for all families:
- `task_id` / `case_id` from the template + prompt; `patient_id` from the case
  record.
- Every `enum` field is decided by protocol triggers/thresholds applied to filtered
  evidence.
- `evidence_ids` = the ids you actually used, in the template's stated order.
- Safety/provenance booleans = honest compliance assertions (see SKILL step 7).

## 1. Adult respiratory / CAP — protocol `RESP-CAP-2026`
Template `adult_respiratory_protocol_assessment`. Decide `primary_assessment`,
`risk_level`, `disposition`, `red_flags`, `recommended_tests`, `medication_plan`,
`stabilization_actions`, `follow_up`, `return_precautions`, `safety_checks`.
- Drive severity from vitals/oxygenation (hypoxemia bands), consolidation on imaging,
  and red-flag findings; escalate (`ed_transfer`, `supplemental_oxygen`,
  `urgent_ed_transfer`) when the protocol's high-risk triggers fire.
- `medication_plan` is **allergy-aware**: check the allergy list, set
  `avoid_allergens`, and choose the `antibiotic_strategy` the protocol allows for
  that allergy profile (e.g. a non-beta-lactam alternative when penicillin-allergic;
  defer to ED when transferring; supportive-care/no-antibiotic for viral).
- Safety checks: `no_penicillin_or_sulfa` (plan avoids those classes),
  `no_normal_cxr_claim`, `no_clear_lungs_claim` — set `true` only if your output
  truly makes no such unsupported claim (a consolidation case must not claim a
  normal CXR / clear lungs).

## 2. Pediatric head injury — protocol `PEDS-HEAD-2026`
Decide `primary_assessment`, `risk_tier`, `disposition`, `imaging_recommendation`,
`red_flags`, `absent_red_flags`, `restrictions`, `follow_up`, `safety_checks`.
- `urgent_route_triggers` (e.g. repeated vomiting, worsening/severe headache,
  seizure, basilar skull signs, focal deficit, GCS<15, prolonged LOC) →
  `ed_evaluation_ct_consideration` / `urgent_ct` / higher tier. Absent all triggers
  with `mild_tbi_support` features → home observation / `no_immediate_ct`.
- Report **present** red flags **and** the sentinel red flags you confirmed
  **absent** — only list a red flag as absent if the record actively supports its
  negation. `restrictions` (rest, return-to-learn, no high-risk sports, driving)
  come from the protocol's restriction rules; `follow_up.timeframe_hours` from its
  `follow_up_hours`.
- Safety checks `no_false_loc` / `no_false_vomiting` / `no_false_photophobia` =
  `true` when you did not fabricate that symptom.

## 3. Potassium repletion & escalation — protocol `K-REPLETION-2026`
Decide `latest_potassium`, `replacement_required`, `potassium_plan`,
`oral_dose_mEq`, `medication_order`, `follow_up_lab`, `urgent_actions`,
`contraindications`, `evidence_ids`; `current_time` from case findings.
- Select the **latest `final` serum-potassium** (code `K`) for the patient.
- `urgent_branch` (e.g. K < 3.0, dialysis-dependent ESRD, ECG abnormality, severe
  renal contraindication, urgent symptoms) → `urgent_escalation` with
  `urgent_actions`, or `hold_due_to_contraindication`; medication `status` becomes
  `defer_to_urgent_clinician` / `not_recommended`.
- Otherwise, if K below `target_potassium_mmol_l`, `routine_oral_repletion`:
  `oral_dose_mEq` from the protocol's dose rule (e.g. mEq per 0.1 mmol/L below
  target, rounded to nearest 10); `medication_order` uses the protocol's controlled
  NDC, route `PO`; `follow_up_lab` uses the follow-up LOINC scheduled per the rule
  (e.g. next-morning final K) computed relative to `current_time`.
- If at/above target → `no_replacement`, `oral_dose_mEq` null, order
  `not_recommended`. Fill `contraindications` (`dialysis_dependent`,
  `arrhythmia_symptoms`, `egfr`) from the eGFR observation / findings.

## 4. Care-management routing — protocol `CM-HIGH-RISK-2026`
Decide `risk_tier`, `program`, `priority_problems`, `numeric_anchors`, `referrals`,
`outreach_stance`, `care_plan_minima`, `escalation_conditions`,
`source_provenance`.
- `risk_tier`/`program` from `risk_score` + problem burden against protocol
  thresholds (`complex_care_management` vs `routine_case_management` vs
  `not_eligible`).
- `numeric_anchors` (risk_score, hba1c, phosphorus, blood_pressure,
  active_medication_count) read from chart values with the template's precision;
  count only `active` medications.
- `source_provenance` splits evidence: `chart_facts` = values present in the record
  (risk_score, labs, eGFR, BP, med count, recent admission, dialysis schedule);
  `member_disclosure_needed` = SDOH/barrier items (transportation, financial/food,
  dialysis fatigue, care-goal preference) that require the member to disclose and
  are **not** assertable from the chart. Let this split also govern
  `outreach_stance` and which `priority_problems`/`escalation_conditions` you assert.

## 5. Observation-window / protocol gate — protocol `OBS-WINDOW-2026`
Decide `window`, `target_code`, `lab_found`, `matched_observation_ids`,
`excluded_observation_ids`, `latest_final`, `protocol_gate`, `repeat_lab`.
- Pure retrieval: for the target patient and `target_code`, keep `final`
  observations whose `effective_time` is in `[from, to)`; everything else relevant
  goes to `excluded_observation_ids` (with reason wrong owner/code/status/date).
- `lab_found` = at least one match. Sort matched (and excluded, when timed) by
  `effective_time` asc then `observation_id` asc. `latest_final` = the newest match
  (null when none / `lab_found` false).
- `protocol_gate` maps the latest final value to the enum
  (`satisfies_recent_final_normal` / `recent_final_low_repletion_needed` /
  `recent_final_critical_or_urgent` / `no_final_lab_in_window`); `repeat_lab`
  follows from the gate and protocol timing.
