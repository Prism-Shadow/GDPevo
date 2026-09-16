# Protocol Decision Rules

This reference documents the decision rules, thresholds, and enum mappings for
all five clinical protocols available through the Harborview Synthetic Clinic.

## RESP-CAP-2026: Adult Respiratory Infection and CAP Assessment

**Case type**: acute_respiratory

### Red Flag Detection

| Clinical finding | Red flag enum |
|---|---|
| SpO2 92-93% on room air | hypoxemia_92_93 |
| SpO2 below 90% on room air | hypoxemia_below_90 |
| Pleuritic chest pain reported | pleuritic_chest_pain |
| Respiratory rate >= 30/min | respiratory_distress |
| Confusion present | confusion |
| Hemoptysis reported | hemoptysis |
| Persistent fever despite treatment | persistent_fever |
| Worsening shortness of breath reported | worsening_shortness_of_breath |

When multiple SpO2 readings exist, use the most recent. If any reading is in a
range, select the red flag matching the lowest value in that range.

### ED Escalation Thresholds

Any of the following triggers disposition = ed_transfer:

- SpO2 < 90% on room air
- Respiratory rate >= 30/min
- Systolic BP < 90 mmHg
- Other red flags: confusion, sepsis concern, immunocompromise, multilobar disease

### Risk Level

- **high**: Any ED escalation threshold is met.
- **moderate**: Red flags present but no ED escalation threshold met.
- **low**: No red flags present; vital signs within normal ranges.

### Disposition

- **ed_transfer**: Any ED escalation threshold met.
- **outpatient_close_followup**: Otherwise.

### Recommended Tests

| Clinical indication | Test enum |
|---|---|
| CXR indicated (respiratory symptoms, suspected CAP) | CXR-2V |
| SpO2 borderline or recheck needed | PULSE_OX_RECHECK |
| Respiratory viral panel indicated | SARS_FLU_RSV_PCR |
| Basic labs needed | CBC_BASIC |

### Medication Plan: Antibiotic Strategy

Select the antibiotic strategy based on patient allergies and clinical picture:

- **doxycycline_outpatient**: Outpatient CAP with penicillin and/or sulfonamide allergies (or when beta-lactam/macrolide contraindicated).
- **standard_outpatient_beta_lactam_plus_macrolide**: Outpatient CAP with no penicillin allergy.
- **supportive_care_no_antibiotic**: Viral URI pattern confirmed (negative PCR, no consolidation on CXR, mild symptoms).
- **defer_antibiotic_selection_to_ed**: When ED transfer is indicated.

### Allergen Mapping for avoid_allergens

| Active allergy contains | avoid_allergens enum |
|---|---|
| "penicillin" | penicillin |
| "sulfonamide" | sulfonamide |
| "erythromycin", "clarithromycin", "azithromycin" | macrolide |
| "doxycycline", "tetracycline", "minocycline" | tetracycline |

Use case-insensitive substring match on the allergen field. Only include
allergens with status = active.

### Stabilization Actions

- **supplemental_oxygen**: SpO2 < 92% on room air.
- **urgent_ed_transfer**: Any ED escalation trigger met.

### Follow-Up

- timeframe_hours: 48 (from protocol: outpatient_follow_up_hours)
- route: primary_care_recheck for outpatient disposition; emergency_department for ED transfer.

### Return Precautions

Use the protocol return_precaution_codes mapped to template enum values:

| Protocol code | Template enum |
|---|---|
| chest_pain | chest_pain |
| confusion | confusion |
| hemoptysis (implied) | hemoptysis |
| oxygen_below_90 | hypoxia |
| persistent_fever | persistent_fever |
| worsening_dyspnea | worsening_shortness_of_breath |

### Safety Checks

- **no_penicillin_or_sulfa**: True when the patient has active penicillin or sulfonamide allergies AND the selected antibiotic strategy avoids both classes.
- **no_normal_cxr_claim**: True when CXR findings are abnormal (consolidation, infiltrate, etc.) — i.e., do NOT claim the CXR was normal.
- **no_clear_lungs_claim**: True when the assessment does NOT claim clear lungs — lung exam or imaging shows abnormality (consolidation present).

## PEDS-HEAD-2026: Pediatric Head Injury Clinic Triage

**Case type**: pediatric_head_injury

### Red Flag Detection

Red flags (present symptoms/findings):

| Clinical finding | Red flag enum |
|---|---|
| Head impact occurred | head_impact |
| Mild nausea reported | mild_nausea |
| Mild coordination abnormality on exam | coordination_symptom_observe |
| Loss of consciousness occurred | loss_of_consciousness |
| Repeated vomiting | repeated_vomiting |
| Seizure activity | seizure |
| Focal weakness on exam | focal_weakness |
| Worsening/severe headache | worsening_headache |
| Signs of basilar skull fracture | basilar_skull_signs |
| Photophobia reported | photophobia |

Absent red flags: List all serious trigger codes from the absent_red_flags
allowed list that are NOT present. Only include codes from the template's
absent_red_flags allowed_values list. The absent_red_flags list does NOT
include head_impact, mild_nausea, or coordination_symptom_observe — those
are only for the red_flags list.

### Primary Assessment

| Clinical pattern | Assessment enum |
|---|---|
| GCS 15, no LOC, mild symptoms, no urgent triggers | mild_traumatic_brain_injury_without_loss_of_consciousness |
| GCS 15, no LOC, but concussion features present | pediatric_head_injury_with_concussion_features |
| GCS 15, no LOC, minimal symptoms | minor_head_injury_no_concussion_features |
| GCS < 15, LOC, or urgent triggers | severe_head_injury |

### Risk Tier

- **low**: GCS 15, no LOC, no concussion features, minimal symptoms.
- **intermediate**: GCS 15, no LOC, but concussion features or moderate symptoms present.
- **high**: Any urgent route trigger (protocol urgent_route_triggers) present.

### Urgent Route Triggers (from protocol)

Any of these -> high risk, ed_evaluation_ct_consideration:

- repeated_vomiting
- worsening_severe_headache
- seizure
- basilar_skull_signs
- focal_neurologic_deficit
- gcs_below_15
- prolonged_loss_of_consciousness

### Disposition

- **ed_evaluation_ct_consideration**: Any urgent route trigger met.
- **home_observation_with_followup**: Otherwise.

### Imaging Recommendation

- **no_immediate_ct**: Low or intermediate risk, GCS 15, no urgent triggers.
- **ct_or_ed_per_protocol**: Intermediate risk with concerning but non-urgent features.
- **urgent_ct**: High risk, urgent triggers present.

### Restrictions

Derive from protocol restrictions section:

- relative_cognitive_physical_rest matches protocol school guidance (short cognitive rest)
- return_to_learn_accommodations matches protocol school guidance (gradual return with accommodations)
- no_high_risk_sports_until_cleared matches protocol return_to_play (no same-day return; graded return after clearance)
- no_driving_until_symptom_free matches protocol driving guidance (avoid driving while symptomatic)
- no_driving_until_cleared: Use when the patient is a minor and driving restriction is categorical.
- normal_activity_as_tolerated: Use for low risk with minimal symptoms.

### Follow-Up

- timeframe_hours: 48 for intermediate risk; 24 for low risk.
- route: primary_care_or_concussion_recheck for home observation; emergency_department for ED disposition; neurology_referral for high risk; return_if_worse_only for very low risk.

### Safety Checks

- **no_false_loc**: True when the clinical data confirms NO loss of consciousness.
- **no_false_vomiting**: True when the clinical data confirms NO vomiting/repeated vomiting.
- **no_false_photophobia**: True when the clinical data confirms NO photophobia.

## K-REPLETION-2026: Potassium Replacement and Escalation

**Case type**: potassium_repletion

### Finding the Latest Final Serum Potassium

1. Filter observations where code = "K" AND status = "final".
2. Ignore observations where code = "6298-4" (whole blood potassium — different matrix).
3. Select the observation with the most recent effective_time among the filtered set.

### Urgent Branch (any true -> do NOT use routine oral repletion dose)

1. dialysis_dependent_esrd: Check problems list for ESRD/dialysis codes AND care_registry if present.
2. ecg_abnormality: ECG observation shows abnormal findings (not normal sinus rhythm).
3. potassium_less_than_3.0: Latest serum K < 3.0 mmol/L.
4. severe_renal_contraindication: eGFR observation shows severely impaired renal function.
5. symptoms: Patient reports palpitations, syncope, or weakness with arrhythmia concern.

### Routine Oral Dose Calculation

Only when the urgent branch is completely false:

1. deficit = target_potassium_mmol_l - latest_potassium_value (3.5 - measured value)
2. mEq = deficit / 0.1 * 10 (protocol: mEq_per_0_1_mmol_l_below_target = 10)
3. Round to nearest 10 mEq (protocol: round_to_nearest_mEq = 10)
4. If the calculated dose rounds to 0, potassium_plan is no_replacement.

### Potassium Plan Enum

| Condition | Plan |
|---|---|
| Urgent branch triggered | urgent_escalation |
| Contraindication present (dialysis, severe renal) | hold_due_to_contraindication |
| Deficit exists, urgent branch false, no contraindication | routine_oral_repletion |
| No deficit (K >= 3.5) | no_replacement |

### Medication Order

When plan = routine_oral_repletion:

- ndc: "40032-917-01" (protocol controlled code for routine oral potassium)
- medication: "potassium chloride oral"
- route: "PO"
- frequency: "once" (single dose)
- status: "recommended"

When plan = urgent_escalation:

- ndc: null
- medication: null
- route: "per_urgent_protocol"
- frequency: "per_urgent_protocol"
- status: "defer_to_urgent_clinician"

When plan = no_replacement:

- ndc: null
- medication: null
- route: null
- frequency: null
- status: "not_recommended"

### Follow-Up Lab

- loinc: "2823-3" (serum potassium)
- scheduled_time: Next morning at 08:00 local time (UTC). Compute from current_time:
  - Extract the date, add one day, set time to 08:00:00Z.
  - If the scheduled time is before current_time + 6h, add another day.

When plan = no_replacement, follow-up may not be needed (null both fields
if the template permits nulls on those fields; check the template).

### Urgent Actions

When urgent branch triggered, include applicable actions in clinical sequence:

1. urgent_clinician_notification (always when urgent)
2. ekg_now (when ECG abnormality or arrhythmia concern)
3. telemetry_or_ed_evaluation (when K critically low or symptoms present)

Use empty list when no urgent actions are required.

### Contraindications Object

- dialysis_dependent: boolean — true when problem list or care_registry confirms ESRD/dialysis.
- arrhythmia_symptoms: boolean — true when palpitations, syncope, or arrhythmia symptoms reported.
- egfr: integer or null — value from observation with code "33914-3", rounded to whole integer.

### Evidence IDs

List in descending relevance: the latest serum potassium observation_id first,
then the eGFR observation_id, then any other supporting observation or case IDs.

## CM-HIGH-RISK-2026: High-Risk Care-Management Routing

**Case type**: care_management

### Risk Tier

- **high**: risk_score >= 0.75 (protocol: high_predictive_risk_min).
- **moderate**: risk_score >= 0.5 but < 0.75.
- **low**: risk_score < 0.5.

### Program Eligibility

complex_care_management when ALL of:
1. chronic_condition_count >= 3 (protocol trigger)
2. At least one supporting trigger present:
   - recent_admission
   - dialysis_or_advanced_ckd
   - heart_failure
   - uncontrolled_diabetes
3. risk_score >= 0.75

routine_case_management when risk is moderate and some triggers present.

not_eligible when low risk and no significant triggers.

### Priority Problems

Map from problems list, labs, and SDOH to allowed enum values:

| Clinical condition | Priority problem enum |
|---|---|
| HbA1c >= 8.0 or diabetes with hyperglycemia | uncontrolled_diabetes |
| ESRD on dialysis (problem code N18.6) | esrd_on_hemodialysis |
| CKD stage 4 (problem code N18.4) | chronic_kidney_disease_stage_4 |
| Heart failure with recent admission | heart_failure_recent_admission |
| Diastolic HF post volume overload | hfpEF_post_volume_overload |
| Phosphorus > 5.5 mg/dL | hyperphosphatemia |
| Hypertension diagnosis with elevated BP | hypertension |
| Medication count >= 10 | polypharmacy |
| Transportation SDOH domain present | transportation_barrier |
| Financial SDOH with food concern | financial_food_barrier |
| Financial SDOH with medication concern | financial_medication_barrier |
| Dialysis fatigue reported | dialysis_fatigue |
| PHQ-9 >= 5 or behavioral health need noted | behavioral_health_need |

### Numeric Anchors

- risk_score: from care_registry.risk_score (2 decimal places).
- hba1c_percent: from observation with code "4548-4" (1 decimal place).
- phosphorus_mg_dl: from observation with code "2777-1" (1 decimal place).
- blood_pressure: Format as "systolic/diastolic" from SBP (code "8480-6") and DBP (code "8462-4") observations with the same effective_time. Use the most recent pair.
- active_medication_count: From care_registry.medication_count or by counting active medications with status = "active".

### Referrals

| Trigger | Referral enum |
|---|---|
| Medication count >= 10 | pharmacist |
| Insulin in medication list | pharmacist |
| High-risk diuretic/electrolyte regimen | pharmacist |
| >= 2 SDOH domains moderate or severe | social_worker |
| ESRD on dialysis | dialysis_care_coordination |
| Recent admission or complex care | primary_care |
| PHQ-9 >= 5 or behavioral health concern | behavioral_health_monitoring |
| Transportation SDOH domain | transportation_benefits |

### Outreach Stance

- **permission_based_plain_language**: Member is reluctant/refusing or has expressed preferences about contact timing. Use when the protocol specifies permission-based outreach.
- **standard_scripted_outreach**: Member is engaged and receptive.
- **directive_clinician_instruction**: When clinical urgency requires directive communication.
- **defer_until_patient_requests_contact**: When member explicitly declines outreach.

The protocol note: "Use permission-based outreach when the member is reluctant or refusing."

### Care Plan Minima

- min_problem_count: 3 (match the number of main priority problems, at least 3).
- weekly_follow_up: true (protocol: weekly_contact_initially).
- requires_member_stated_priority: true (protocol includes barrier_resolution and clear_escalation_conditions).
- min_disciplines: 2 (at least 2 referral disciplines needed for complex care).

### Escalation Conditions

Select from the allowed list based on clinical risks:

- missed_dialysis_or_volume_overload: ESRD patient with recent volume overload admission.
- dyspnea_weight_gain_or_ed_return: Heart failure with recent admission.
- phq9_increase_or_item9_positive: PHQ-9 score elevated or behavioral health concern.
- severe_hypoglycemia_or_hyperglycemia: Uncontrolled diabetes with HbA1c >= 9.0.
- hypertensive_urgency: BP >= 180/110.
- medication_access_failure: Financial medication barrier reported.

### Source Provenance

**chart_facts**: Values derived from observations or registry (not member-reported):
- risk_score, hba1c_percent, phosphorus_mg_dl, egfr, blood_pressure,
  active_medication_count, recent_admission, dialysis_schedule

Include only the facts whose values you actually used in the answer.

**member_disclosure_needed**: Facts sourced from SDOH entries with source = "member-disclosed" or from care-manager notes:
- transportation_barrier, financial_medication_barrier, financial_food_barrier,
  dialysis_fatigue, medication_access_barrier, care_goal_preference

Include only the facts that came through member disclosure (not from automated feeds).

## OBS-WINDOW-2026: Observation Window Interpretation

**Case type**: observation_window

### Window Definition

- from: Inclusive start timestamp from findings (window_start).
- to: Exclusive end timestamp from findings (window_end).

### Matching Criteria

An observation is a match when ALL of:
1. patient_id matches the case's patient_id
2. code matches the target_code (typically "K")
3. status = "final"
4. effective_time >= window.from AND effective_time < window.to

### Excluded Observations

Include observations that are relevant to the case review but fail at least one
matching criterion. Common exclusion reasons:

- Outside the date window (effective_time before from or on/after to)
- Wrong observation code (e.g., "NA" for sodium when target is "K")
- Wrong patient (patient_id does not match the case's patient)
- Non-final status (preliminary, entered-in-error, cancelled)

Only include excluded observations that are plausibly relevant: they belong to
the same case, have a relevant code, or appear in the case's observation list.

### Sorting Rules

- matched_observation_ids: Sort by effective_time ascending, then observation_id ascending.
- excluded_observation_ids: Sort by effective_time ascending when available, then observation_id ascending.

### Latest Final

Populate only when lab_found is true:

- observation_id: The last entry in matched_observation_ids.
- value_mmol_l: value_number from that observation (to 1 decimal place).
- effective_time: effective_time from that observation.

When lab_found is false, latest_final is null.

### Protocol Gate

Determine from the latest final value:

| Latest K value | Protocol gate |
|---|---|
| >= 3.5 and < 5.0 | satisfies_recent_final_normal |
| >= 3.0 and < 3.5 | recent_final_low_repletion_needed |
| < 3.0 or >= 5.5 | recent_final_critical_or_urgent |
| No final lab found | no_final_lab_in_window |

### Repeat Lab

- recommended: false when protocol_gate = satisfies_recent_final_normal; true otherwise.
- scheduled_time: null when not recommended; otherwise compute an appropriate future time.
