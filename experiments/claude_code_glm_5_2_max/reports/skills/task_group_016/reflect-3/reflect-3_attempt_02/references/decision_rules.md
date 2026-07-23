# Per-Domain Decision Rules

Transferable decision patterns for each clinic protocol family. These describe *how to reason*;
they do not contain task-specific answers. Always confirm thresholds against the protocol body
fetched from the runtime for the current run, since versions change.

## Adult respiratory / CAP (`RESP-CAP-*`)

1. Determine `primary_assessment` from fever + productive sputum + focal CXR consolidation →
   `community_acquired_pneumonia`. Negative viral PCR does not rule out CAP.
2. `risk_level`: escalate only when a protocol red flag / ED-escalation threshold is crossed.
   SpO2 92–93% (borderline, not <90) + pleuritic chest pain → `moderate`, not high.
3. `disposition`: `outpatient_close_followup` unless an ED-escalation threshold is met
   (SpO2 < 90, RR ≥ 30, SBP < 90, confusion, sepsis concern, immunocompromise, multilobar
   disease). `stabilization_actions` is `[]` when no threshold is crossed.
4. `red_flags`: only enum values actually present (hypoxemia_92_93, pleuritic_chest_pain,
   persistent_fever when fever is prolonged, etc.). Respiratory_distress / hemoptysis /
   confusion require explicit documentation.
5. `recommended_tests`: the protocol's controlled test panel (CXR-2V, SARS_FLU_RSV_PCR,
   PULSE_OX_RECHECK, CBC_BASIC) relevant to the workup.
6. `medication_plan`: allergy-aware. Active penicillin + sulfonamide →
   `doxycycline_outpatient` (avoids beta-lactam + sulfa). Set `avoid_allergens` to the active
   allergen classes; leave medication/dose/route/frequency/duration consistent with the
   strategy, or null for supportive/ED-deferred strategies.
7. `follow_up`: `timeframe_hours` from the protocol's `outpatient_follow_up_hours`;
   `route` = `primary_care_recheck`.
8. `return_precautions`: map the protocol's `return_precaution_codes` (e.g.
   worsening_shortness_of_breath, hypoxia, confusion, persistent_fever, chest_pain). These are
   general warnings — include confusion even when currently absent.
9. `safety_checks`: `no_penicillin_or_sulfa` true when the plan avoids them;
   `no_normal_cxr_claim` / `no_clear_lungs_claim` true when CXR is abnormal.

## Pediatric head injury (`PEDS-HEAD-*`)

1. `primary_assessment`: concussion features (headache, nausea, coordination difficulty, etc.)
   after head impact → `pediatric_head_injury_with_concussion_features`. No symptoms →
   `minor_head_injury_no_concussion_features`. No LOC + GCS 15 + symptomatic is still
   concussion-features, not "mild TBI without LOC" when symptoms are clearly present.
2. `risk_tier`: no urgent trigger + near-normal neuro exam → `intermediate` when concussion
   features exist, `low` only when no features. Reserve `high` for urgent triggers.
3. `disposition`: `home_observation_with_followup` when no urgent trigger; `ed_evaluation_ct_consideration`
   only with urgent triggers.
4. `imaging_recommendation`: no urgent trigger → `no_immediate_ct`.
5. `red_flags`: present items only — `head_impact`, `mild_nausea`, `coordination_symptom_observe`
   (mild coordination issue to observe). `worsening_headache` requires documented worsening, not
   a stable mild headache.
6. `absent_red_flags`: list only symptoms explicitly documented as absent (LOC, repeated
   vomiting, focal weakness "no focal weakness", worsening headache "stable"). Do **not** list
   `photophobia` as absent unless it was assessed — that is the classic false-claim trap.
7. `restrictions`: concussion → `relative_cognitive_physical_rest`,
   `return_to_learn_accommodations`, `no_high_risk_sports_until_cleared`. Driving restrictions
   only when the patient is driving-age and symptomatic.
8. `follow_up`: `timeframe_hours` from the protocol's `follow_up_hours` set (e.g. 48 for stable
   concussion features); `route` = `primary_care_or_concussion_recheck`.
9. `safety_checks`: `no_false_loc`, `no_false_vomiting`, `no_false_photophobia` — all true when
   you correctly report LOC/vomiting as absent (documented) and avoid claiming photophobia.

## Potassium replacement (`K-REPLETION-*`)

1. `current_time`: from the case `current_time` finding (ISO-8601 UTC with trailing `Z`).
2. `latest_potassium`: latest **final** serum-K (code `K`) observation for the target patient —
   exclude preliminary, canceled, whole-blood (`6298-4`), and wrong-patient. One decimal place.
3. Urgent branch (any of): K < `urgent_branch.potassium_less_than`, dialysis-dependent ESRD,
   ECG abnormality, severe renal contraindication, or arrhythmia symptoms
   (palpitations/syncope/weakness with arrhythmia concern). If urgent →
   `potassium_plan: urgent_escalation`, `urgent_actions` in clinical sequence
   (urgent_clinician_notification, ekg_now, telemetry_or_ed_evaluation), medication_order
   `status: defer_to_urgent_clinician`, `route/frequency: per_urgent_protocol`.
4. Routine branch (no urgent trigger, K below target): `replacement_required: true`,
   `potassium_plan: routine_oral_repletion`, `oral_dose_mEq` from the `routine_dose_rule`
   (deficit × mEq per 0.1 mmol/L, rounded to nearest mEq), `medication_order` with NDC from
   protocol `controlled_codes.routine_oral_potassium_ndc`, route PO, frequency `once`,
   status `recommended`.
5. `follow_up_lab`: LOINC from `controlled_codes.follow_up_lab`, `scheduled_time` = next
   calendar day 08:00 UTC ("next morning final serum potassium").
6. `contraindications`: `dialysis_dependent`, `arrhythmia_symptoms` booleans; `egfr` integer
   from the eGFR observation (or null if none).
7. `evidence_ids`: latest K obs, renal-function (eGFR) obs, case id, then other supporting
   obs — descending relevance.

## Care-management routing (`CM-*`)

1. `risk_tier`: `high` when registry `risk_score` ≥ protocol `high_predictive_risk_min`
   (e.g. 0.75); else moderate/low.
2. `program`: `complex_care_management` when complex-care supporting triggers hold
   (≥3 chronic conditions, recent admission, dialysis/advanced CKD, heart failure,
   uncontrolled diabetes) and risk is high; otherwise `routine_case_management` or
   `not_eligible`.
3. `priority_problems`: select the specific codes that match chart facts — use exactly one HF
   code per case (`hfpEF_post_volume_overload` for diastolic HF + volume overload vs
   `heart_failure_recent_admission` for a systolic post-admission case). Include
   `uncontrolled_diabetes` (high HbA1c), `esrd_on_hemodialysis`, `hyperphosphatemia`,
   `hypertension`, `polypharmacy` (≥10 meds), `transportation_barrier`,
   `financial_food_barrier` / `financial_medication_barrier` (match the disclosed facts),
   `dialysis_fatigue` when member-reported.
4. `numeric_anchors`: copy exact values with stated precision — `risk_score` (2 decimals),
   `hba1c_percent` (1 decimal), `phosphorus_mg_dl` (1 decimal), `blood_pressure` as
   "systolic/diastolic", `active_medication_count` integer.
5. `referrals`: protocol-triggered only — pharmacist (≥10 meds / insulin / high-risk
   diuretic-electrolyte), social_worker (≥2 moderate/severe SDOH domains),
   dialysis_care_coordination (ESRD), transportation_benefits (transport barrier). Skip
   behavioral_health_monitoring unless the PHQ-9 threshold/item is met.
6. `outreach_stance`: `permission_based_plain_language` when reluctant/refusing or when
   permission-based outreach is still required despite engagement.
7. `care_plan_minima`: `weekly_follow_up` true when protocol says weekly contact initially;
   `requires_member_stated_priority` true for complex care with member-disclosed preferences.
8. `escalation_conditions`: select the codes tied to the patient's conditions (missed dialysis
   / volume overload, dyspnea/weight-gain/ED return, PHQ-9 increase or item-9, severe
   hypo/hyperglycemia, hypertensive urgency, medication access failure).
9. `source_provenance.chart_facts`: objective facts present in the chart (include `egfr` only
   if an eGFR value exists). `member_disclosure_needed`: only member-stated barriers and
   preferences (not care-manager-noted facts).

## Observation-window lab retrieval (`LAB-*`)

1. `window`: inclusive `from`, exclusive `to` (copy from the case findings; ISO-8601 UTC).
2. `target_code`: from findings (e.g. `K`).
3. `lab_found`: true only if ≥1 **final** target-code observation for the target patient falls
   inside the window.
4. `matched_observation_ids`: all final + target-code + target-patient + in-window, sorted by
   `effective_time` asc then `observation_id` asc.
5. `excluded_observation_ids`: relevant distractors that fail by **date, code, or status**
   only — never include a wrong-patient observation. Sort by `effective_time` asc then
   `observation_id` asc.
6. `latest_final`: the matched observation with the latest `effective_time` (one decimal for
   the value). Null only when `lab_found` is false.
7. `protocol_gate`: from the latest final value — normal → `satisfies_recent_final_normal`;
   low → `recent_final_low_repletion_needed`; critical → `recent_final_critical_or_urgent`;
   none → `no_final_lab_in_window`.
8. `repeat_lab`: `recommended: false`, `scheduled_time: null` when the gate is
   `satisfies_recent_final_normal`; recommend a repeat only for abnormal/urgent gates.
