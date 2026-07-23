# Task-Family Playbooks

Derivation patterns for each task family. These describe the **reasoning**, not any specific case's answer. Always re-derive from the current case + protocol.

## A. Adult respiratory infection / CAP assessment

1. Fetch the respiratory protocol. Note `ed_escalation` thresholds (SpO2 `<`, RR `>=`, SBP `<`, and `other_red_flags`) and `outpatient_follow_up_hours`.
2. From `findings`, decide:
   - **primary_assessment**: focal consolidation on imaging + productive cough + fever → community-acquired pneumonia; a negative viral PCR supports bacterial over viral.
   - **risk_level / disposition**: any ed_escalation trigger met → high / ed_transfer; borderline SpO2 in the 92–93 band with stable vitals and no trigger → moderate / outpatient_close_followup.
   - **red_flags**: include only findings explicitly present (e.g. a 92–93% SpO2 band, pleuritic chest pain). A fever of a few days is **not** automatically a "persistent_fever" red flag unless the case frames it so; do not add it speculatively.
   - **recommended_tests**: list the protocol-controlled tests actually relevant/performed for this case. Do **not** add a basic lab panel that was never resulted (over-inclusion fails the set).
   - **medication_plan**: use active allergies to choose the strategy; pick the protocol's non-cross-reactive outpatient alternative (e.g. a tetracycline when beta-lactams and sulfa are both contraindicated). Set `avoid_allergens` to the active allergen classes only.
   - **stabilization_actions**: empty list unless an immediate action (supplemental O2, urgent ED transfer) is genuinely indicated by the escalation thresholds.
   - **return_precautions**: map the protocol's `return_precaution_codes` to the template enum (e.g. `oxygen_below_90` → `hypoxia`, `worsening_dyspnea` → `worsening_shortness_of_breath`).
   - **safety_checks**: assert no penicillin/sulfa given, no "normal CXR" claim when imaging shows consolidation, no "clear lungs" claim.

## B. Pediatric head injury triage

1. Fetch the pediatric head-injury protocol. Note `urgent_route_triggers` (the high tier) and `mild_tbi_support` (the lower band), plus `follow_up_hours` and `restrictions`.
2. From `findings`:
   - **primary_assessment**: choose the enum that matches the protocol band. "No LOC, GCS 15, near-normal exam, no urgent trigger, mild symptoms" → mild TBI without loss of consciousness (mirrors `mild_tbi_support`); reserve the "concussion features" enum for cases the protocol frames that way.
   - **risk_tier / disposition / imaging**: any urgent trigger → high / ED / urgent or CT-per-protocol; otherwise intermediate (symptomatic) or low (trivial) / home observation / no immediate CT.
   - **red_flags** vs **absent_red_flags**: split the enum by explicit presence/absence in findings (LOC, vomiting, seizure, focal weakness, worsening headache, basilar skull signs, photophobia are the serious absent-able ones). Include a mild-symptom flag (head impact, mild nausea, coordination-to-observe) only when documented.
   - **restrictions**: map protocol restriction clauses. A driving clause that fires on "sedating medicine" does **not** fire when the patient's medication is a stimulant; and applies to the symptomatic clause only when actually symptomatic. Do not add restrictions unsupported by the protocol.
   - **safety_checks**: assert no false LOC / vomiting / photophobia (i.e. those are listed absent, not present).

## C. Potassium replacement and follow-up lab

1. Fetch the potassium protocol. Note `controlled_codes` (serum_potassium code, eGFR code, follow-up lab LOINC, routine oral NDC, ECG code), `target_potassium_mmol_l`, `urgent_branch` triggers, and `routine_dose_rule`.
2. Identify the **latest eligible final serum potassium**: code must equal the serum potassium code (exclude whole-blood/POC potassium codes and any non-final status). Among final, correct-code results at/before `current_time`, take the latest `effective_time`.
3. Evaluate the **urgent branch**: K below `potassium_less_than`, abnormal ECG, dialysis-dependent ESRD, severe renal contraindication, or protocol-listed arrhythmia symptoms. If any → `urgent_escalation` plan, urgent actions ordered by clinical sequence, and `defer_to_urgent_clinician` medication status.
4. If urgent branch false → `routine_oral_repletion`: `replacement_required` true; `oral_dose_mEq` = (target − latest K) / 0.1 × `mEq_per_0_1_mmol_l_below_target`, rounded to `round_to_nearest_mEq`. Medication order uses the protocol NDC, PO route, status `recommended`.
5. **follow_up_lab**: LOINC from `controlled_codes`; `scheduled_time` = next morning = **next calendar day 08:00:00Z**.
6. **contraindications**: dialysis_dependent, arrhythmia_symptoms booleans from findings; eGFR as integer (or null if absent).
7. **evidence_ids**: main observation (latest final K), renal-function observation, case id — in descending relevance per the template.

## D. Care-management routing

1. Fetch the high-risk care-management protocol. Note `high_predictive_risk_min`, `complex_care_supporting_triggers`, pharmacist/social-work referral triggers, outreach rule, and `care_plan_minima` (qualitative list).
2. **risk_tier**: registry risk_score ≥ `high_predictive_risk_min` → high.
3. **program**: complex_care_management if supporting triggers are met (chronic conditions ≥ threshold, recent admission, dialysis/advanced CKD, heart failure, uncontrolled diabetes); else routine/not-eligible.
4. **priority_problems**: include one code per documented active problem/issue (diabetes, ESRD-on-dialysis, HF phenotype + volume-overload event, hyperphosphatemia, hypertension, polypharmacy, SDOH barriers, dialysis fatigue, behavioral health when a positive screen exists). Use the most specific code that matches the documented phenotype (e.g. an HFpEF + volume-overload code rather than a generic HF-admission code when both facts are present). Do not invent stage-4 CKD when the patient is ESRD.
5. **numeric_anchors**: copy risk_score (2 dp), hba1c_percent (1 dp), phosphorus_mg_dl (1 dp), blood_pressure "sys/dia", active_medication_count (integer) from the registry/observations. Include only chart facts that actually exist (e.g. omit eGFR if no eGFR observation is present).
6. **referrals**: pharmacist (med count ≥ threshold / insulin / high-risk diuretic-electrolyte), social_worker (≥ threshold moderate/severe SDOH domains), dialysis_care_coordination (ESRD), behavioral_health_monitoring (positive screen), transportation_benefits (transportation barrier). Do not add primary_care as a "referral" unless the protocol frames it so.
7. **outreach_stance**: permission-based plain language when the case states permission-based outreach is required (even if the member is engaged).
8. **care_plan_minima**: weekly_follow_up true (weekly contact initially); requires_member_stated_priority true when member barriers/preferences are disclosed; min_problem_count/min_disciplines from the protocol's "at least" thresholds.
9. **escalation_conditions**: include conditions tied to the patient's **documented** active problem domains (dialysis/volume-overload, HF decompensation, PHQ-9, dysglycemia, etc.). Do not add a hypertensive-urgency condition when the BP is not urgency-level, and do not add a medication-access-failure condition when no medication-access barrier is documented.
10. **source_provenance**: chart_facts = the numeric/registry facts actually present; member_disclosure_needed = member-disclosed barriers/preferences (transportation, financial-food, dialysis fatigue, care-goal preference).

## E. Observation-window retrieval and protocol gate

1. Fetch the observation-window protocol. Note `controlled_codes` (target code), `excluded_statuses`, `status_rule` (final only), window bounds, and ordering.
2. From `findings`: read target patient, target code, window `from` (inclusive) / `to` (exclusive), status rule.
3. Partition observations:
   - **matched**: code == target AND status == final AND patient == target AND `from` <= effective_time < `to`.
   - **excluded**: relevant distractors failing on **date, code, or status** only (not patient-mismatched ones).
   - Sort both lists by effective_time ascending, then observation_id ascending.
4. **latest_final** = matched observation with max effective_time; report observation_id, value (1 dp), effective_time.
5. **protocol_gate**: normal latest → `satisfies_recent_final_normal` (repeat_lab recommended=false, scheduled_time=null); low → `recent_final_low_repletion_needed`; critical/urgent → `recent_final_critical_or_urgent`; none in window → `no_final_lab_in_window`.
6. `lab_found` true iff matched is non-empty.

## Cross-family reminders
- Sets are exact: one wrong member fails the field. Include only members explicitly documented in the case `findings` or required by the protocol.
- Prefer protocol-supplied codes/values verbatim over recalled "correct" values.
- Echo timestamps with trailing `Z`; "next morning" = next day 08:00:00Z.
- When two readings of a field both seem defensible, prefer the one tied to an explicit protocol clause or an explicit present/absent finding over a generic clinical default.
