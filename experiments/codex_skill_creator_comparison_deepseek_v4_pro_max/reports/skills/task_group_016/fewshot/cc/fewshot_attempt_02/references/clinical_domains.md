# Clinical Domain Patterns

This reference describes domain-specific patterns you will encounter across clinic protocol tasks. For each domain, the key question types, reasoning patterns, and decision thresholds are outlined.

Read the section matching the current task's domain **after** you have gathered all clinical data from the API, and before you build the output JSON.

## Respiratory Protocol (Community-Acquired Pneumonia)

**Typical template keys:** `primary_assessment`, `risk_level`, `disposition`, `red_flags`, `recommended_tests`, `medication_plan`, `stabilization_actions`, `follow_up`, `return_precautions`, `evidence_ids`, `safety_checks`.

### Key Decision Points

**Primary assessment** — determined by the combination of:
- Imaging findings (CXR report impression: infiltrate vs. normal vs. pending)
- Clinical presentation (vitals, exam findings)
- Protocol criteria for CAP vs. viral URI

If imaging shows an infiltrate consistent with pneumonia, the assessment is community-acquired pneumonia. If imaging is not yet available but clinical suspicion is high, use pneumonia_protocol_pending. If imaging is normal and vitals suggest a viral process, the assessment is viral_upper_respiratory_infection.

**Risk level** — driven by:
- Oxygen saturation (SPO2): below 90% means high risk; 92-93% means moderate risk with hypoxemia red flag
- Presence of confusion or respiratory distress elevates risk
- Stable vitals without red flags: low risk

**Disposition** — outpatient_close_followup for moderate/low risk patients who are clinically stable. ed_transfer when risk is high or stabilization is needed.

**Red flags** — extract from observations and imaging:
- SPO2: 92-93% maps to hypoxemia_92_93; below 90% maps to hypoxemia_below_90
- Pleuritic chest pain, respiratory distress, confusion, hemoptysis from case notes
- Persistent fever, worsening shortness of breath from clinical history

Only include red flags actually present in the clinical data. Do not guess.

**Recommended tests** — protocol-guided:
- CXR-2V when imaging is needed for diagnosis or was ordered
- PULSE_OX_RECHECK when SPO2 is borderline
- SARS_FLU_RSV_PCR for respiratory pathogen testing
- CBC_BASIC for infection workup

**Medication plan** — allergy-aware:
- Always check allergies first. The patient's allergy list drives avoid_allergens.
- For outpatient CAP without penicillin/sulfonamide allergy: doxycycline_outpatient or standard_outpatient_beta_lactam_plus_macrolide depending on protocol guidance
- For patients with penicillin allergy: avoid penicillin and sulfonamide; doxycycline is often the safe choice
- For viral URI: supportive_care_no_antibiotic
- For ED transfer: defer_antibiotic_selection_to_ed
- When an antibiotic is recommended, fill out medication, dose, route, frequency, and duration_days with protocol-recommended values
- When no antibiotic is recommended, set medication, dose, route, frequency to null and duration_days to null

**Stabilization actions** — only when acutely indicated:
- supplemental_oxygen for hypoxemia below 90%
- urgent_ed_transfer for high-risk patients needing escalation
- Empty list for stable patients

**Follow-up** — timeframe_hours as an integer: 48 for outpatient CAP recheck. route: primary_care_recheck for outpatient, emergency_department for ED transfer, pulmonology_followup for specialist referral.

**Return precautions** — use the full set of return precautions that apply to the patient's condition. For a CAP patient, this typically includes chest_pain, confusion, hemoptysis, hypoxia, persistent_fever, worsening_shortness_of_breath — all of them, since any of these could signal deterioration.

**Evidence IDs** — include the case ID, any imaging IDs that were reviewed, and the key observation IDs (especially SPO2) that drove your decisions. Use the actual identifiers from API responses.

**Safety checks** — three boolean assertions about what was NOT found:
- no_penicillin_or_sulfa: true when neither penicillin nor sulfonamide allergies are present in the patient's allergy list
- no_normal_cxr_claim: true when CXR findings are abnormal (infiltrate, opacity, consolidation) and the CXR is not normal
- no_clear_lungs_claim: true when lung auscultation findings are abnormal, not clear

## Pediatric Head Injury Protocol

**Typical template keys:** `primary_assessment`, `risk_tier`, `disposition`, `imaging_recommendation`, `red_flags`, `absent_red_flags`, `restrictions`, `follow_up`, `evidence_ids`, `safety_checks`.

### Key Decision Points

**Primary assessment** — determined by the injury mechanism, symptoms, and exam findings:
- minor_head_injury_no_concussion_features: head impact without concussion symptoms
- mild_traumatic_brain_injury_without_loss_of_consciousness: concussion symptoms present but no LOC
- pediatric_head_injury_with_concussion_features: multiple concussion features present
- severe_head_injury: LOC, seizure, focal weakness, or basilar skull signs present

The critical discriminators: loss of consciousness, coordination symptoms, nausea, and headache severity.

**Risk tier** — driven by red flag count and severity:
- low: minimal symptoms, no concerning red flags
- intermediate: some red flags present (head_impact with mild_nausea or coordination_symptom_observe) but no high-risk red flags
- high: severe red flags present (LOC, repeated vomiting, seizure, focal weakness, basilar skull signs)

**Disposition and imaging** — paired decisions:
- home_observation_with_followup + no_immediate_ct: for low and intermediate risk
- ed_evaluation_ct_consideration + ct_or_ed_per_protocol: for severe symptoms
- urgent_ct: only for clear high-risk findings

**Red flags and absent red flags** — the allowed_values list covers ALL possible red flags. Partition them into two lists:
- red_flags: every red flag that is PRESENT in the clinical data
- absent_red_flags: every red flag from the list that is ABSENT from the clinical data

Common present red flags: head_impact (the injury itself), mild_nausea, coordination_symptom_observe.
Common absent red flags: loss_of_consciousness, repeated_vomiting, seizure, focal_weakness, worsening_headache, basilar_skull_signs, photophobia.

Review each red flag against the clinical observations and notes. Do not leave any allowed value unassigned.

**Restrictions** — based on assessment severity:
- relative_cognitive_physical_rest: for any concussion-features case
- return_to_learn_accommodations: for school-age patients with cognitive symptoms
- no_high_risk_sports_until_cleared: for any head injury with concussion features
- no_driving_until_symptom_free: for adolescent patients with concussion symptoms
- normal_activity_as_tolerated: for minor head injury without concussion features

**Follow-up** — timeframe_hours: 24-72 as integer hours based on risk. route: primary_care_or_concussion_recheck for home observation; emergency_department for ED disposition; neurology_referral for severe cases; return_if_worse_only for minimal risk.

**Safety checks** — three boolean assertions about absent findings:
- no_false_loc: true when LOC is genuinely absent (not present in data)
- no_false_vomiting: true when repeated vomiting is absent
- no_false_photophobia: true when photophobia is absent

Do not mark these true if the finding is actually present in the clinical data.

## Potassium Replacement Protocol

**Typical template keys:** `task_id`, `case_id`, `patient_id`, `current_time`, `latest_potassium`, `replacement_required`, `potassium_plan`, `oral_dose_mEq`, `medication_order`, `follow_up_lab`, `urgent_actions`, `contraindications`, `evidence_ids`.

### Key Decision Points

**Current time** — the clinical review time. Use a reasonable timestamp consistent with the case data (typically a time shortly after the latest observation). ISO-8601 UTC with trailing Z.

**Latest potassium** — find the most recent `final` observation with code `K` for the patient. Extract:
- observation_id: the actual observation identifier from the API
- value_mmol_l: the numeric potassium value (one decimal place)
- effective_time: the observation's effective time (ISO-8601 UTC with Z)

**Replacement required** — boolean driven by potassium thresholds. A potassium below 3.5 mmol/L generally means replacement is required. If contraindications are present (dialysis-dependent, arrhythmia symptoms), replacement may still be required but under a different plan.

**Potassium plan** — selected from:
- routine_oral_repletion: potassium is low but not critical, no contraindications, oral replacement is appropriate
- no_replacement: potassium is normal and replacement is not indicated
- urgent_escalation: potassium is critically low (below 3.0) or arrhythmia symptoms are present
- hold_due_to_contraindication: contraindication prevents safe replacement

**Oral dose mEq** — when routine_oral_repletion applies, use protocol-recommended dose (commonly 20-40 mEq as an integer). Set to null when no replacement is recommended.

**Medication order** — when replacement is recommended:
- ndc: the medication code from the protocol (string like "40032-917-01")
- medication: "potassium chloride oral" or protocol-specified name
- route: "PO" for oral
- frequency: "once" for a single dose
- status: "recommended"

When no replacement is recommended:
- set ndc, medication, route, frequency to null
- status: "not_recommended"

When deferring to urgent clinician:
- ndc, medication: null; route: "per_urgent_protocol"; frequency: "per_urgent_protocol"; status: "defer_to_urgent_clinician"

**Follow-up lab** — when replacement is given:
- loinc: "2823-3" (the LOINC code for serum potassium)
- scheduled_time: a time approximately 24 hours after the current review time, ISO-8601 UTC with Z

When no replacement, set both to null.

**Urgent actions** — only when potassium is critically low or arrhythmia symptoms are present. Use clinical action sequence: urgent_clinician_notification first, then ekg_now, then telemetry_or_ed_evaluation. Empty list when no urgent actions are needed.

**Contraindications** — three boolean/numeric fields:
- dialysis_dependent: true when the patient is on dialysis (from problems or care-registry)
- arrhythmia_symptoms: true when arrhythmia symptoms are documented
- egfr: the patient's most recent eGFR value as integer mL/min/1.73m2, or null if not available

**Evidence IDs** — the key observation ID for the potassium result, plus any renal function observation ID. List in descending relevance.

## Care Management Routing Protocol

**Typical template keys:** `task_id`, `case_id`, `patient_id`, `risk_tier`, `program`, `priority_problems`, `numeric_anchors`, `referrals`, `outreach_stance`, `care_plan_minima`, `escalation_conditions`, `source_provenance`.

### Key Decision Points

**Patient identifier** — always retrieve by querying the case first, then the patient endpoint.

**Risk tier** — driven by the risk_score from the care-registry:
- high: risk_score around 0.80 or above, multiple uncontrolled conditions, recent admission
- moderate: elevated risk_score but fewer complicating factors
- low: well-controlled conditions, low risk_score

**Program** — determined by risk tier and complexity:
- complex_care_management: high risk tier, multiple priority problems, recent admission, social barriers
- routine_case_management: moderate risk tier, fewer complicating factors
- not_eligible: low risk tier, minimal needs

**Priority problems** — extract from problems endpoint, observations (labs), and care-registry. Select the relevant codes from the allowed_values list. Common patterns:
- Uncontrolled diabetes → uncontrolled_diabetes (when hba1c is elevated, typically above 8.0)
- ESRD on dialysis → esrd_on_hemodialysis (when dialysis_schedule is present)
- Heart failure → hfpEF_post_volume_overload or heart_failure_recent_admission (from problems)
- Elevated phosphorus → hyperphosphatemia (from labs)
- Elevated blood pressure → hypertension
- High medication count → polypharmacy
- SDOH barriers → transportation_barrier, financial_food_barrier, financial_medication_barrier
- Behavioral health needs → behavioral_health_need

**Numeric anchors** — extract exact values from care-registry and observations:
- risk_score: two decimal places (e.g., 0.84)
- hba1c_percent: one decimal place
- phosphorus_mg_dl: one decimal place
- blood_pressure: string format "systolic/diastolic" (e.g., "152/88")
- active_medication_count: integer count

**Referrals** — based on priority problems and SDOH:
- pharmacist for polypharmacy or medication access issues
- social_worker for SDOH barriers
- dialysis_care_coordination for ESRD patients
- primary_care for general coordination
- behavioral_health_monitoring for behavioral health needs
- transportation_benefits for transportation barriers

**Outreach stance** — permission_based_plain_language for complex patients needing trust-building. standard_scripted_outreach for routine cases. directive_clinician_instruction for urgent clinical needs. defer_until_patient_requests_contact for minimal-need patients.

**Care plan minima** — based on risk tier and complexity:
- min_problem_count: for high risk with complex needs, 3; for moderate, 2; for low, 1
- weekly_follow_up: true for high risk; false for moderate/low
- requires_member_stated_priority: true when patient engagement is critical (SDOH barriers, complex cases); false for straightforward cases
- min_disciplines: 2 for complex cases needing multiple specialists; 1 for simpler cases

**Escalation conditions** — select from the allowed_values based on the patient's conditions:
- ESRD patient → missed_dialysis_or_volume_overload
- Heart failure → dyspnea_weight_gain_or_ed_return
- Behavioral health → phq9_increase_or_item9_positive
- Diabetes → severe_hypoglycemia_or_hyperglycemia
- Hypertension → hypertensive_urgency
- Medication barriers → medication_access_failure

**Source provenance** — partition data sources:
- chart_facts: data that comes from the medical record (labs, vitals, registry). Common: risk_score, hba1c_percent, phosphorus_mg_dl, active_medication_count, blood_pressure, recent_admission, dialysis_schedule, egfr.
- member_disclosure_needed: data that requires the patient to self-report (SDOH barriers, preferences). Common: transportation_barrier, financial_medication_barrier, financial_food_barrier, dialysis_fatigue, medication_access_barrier, care_goal_preference.

## Lab Observation Window / Protocol Gate

**Typical template keys:** `task_id`, `case_id`, `patient_id`, `window`, `target_code`, `lab_found`, `matched_observation_ids`, `excluded_observation_ids`, `latest_final`, `protocol_gate`, `repeat_lab`.

### Key Decision Points

**Window** — the date range for the observation search. Determined from the task context (e.g., "March 2026" means from "<WINDOW_START>" to "<WINDOW_END>"). Use inclusive start, exclusive end.

**Target code** — the observation code to search for. For potassium tasks, this is "K".

**Lab found** — true when at least one `final` observation with the target code exists for the patient within the window. false otherwise.

**Finding matching observations:**
- Filter all observations by patient_id, code, and effective_time range
- Only include `final` status observations
- Sort by effective_time ascending, then observation_id ascending

**Finding excluded observations** — identify observations that are relevant to the task but do NOT qualify:
- Same patient and target code but outside the window (effective_time before or after)
- Same patient and target code but not `final` status (e.g., `preliminary`)
- Same patient and window but wrong code (e.g., `NA` instead of `K`)
- Sort by effective_time ascending when available, then observation_id ascending

**Latest final** — when lab_found is true:
- Take the last matching observation by effective_time
- Extract observation_id, value_mmol_l (one decimal place), effective_time
- When lab_found is false, latest_final is null (the template may mark it as nullable)

**Protocol gate** — determined by the latest final potassium value:
- satisfies_recent_final_normal: potassium is within normal range (approximately 3.5-5.0 mmol/L)
- recent_final_low_repletion_needed: potassium is below normal range and replacement is needed
- recent_final_critical_or_urgent: potassium is critically low or critically high
- no_final_lab_in_window: no qualifying lab result exists in the window

**Repeat lab** — recommended when the potassium is abnormal and follow-up is needed:
- recommended: false when potassium is normal (no repeat needed); true when abnormal
- scheduled_time: null when not recommended; a future ISO-8601 UTC timestamp when recommended
