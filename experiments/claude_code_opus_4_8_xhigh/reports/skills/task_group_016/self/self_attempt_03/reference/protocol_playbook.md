# Protocol playbook (per case_type)

Condition-driven decision rules for each clinic protocol, plus the mapping from
protocol wording to answer-template enum values. Everything below is a **reusable
rule keyed on evidence**, not a stored answer for any specific case. Numbers shown
(e.g. `0.75`, `3.5 mmol/L`, `48h`) are protocol thresholds/constants — always
re-fetch `GET /api/protocols/{id}` and let the live `body` win if it differs.

General mapping principle: protocols name concepts in their own vocabulary
(triggers, code keys, return-precaution codes). The answer template has its **own**
enum vocabulary. Compute the clinical fact from the protocol, then emit the nearest
value from the template field's `allowed_values`. If no allowed value fits, the
value is simply not selected.

---

## acute_respiratory → RESP-CAP-2026

**Protocol body:** `controlled_codes` (chest_xray=CXR-2V, respiratory_viral_pcr=
SARS_FLU_RSV_PCR, pulse_ox_recheck=PULSE_OX_RECHECK, basic_cbc=CBC_BASIC,
oxygen_saturation=59408-5, respiratory_rate=9279-1, temperature=8310-5);
`authoritative_statuses`=[final]; `ed_escalation` = SpO2 room-air `< 90`, RR `>= 30`,
SBP `< 90`, or other_red_flags {confusion, sepsis_concern, immunocompromise,
multilobar_disease}; `outpatient_follow_up_hours`=48; `allergy_rule` = avoid
implicated classes of active allergies.

**Decision rules:**
- `primary_assessment`: final chest X-ray shows focal consolidation + infective
  features → `community_acquired_pneumonia`; no imaging/impression available yet →
  `pneumonia_protocol_pending`; URI picture without consolidation →
  `viral_upper_respiratory_infection`.
- ED-escalation test: if any `ed_escalation` criterion is met → `disposition`=
  `ed_transfer`, `risk_level`=`high`, `stabilization_actions` include
  `urgent_ed_transfer` (add `supplemental_oxygen` when hypoxemic), `follow_up.route`=
  `emergency_department`. Otherwise → `outpatient_close_followup`, `risk_level`
  low/moderate by severity, `follow_up` = 48h `primary_care_recheck`.
- `red_flags` (map observed → enum): SpO2 92–93% → `hypoxemia_92_93`; SpO2 < 90 →
  `hypoxemia_below_90`; pleuritic pain → `pleuritic_chest_pain`; plus
  `respiratory_distress`, `confusion`, `hemoptysis`, `persistent_fever`,
  `worsening_shortness_of_breath` as evidenced.
- `recommended_tests` ⊂ {CXR-2V, SARS_FLU_RSV_PCR, PULSE_OX_RECHECK, CBC_BASIC}.
- `medication_plan` (allergy-aware):
  - CAP outpatient with **active penicillin and/or sulfonamide** allergy →
    `antibiotic_strategy`=`doxycycline_outpatient` (doxycycline, PO), and
    `avoid_allergens` lists every active implicated class (e.g. penicillin,
    sulfonamide).
  - CAP outpatient, no such allergy → `standard_outpatient_beta_lactam_plus_macrolide`.
  - Viral URI → `supportive_care_no_antibiotic`, medication/dose/route/frequency null.
  - ED transfer → `defer_antibiotic_selection_to_ed`.
- `return_precautions` — map protocol `return_precaution_codes` → template enums:
  `worsening_dyspnea`→`worsening_shortness_of_breath`, `oxygen_below_90`→`hypoxia`,
  `confusion`→`confusion`, `persistent_fever`→`persistent_fever`,
  `chest_pain`→`chest_pain`.
- `safety_checks`: `no_penicillin_or_sulfa`=true when the plan avoids those classes;
  `no_normal_cxr_claim`=true when you did not assert a normal CXR (never claim normal
  when consolidation is present); `no_clear_lungs_claim`=true when you did not assert
  clear lungs.

---

## pediatric_head_injury → PEDS-HEAD-2026

**Protocol body:** `authoritative_statuses`=[final]; `follow_up_hours`=[24,48];
`mild_tbi_support` = {brief_confusion_or_symptoms, normal_or_near_normal_neurologic_exam,
no_protocol_urgent_trigger}; `urgent_route_triggers` = {repeated_vomiting,
worsening_severe_headache, seizure, basilar_skull_signs, focal_neurologic_deficit,
gcs_below_15, prolonged_loss_of_consciousness}; `restrictions` for driving/school/
return-to-play.

**Decision rules:**
- Any `urgent_route_trigger` present → `risk_tier`=`high`, `disposition`=
  `ed_evaluation_ct_consideration`, `imaging_recommendation`=`urgent_ct` (or
  `ct_or_ed_per_protocol`), `follow_up.route`=`emergency_department`.
- No urgent trigger, GCS 15, exam normal/near-normal with mild symptoms →
  `mild_traumatic_brain_injury_without_loss_of_consciousness` (no LOC) or
  `pediatric_head_injury_with_concussion_features` (concussion features present),
  `risk_tier` low/intermediate, `disposition`=`home_observation_with_followup`,
  `imaging_recommendation`=`no_immediate_ct`, `follow_up` = 24–48h
  `primary_care_or_concussion_recheck`. Truly minimal, no features →
  `minor_head_injury_no_concussion_features`.
- `red_flags`: list present findings mapped to enums (`head_impact`, `mild_nausea`,
  `coordination_symptom_observe`, and any true urgent findings).
- `absent_red_flags`: list only the ones the record **explicitly denies** (e.g. LOC
  absent, vomiting absent) drawn from the field's allowed_values.
- `restrictions`: typically `relative_cognitive_physical_rest`,
  `return_to_learn_accommodations`, `no_high_risk_sports_until_cleared`; add a driving
  restriction only when driving is relevant to the patient. Use
  `normal_activity_as_tolerated` only for a truly minor injury.
- `safety_checks`: `no_false_loc` / `no_false_vomiting` / `no_false_photophobia` =
  true when your output makes no such claim beyond what the record supports (record
  says "absent" → set true).

---

## potassium_repletion → K-REPLETION-2026

**Protocol body:** `authoritative_statuses`=[final]; `controlled_codes`
(serum_potassium=**K**, egfr=33914-3, follow_up_lab=2823-3,
routine_oral_potassium_ndc=40032-917-01, ecg_summary=ECG-SUMMARY);
`target_potassium_mmol_l`=3.5; `routine_dose_rule` = 10 mEq per 0.1 mmol/L below
target, round to nearest 10 mEq, applies only when the urgent branch is false;
`routine_follow_up` = next-morning final serum potassium; `urgent_branch` if K `< 3.0`
OR dialysis-dependent ESRD OR ECG abnormality OR severe renal contraindication OR
symptoms {palpitations, syncope, weakness_with_arrhythmia_concern}.

**Decision rules:**
- `latest_potassium`: latest observation with `code == "K"` (serum), `status ==
  final`, patient-matched. **Exclude** whole-blood look-alikes (e.g. `6298-4`) and
  `preliminary` results — classic distractors.
- Urgent branch true → `potassium_plan`=`urgent_escalation`; `medication_order.status`
  =`defer_to_urgent_clinician` with route/frequency `per_urgent_protocol` (or null);
  `urgent_actions` sorted by clinical sequence: `urgent_clinician_notification`,
  `ekg_now`, `telemetry_or_ed_evaluation`.
- Contraindication that makes routine oral unsafe (e.g. dialysis/severe renal) →
  `hold_due_to_contraindication`, no oral dose.
- Otherwise, K `< 3.5` and urgent branch false → `replacement_required`=true,
  `potassium_plan`=`routine_oral_repletion`; `oral_dose_mEq` =
  round-to-nearest-10 of `10 × ((3.5 − K) / 0.1)` mEq (e.g. K 3.2 → 30 mEq;
  K 3.4 → 10 mEq); `medication_order` ndc=40032-917-01, route `PO`,
  `status`=`recommended`; `follow_up_lab.loinc`=2823-3, `scheduled_time` = next
  morning **relative to `current_time`**.
- K `>= 3.5` → `no_replacement`, `oral_dose_mEq`=null, `medication_order.status`=
  `not_recommended` (nulls per spec), follow-up lab per protocol (may be null).
- `contraindications`: `dialysis_dependent` and `arrhythmia_symptoms` booleans from
  problems/findings; `egfr` = integer from a final 33914-3 observation, else null.

---

## observation_window → OBS-WINDOW-2026

**Protocol body:** `controlled_codes` (serum_potassium=K, etc.);
`excluded_statuses`=[preliminary, entered-in-error, canceled]; `status_rule` =
only `final` satisfies gates; `same_code_selection` = latest final within the window;
`ordering` = effective_time ascending, then observation_id ascending.

**Decision rules:**
- `window.from`/`window.to` come from the case findings (`window_start`/`window_end`).
  Treat as `from` inclusive, `to` exclusive (per template).
- A row **matches** iff: `patient_id == target patient`, `code == target_code`,
  `status == final`, and `from <= effective_time < to`. Sort matches by
  effective_time asc then observation_id asc → `matched_observation_ids`.
- `excluded_observation_ids`: relevant-but-disqualified distractors — wrong patient
  (another patient's row attached to the case), wrong code (e.g. `NA`, whole-blood),
  non-final status, or outside the window. Sort them the same way.
- `lab_found` = matches is non-empty. `latest_final` = the latest matched row
  (observation_id, value_mmol_l at required precision, effective_time); null when
  `lab_found` is false.
- `protocol_gate` from the latest final value/interpretation: normal →
  `satisfies_recent_final_normal`; low → `recent_final_low_repletion_needed`;
  critical/urgent → `recent_final_critical_or_urgent`; none matched →
  `no_final_lab_in_window`.
- `repeat_lab.recommended` + `scheduled_time` per the gate (recommend and schedule a
  repeat when repletion/critical; compute time relative to the window/clock).

---

## care_management → CM-HIGH-RISK-2026

**Protocol body:** `high_predictive_risk_min`=0.75;
`complex_care_supporting_triggers` = {chronic_condition_count_at_least_3,
recent_admission, dialysis_or_advanced_ckd, heart_failure, uncontrolled_diabetes};
`pharmacist_referral_triggers` = {active_medication_count_at_least_10, insulin_safety,
high_risk_diuretic_or_electrolyte_regimen}; `social_work_referral` = ≥2 moderate/severe
domains among {transportation, financial, food, housing}; `care_plan_minima` =
{weekly_contact_initially, medication_reconciliation, barrier_resolution,
clear_escalation_conditions}; `outreach` = permission-based when member is
reluctant/refusing.

**Decision rules:**
- `risk_tier`: `high` when registry `risk_score >= 0.75`; else moderate/low.
- `program`: `complex_care_management` when high risk **and** ≥1 supporting trigger;
  else `routine_case_management` or `not_eligible`.
- `numeric_anchors` (exact precision): `risk_score` (2 dp), `hba1c_percent` (1 dp),
  `phosphorus_mg_dl` (1 dp), `blood_pressure` as `"systolic/diastolic"`,
  `active_medication_count` (integer). Pull from final observations / care_registry.
- `priority_problems` from problems + registry, mapped to allowed enums (e.g.
  `esrd_on_hemodialysis`, `uncontrolled_diabetes` when A1c high, `hyperphosphatemia`,
  `heart_failure_recent_admission` / `hfpEF_post_volume_overload`, `hypertension`,
  `polypharmacy` when meds ≥ 10, plus disclosed barriers/`dialysis_fatigue`).
- `referrals`: `pharmacist` when a pharmacist trigger is met; `social_worker` when ≥2
  moderate/severe SDOH domains; `dialysis_care_coordination` for dialysis;
  `behavioral_health_monitoring` for a behavioral-health signal; `transportation_benefits`
  for a transport barrier; `primary_care` as appropriate.
- `outreach_stance`: `permission_based_plain_language` when the member is reluctant or
  wants to control contact timing.
- `care_plan_minima`: derive `min_problem_count`, `weekly_follow_up` (true when weekly
  contact required), `requires_member_stated_priority`, `min_disciplines` from the
  protocol minima.
- `escalation_conditions`: choose allowed enums matching the member's conditions
  (e.g. `missed_dialysis_or_volume_overload`, `dyspnea_weight_gain_or_ed_return`,
  `phq9_increase_or_item9_positive`, `severe_hypoglycemia_or_hyperglycemia`,
  `hypertensive_urgency`, `medication_access_failure`).
- `source_provenance`: `chart_facts` = facts already in the chart (risk_score,
  hba1c_percent, phosphorus_mg_dl, egfr, blood_pressure, active_medication_count,
  recent_admission, dialysis_schedule that you used); `member_disclosure_needed` =
  facts only the member can confirm (transportation/financial/food barriers,
  dialysis_fatigue, care_goal_preference).
