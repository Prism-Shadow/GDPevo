# Protocol Decision Logic

This reference provides clinical reasoning patterns for each protocol domain. Read it when the answer template alone does not make the protocol logic obvious, or when you need to confirm how to map clinical facts to template enum values.

## Respiratory Assessment (RESP-CAP-2026)

**Template**: `adult_respiratory_protocol_assessment`

### Assessment classification

- `community_acquired_pneumonia`: Final CXR shows consolidation AND respiratory viral PCR is negative. This is the default when imaging confirms pneumonia and viral causes are excluded.
- `viral_upper_respiratory_infection`: Final CXR shows no consolidation OR respiratory viral PCR is positive.
- `pneumonia_protocol_pending`: Used when protocol data is incomplete.

### Risk level

- `high`: SpO2 < 90% on room air, respiratory rate >= 30, systolic BP < 90, or any ED escalation red flag (confusion, sepsis concern, immunocompromise, multilobar disease).
- `moderate`: SpO2 90-93%, RR < 30, no ED-level red flags, CXR consolidation present.
- `low`: No consolidation, normal vitals, viral etiology.

### Disposition

- `ed_transfer`: Any high-risk criterion met.
- `outpatient_close_followup`: Moderate or low risk.

### Red flags

Map findings to enum values:
- Oxygen 92-93% → `hypoxemia_92_93`
- Oxygen < 90% → `hypoxemia_below_90`
- Pleuritic chest pain present → `pleuritic_chest_pain`
- Respiratory distress → `respiratory_distress`
- Confusion → `confusion`
- Hemoptysis → `hemoptysis`
- Persistent fever → `persistent_fever`
- Worsening shortness of breath → `worsening_shortness_of_breath`

### Antibiotic strategy selection

Check active allergies first:
- Penicillin allergy → avoid beta-lactams
- Sulfonamide allergy → avoid sulfa-containing regimens

Available strategies:
- `doxycycline_outpatient`: When penicillin and/or sulfonamide allergies are active. Doxycycline is a tetracycline-class antibiotic.
- `standard_outpatient_beta_lactam_plus_macrolide`: When no penicillin or macrolide allergies.
- `defer_antibiotic_selection_to_ed`: For ED transfer disposition.
- `supportive_care_no_antibiotic`: For viral URI where no consolidation is present.

### Safety checks

- `no_penicillin_or_sulfa`: `true` when the selected strategy avoids penicillin and sulfonamide classes.
- `no_normal_cxr_claim`: `true` when the CXR impression explicitly shows consolidation.
- `no_clear_lungs_claim`: `true` when lung findings are abnormal.

## Pediatric Head Injury (PEDS-HEAD-2026)

**Template**: pediatric head injury assessment

### Assessment classification

- `minor_head_injury_no_concussion_features`: No concussion symptoms, GCS 15, normal neuro exam.
- `mild_traumatic_brain_injury_without_loss_of_consciousness`: Concussion symptoms present (nausea, headache, coordination issues) but no LOC.
- `pediatric_head_injury_with_concussion_features`: Concussion symptoms plus one or more moderate findings.
- `severe_head_injury`: Any urgent-route trigger (GCS < 15, prolonged LOC, repeated vomiting, seizure, focal deficit, basilar skull signs, worsening severe headache).

### Risk tier

- `low`: GCS 15, no concussion symptoms, normal neuro exam, no urgent triggers.
- `intermediate`: Concussion findings present but no urgent triggers, GCS 15.
- `high`: Any urgent-route trigger from the protocol.

### Red flags and absent red flags

Red flags are clinical findings present in the case. Use:
- `head_impact` when mechanism involves head trauma
- `mild_nausea` when nausea finding is present
- `coordination_symptom_observe` when coordination exam is abnormal

Absent red flags are serious findings that are confirmed absent:
- `loss_of_consciousness`: LOC duration is zero or finding explicitly "absent"
- `repeated_vomiting`: Vomit count is zero
- `seizure`: No seizure finding
- `focal_weakness`: Neuro exam shows no focal weakness
- `worsening_headache`: Headache is mild and stable
- `basilar_skull_signs`: No basilar skull signs
- `photophobia`: No photophobia finding

Only include absent red flags that are explicitly addressed in the case findings. If a red flag is simply not mentioned, do not include it in absent_red_flags.

### Restrictions

- `relative_cognitive_physical_rest`: Any concussion symptoms present — per protocol "short cognitive rest with gradual return"
- `return_to_learn_accommodations`: School-age patient with concussion — per protocol "gradual return and accommodations"
- `no_high_risk_sports_until_cleared`: Per protocol "no same-day return; graded return after symptom resolution and clearance"
- `no_driving_until_symptom_free`: Patient is of driving age (varies by jurisdiction; for this protocol, apply when patient age and symptoms suggest driving risk)
- `no_driving_until_cleared`: Stronger restriction for cases with more significant findings
- `normal_activity_as_tolerated`: Low-risk cases with no concussion features

### Safety checks

- `no_false_loc`: `true` when LOC is confirmed absent (duration 0 or explicit "absent" finding).
- `no_false_vomiting`: `true` when vomiting is confirmed absent (count 0).
- `no_false_photophobia`: `true` when photophobia is not present in findings.

## Potassium Replacement (K-REPLETION-2026)

**Template**: `potassium_replacement_follow_up_lab_answer`

### Finding the latest potassium

The protocol code for serum potassium is `K`. Filter observations by:
1. `patient_id` matches the target patient
2. `code` is `K`
3. `status` is `final`

Among matching observations, select the one with the latest `effective_time`.

Do NOT use:
- Observations with `status: "preliminary"` (even if they have a later effective_time)
- Observations with code `6298-4` (whole blood potassium) when serum potassium is available — prefer the `K` code
- Whole-blood potassium observations — these have different reference ranges

### Urgent branch evaluation

Check these conditions from the protocol. If ANY are true, the urgent branch applies:

1. Potassium < 3.0 mmol/L
2. ECG abnormality present
3. Dialysis-dependent ESRD (check problems list for `N18.6` or dialysis schedule in care registry)
4. Severe renal contraindication
5. Symptoms: palpitations, syncope, or weakness with arrhythmia concern

### Routine dose calculation

When potassium is below target (3.5 mmol/L) and the urgent branch does NOT apply:

```
deficit = target - latest_value  (in mmol/L)
mEq = round(deficit / 0.1) * 10
round mEq to nearest 10
```

Example: K = 3.2 → deficit = 0.3 → 30 mEq

### Contraindications

- `dialysis_dependent`: `true` when problems include ESRD on dialysis (N18.6) or dialysis schedule exists
- `arrhythmia_symptoms`: `true` when palpitations, syncope, or arrhythmia concern are present
- `egfr`: The eGFR value from the most recent final observation with code `33914-3`, or null if unavailable

## Care Management Routing (CM-HIGH-RISK-2026)

**Template**: `care_management_routing_answer`

### Risk tier

- `high`: risk_score >= 0.75 from the care registry
- `moderate`: risk_score >= 0.5 but < 0.75
- `low`: risk_score < 0.5

### Program assignment

- `complex_care_management`: High risk tier AND at least 3 of: chronic_condition_count >= 3, recent admission, dialysis/advanced CKD, heart failure, uncontrolled diabetes (HbA1c > 8.0).
- `routine_case_management`: Moderate risk tier OR fewer than 3 complex-care triggers met.
- `not_eligible`: Low risk, no triggers.

### Priority problems

Use only problems with clinical evidence:
- `uncontrolled_diabetes`: HbA1c >= 8.0 or problem list includes diabetes with hyperglycemia
- `esrd_on_hemodialysis`: Problem list includes N18.6 or dialysis schedule present
- `hfpEF_post_volume_overload`: Heart failure problem plus recent volume-overload admission
- `hyperphosphatemia`: Phosphorus > 5.5 mg/dL or hyperphosphatemia in problem list
- `hypertension`: BP >= 140/90 or hypertension in problem list
- `polypharmacy`: active_medication_count >= 10
- `transportation_barrier`: SDOH transportation domain severity moderate or higher
- `financial_food_barrier`: SDOH food domain OR financial domain with food-related evidence
- `financial_medication_barrier`: SDOH financial domain with medication-related evidence
- `dialysis_fatigue`: Finding explicitly mentions post-dialysis fatigue
- `behavioral_health_need`: PHQ-9 score elevated or behavioral health concern in findings

### Referrals

- `pharmacist`: medication_count >= 10 OR insulin safety OR high-risk diuretic/electrolyte regimen
- `social_worker`: 2 or more moderate/severe SDOH domains
- `dialysis_care_coordination`: ESRD on dialysis
- `primary_care`: Routine care management cases
- `behavioral_health_monitoring`: PHQ-9 elevated
- `transportation_benefits`: Transportation SDOH domain present

### Outreach stance

- `permission_based_plain_language`: Member is reluctant, refusing, or has requested specific contact preferences. Use when findings indicate the patient wants calls after dialysis or has engagement preferences.
- `standard_scripted_outreach`: Standard outreach, no refusal.
- `directive_clinician_instruction`: Clinician-directed contact.
- `defer_until_patient_requests_contact`: Member explicitly refuses contact.

### Care plan minima

- `min_problem_count`: For complex care, at least 3 problems. For routine, at least 1.
- `weekly_follow_up`: `true` for high-risk complex care.
- `requires_member_stated_priority`: `true` when member disclosure of goals/preferences is documented.
- `min_disciplines`: Number of distinct referral disciplines needed (at least 2 for complex care with multiple referrals).

### Escalation conditions

- `missed_dialysis_or_volume_overload`: ESRD + recent volume-overload admission
- `dyspnea_weight_gain_or_ed_return`: Heart failure + recent admission
- `phq9_increase_or_item9_positive`: PHQ-9 >= 5 or item 9 positive
- `severe_hypoglycemia_or_hyperglycemia`: Diabetes + HbA1c > 9.0
- `hypertensive_urgency`: BP >= 180/110
- `medication_access_failure`: SDOH financial domain with medication barrier

### Source provenance

- `chart_facts`: Facts available from the medical record (risk_score, hba1c_percent, phosphorus_mg_dl, egfr, blood_pressure, active_medication_count, recent_admission, dialysis_schedule)
- `member_disclosure_needed`: Facts only available through member interview (transportation_barrier, financial_medication_barrier, financial_food_barrier, dialysis_fatigue, medication_access_barrier, care_goal_preference)

## Observation Window Retrieval (OBS-WINDOW-2026)

**Template**: observation-window retrieval and protocol-gate task

### Window definition

The window boundaries come from the case findings (`window_start` and `window_end`). The `from` is inclusive, the `to` is exclusive.

### Target code

Always `K` for serum potassium tasks.

### Matching observations

Filter observations:
1. `patient_id` matches the target patient
2. `code` matches the target code (`K`)
3. `status` is `final`
4. `effective_time` is >= window.from and < window.to

Sort: effective_time ascending, then observation_id ascending.

### Excluded observations

Include observations that are relevant to the review but fail one or more criteria:
- Out-of-window final K observations (e.g., just before the window)
- In-window K observations with non-final status (preliminary, canceled)
- In-window final observations with a different code that could distract (e.g., `NA` sodium)
- In-window K observations for a different patient

Sort: effective_time ascending, then observation_id ascending.

### Latest final

The matched observation with the latest effective_time. Extract observation_id, value_mmol_l (one decimal place), and effective_time.

### Protocol gate

- `satisfies_recent_final_normal`: Latest final K >= 3.5 (target)
- `recent_final_low_repletion_needed`: Latest final K < 3.5 and >= 3.0
- `recent_final_critical_or_urgent`: Latest final K < 3.0
- `no_final_lab_in_window`: No matching final K observations found

### Repeat lab

- `recommended`: `true` when protocol gate indicates low or critical potassium (repletion or urgent), `false` when normal.
- `scheduled_time`: When recommended, compute a reasonable follow-up time (typically next morning). Use null when not recommended.
