# Protocol logic — orientation guide

Always read the **live** protocol body (`GET /api/protocols/{id}`) and apply its actual
values. The summaries below (as of version `2026.1`) tell you *which fields to read* and
*how they map to the answer template*. They contain no case-specific answers — only
general rules to reconcile against the live protocol and the case bundle.

---

## RESP-CAP-2026 — Adult respiratory / CAP

Read from `body`: `ed_escalation` thresholds, `controlled_codes`, `authoritative_statuses`
(`final`), `outpatient_follow_up_hours`, `return_precaution_codes`, `allergy_rule`.

Decision flow:
- **Disposition / risk:** escalate to ED when any `ed_escalation` threshold is met — room-air
  SpO₂ < the stated cutoff, respiratory rate ≥ the stated cutoff, systolic BP < the stated
  cutoff, or an `other_red_flags` item (confusion, sepsis concern, immunocompromise,
  multilobar disease). If none are met, disposition is outpatient with close follow-up and
  risk is graded from the borderline findings present (e.g. borderline hypoxemia raises it
  off "low").
- **Primary assessment:** consolidation on imaging + infectious features → CAP; negative
  viral PCR does not downgrade a radiographic consolidation. Choose the enum that the
  evidence supports; use the "pending" enum only when the defining evidence is genuinely
  unresolved.
- **Red flags / return precautions:** translate observed findings and the protocol's
  `return_precaution_codes` into the template's enum vocabulary (map, don't copy raw text).
- **Recommended tests:** use the controlled-code enums (`CXR-2V`, `SARS_FLU_RSV_PCR`,
  `PULSE_OX_RECHECK`, `CBC_BASIC`) that support the workup.
- **Medication plan (allergy-aware):** honor `allergy_rule` — avoid classes implicated by
  **active** allergies. With active penicillin + sulfonamide allergies, a beta-lactam and
  sulfa are off the table; choose an enum-allowed non-cross-reactive strategy, list avoided
  classes in `avoid_allergens`, and set `no_penicillin_or_sulfa` accordingly. If disposition
  is ED, the enum may direct deferring antibiotic selection to the ED.
- **Follow-up:** `outpatient_follow_up_hours` with a primary-care recheck route.
- **Safety:** never claim a normal CXR or clear lungs when imaging is abnormal.

## PEDS-HEAD-2026 — Pediatric head injury

Read: `urgent_route_triggers`, `mild_tbi_support`, `follow_up_hours` (e.g. 24/48),
`restrictions` (return_to_play, school, driving).

- **Urgent vs. home:** if any `urgent_route_triggers` item is present (repeated vomiting,
  worsening/severe headache, seizure, basilar skull signs, focal deficit, GCS < 15,
  prolonged LOC) → ED / CT consideration, higher tier, urgent imaging. Otherwise home
  observation with follow-up and `no_immediate_ct`.
- **Assessment enum:** presence of concussion features (symptoms + a mild exam finding such
  as a coordination issue) vs. minor injury with no concussion features vs. mild TBI — pick
  per `mild_tbi_support` and the exam.
- **red_flags / absent_red_flags:** report observed flags, and list the protocol red flags
  the record explicitly shows to be **absent** in `absent_red_flags`. The `no_false_*`
  safety booleans assert you did not fabricate LOC / vomiting / photophobia.
- **restrictions:** map the protocol's rest / return-to-learn / return-to-play / driving
  guidance to the template enums.

## K-REPLETION-2026 — Potassium replacement

Read: `target_potassium_mmol_l`, `authoritative_statuses` (`final`), `controlled_codes`
(serum K = `K`, eGFR = `33914-3`, follow-up lab LOINC = `2823-3`, oral KCl NDC,
ECG summary), `urgent_branch`, `routine_dose_rule`, `routine_follow_up`.

- **Latest potassium:** among the patient's **final** observations with code `K` (serum —
  not whole-blood `6298-4`, not preliminary), take the latest by `effective_time`. Report
  it to one decimal place.
- **Urgent branch first:** if K < the urgent cutoff, dialysis-dependent ESRD, ECG
  abnormality, severe renal contraindication, or urgent symptoms (palpitations, syncope,
  weakness with arrhythmia concern) → `urgent_escalation`, populate `urgent_actions` in
  clinical sequence, and defer medication to the urgent clinician. Contraindication present
  → `hold_due_to_contraindication`.
- **Routine branch:** if none of the above and K < target → `routine_oral_repletion`.
  Oral dose from `routine_dose_rule`: `mEq_per_0_1_mmol_l_below_target` × (deficit / 0.1),
  rounded to the nearest `round_to_nearest_mEq`. Order the oral KCl NDC (PO). If K ≥ target
  → `no_replacement`, dose `null`.
- **Follow-up lab:** LOINC `2823-3`, scheduled per `routine_follow_up` (e.g. next-morning
  final serum potassium) relative to the case `current_time`. `contraindications` reports
  dialysis dependence, arrhythmia symptoms, and eGFR (integer or null).

## OBS-WINDOW-2026 — Observation window / protocol gate

Read: `status_rule` / `excluded_statuses` (only `final` qualifies), `controlled_codes`,
`same_code_selection` (latest final within window), `ordering`
(`effective_time` asc, then `observation_id` asc).

- **Window:** `from` inclusive, `to` exclusive.
- **Matched:** observations that are the target patient + target code + `final` +
  inside the window. Sort per `ordering`.
- **Excluded:** the *relevant near-misses* — right idea, disqualified by date (outside
  window), code (e.g. sodium or whole-blood K), status (preliminary), or patient (row
  stamped with the case but another `patient_id`). Sort by effective_time asc.
- **lab_found / latest_final:** `lab_found` true iff ≥1 matched; `latest_final` is the
  latest matched by effective_time (null when none).
- **protocol_gate:** pick the enum from the latest final value vs. the repletion threshold
  (normal-satisfies vs. low-repletion-needed vs. critical/urgent vs. no-final-in-window).
  `repeat_lab.recommended` and `scheduled_time` follow from the gate (null time when not
  recommended).

## CM-HIGH-RISK-2026 — Care-management routing

Read: `high_predictive_risk_min` (e.g. 0.75), `complex_care_supporting_triggers`,
`pharmacist_referral_triggers`, `social_work_referral` (domains; ≥2 moderate/severe),
`care_plan_minima`, `outreach` guidance. Registry facts live in
`care_registry` (risk_score, chronic_condition_count, medication_count, dialysis_schedule,
recent_admission_date, program_hint).

- **Risk tier / program:** `high` when risk_score ≥ `high_predictive_risk_min`; assign
  `complex_care_management` when the risk floor plus supporting triggers (≥3 chronic
  conditions, recent admission, dialysis / advanced CKD, heart failure, uncontrolled
  diabetes) are met; else routine/none.
- **priority_problems / escalation_conditions:** map active problems + registry facts to
  the template enums (e.g. ESRD on HD, HFpEF post volume overload, hyperphosphatemia,
  uncontrolled diabetes, polypharmacy, disclosed barriers).
- **numeric_anchors:** risk_score (2 dp), HbA1c (1 dp), phosphorus (1 dp), blood_pressure as
  `"sys/dia"` string, active_medication_count (int) — pull from observations/registry.
- **referrals:** pharmacist when a `pharmacist_referral_triggers` item holds (≥10 meds,
  insulin safety, high-risk diuretic/electrolyte regimen); social worker when ≥2
  moderate/severe SDOH domains; plus dialysis/PC/behavioral as the data supports.
- **outreach_stance:** permission-based/plain-language when the member is reluctant or
  requests it.
- **care_plan_minima:** derive `min_problem_count`, `weekly_follow_up`,
  `requires_member_stated_priority`, `min_disciplines` from the protocol's `care_plan_minima`.
- **source_provenance — the key distinction:** `chart_facts` are objective values already in
  the chart/registry/observations (risk_score, hba1c, phosphorus, egfr, BP, med count,
  recent_admission, dialysis_schedule). `member_disclosure_needed` are things known only
  because the member said so — trace them by `source_id` (call notes, member-disclosed SDOH):
  transportation/financial/food barriers, dialysis fatigue, care-goal preference. Classify by
  the evidence's source, not by the topic.
