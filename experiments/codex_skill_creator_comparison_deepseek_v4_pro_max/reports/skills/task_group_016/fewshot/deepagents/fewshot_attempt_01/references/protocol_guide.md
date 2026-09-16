## Protocol Decision Rules

Each protocol at `/api/protocols/{protocol_id}` returns:

```json
{
  "protocol_id": "...",
  "title": "...",
  "version": "...",
  "body": {
    "scope": "...",
    "authoritative_statuses": ["final"],
    "controlled_codes": { ... },
    ...
  }
}
```

### RESP-CAP-2026: Adult Respiratory and CAP Assessment

**Decision sequence:**

1. Read the case composite. Collect findings for: current time, chief complaint,
   cough, dyspnea, pleuritic chest pain, confusion, oxygen saturation, respiratory
   rate, systolic BP, temperature, occupational exposure, and allergy constraints.
2. Read the CXR imaging impression and check for consolidation.
3. Map allergies to avoid list: penicillin allergy → avoid `penicillin`,
   sulfonamide allergy → avoid `sulfonamide`.

**ED escalation triggers (check all):**
- SpO2 < 90% (`oxygen_saturation_room_air_less_than: 90`)
- Respiratory rate >= 30 (`respiratory_rate_at_least: 30`)
- Systolic BP < 90 (`systolic_bp_less_than: 90`)
- Other red flags: confusion, sepsis concern, immunocompromise, multilobar disease

**If any ED trigger fires:** disposition = `ed_transfer`, stabilization includes
`supplemental_oxygen` or `urgent_ed_transfer`, defer antibiotic selection to ED.

**If no ED trigger fires:**
- SpO2 92-93% → red flag `hypoxemia_92_93`
- SpO2 < 92% → red flag `hypoxemia_below_90`
- Pleuritic chest pain present → red flag `pleuritic_chest_pain`
- Respiratory distress → `respiratory_distress`
- Confusion → `confusion`
- Hemoptysis → `hemoptysis`
- Persistent fever → `persistent_fever`
- Worsening shortness of breath → `worsening_shortness_of_breath`

- Primary assessment: CXR shows consolidation + negative viral PCR →
  `community_acquired_pneumonia`. Clear CXR with symptoms → `viral_upper_respiratory_infection`.
  Pending results → `pneumonia_protocol_pending`.
- Risk level: SpO2 <= 93% → `moderate`; otherwise `low` (unless ED triggers force `high`).
- Disposition: `outpatient_close_followup` if not ED.
- Follow-up: `primary_care_recheck` at 48 hours.
- Return precautions: use codes from `return_precaution_codes` (map to template enums).
- Recommended tests: CXR-2V, PULSE_OX_RECHECK, SARS_FLU_RSV_PCR (if not done), CBC_BASIC.
- Antibiotic: choose strategy avoiding allergens. Doxycycline if both penicillin
  and sulfa must be avoided.

### PEDS-HEAD-2026: Pediatric Head Injury Triage

**Decision sequence:**

1. Check urgent triggers:
   - `repeated_vomiting`, `worsening_severe_headache`, `seizure`,
     `basilar_skull_signs`, `focal_neurologic_deficit`, `gcs_below_15`,
     `prolonged_loss_of_consciousness`.
2. If any urgent trigger fires: disposition = `ed_evaluation_ct_consideration`,
   imaging = `ct_or_ed_per_protocol` or `urgent_ct`, risk tier = `high`.
3. If no urgent triggers, check for concussion features:
   - Head impact → `head_impact`
   - Mild nausea → `mild_nausea`
   - Coordination issues → `coordination_symptom_observe`
   - Photophobia (if present) → `photophobia`
4. Determine absent red flags from: `loss_of_consciousness`, `repeated_vomiting`,
   `seizure`, `focal_weakness`, `worsening_headache`, `basilar_skull_signs`,
   `photophobia` — include any that are NOT present.
5. Primary assessment:
   - Concussion features + no LOC → `mild_traumatic_brain_injury_without_loss_of_consciousness`
   - LOC present → `pediatric_head_injury_with_concussion_features` or `severe_head_injury`
   - No concussion features → `minor_head_injury_no_concussion_features`
6. Risk tier: concussion features without urgent triggers → `intermediate`.
   No concussion features → `low`. Urgent triggers → `high`.
7. Disposition: non-urgent → `home_observation_with_followup`.
8. Imaging: non-urgent → `no_immediate_ct`.
9. Restrictions: `relative_cognitive_physical_rest`, `return_to_learn_accommodations`,
   `no_high_risk_sports_until_cleared`. Driving: `no_driving_until_symptom_free`.
   Low risk (no concussion) → `normal_activity_as_tolerated`, skip sport/driving.
10. Follow-up: 48 hours → `primary_care_or_concussion_recheck`. Low risk →
    `return_if_worse_only` at 24 hours.

### K-REPLETION-2026: Potassium Replacement and Escalation

**Decision sequence:**

1. Identify the latest `final` serum potassium observation (code `"K"`).
   Ignore `preliminary`, `canceled`, `entered-in-error`.
2. Identify eGFR (code `"33914-3"`).
3. Check urgent branch conditions:
   - `potassium_less_than: 3.0` → K < 3.0 triggers urgent
   - `dialysis_dependent_esrd: true` → patient on dialysis
   - `ecg_abnormality: true` → ECG abnormal
   - `severe_renal_contraindication: true` → severe renal issues
   - Symptoms: palpitations, syncope, weakness_with_arrhythmia_concern
4. **Urgent branch active:**
   `potassium_plan` = `urgent_escalation`, `replacement_required` = false,
   `medication_order.status` = `defer_to_urgent_clinician`, `oral_dose_mEq` = null.
5. **Not urgent, K < 3.5:**
   `replacement_required` = true, `potassium_plan` = `routine_oral_repletion`.
   Dose calculation: round((3.5 - K) * 10 * mEq_per_0_1_mmol_l_below_target)
   to nearest 10 mEq. Since mEq_per_0_1 = 10:
   dose = round((3.5 - K) * 100 / 10) * 10 = round((3.5 - K) * 10) * 10.
   Simpler: dose = round((3.5 - K) * 100) to nearest 10.
   Example: K=3.2 → (3.5-3.2)*100 = 30 → 30 mEq.
   Medication: ndc from controlled_codes, name "potassium chloride oral",
   route "PO", frequency "once", status "recommended".
   Follow-up lab: LOINC "2823-3", schedule next morning.
6. **K >= 3.5:**
   `replacement_required` = false, `potassium_plan` = `no_replacement`,
   `oral_dose_mEq` = null, `medication_order.status` = `not_recommended`,
   follow-up `scheduled_time` = null.
7. Contraindications: populate `dialysis_dependent`, `arrhythmia_symptoms`, `egfr`.

### CM-HIGH-RISK-2026: High-Risk Care-Management Routing

**Decision sequence:**

1. Get registry data from `care_registry` in case composite.
2. Risk tier:
   - `risk_score >= 0.75` → `high`
   - `0.5 <= risk_score < 0.75` → `moderate`
   - `risk_score < 0.5` → `low`
3. Check `complex_care_supporting_triggers` (each checked independently):
   - Chronic conditions >= 3
   - Recent admission present
   - Dialysis or advanced CKD
   - Heart failure
   - Uncontrolled diabetes
   If high risk AND multiple triggers → `complex_care_management`.
   Moderate risk with some triggers → `routine_case_management`.
   Otherwise → `not_eligible`.
4. Priority problems: from findings, problems list, and registry, map to template
   priority_problems enums.
5. Referrals:
   - Pharmacist: if medication_count >= 10
   - Social worker: if >= 2 SDOH domains at moderate or severe
   - Dialysis care coordination: if on dialysis
   - Transportation benefits: if transportation barrier in SDOH
6. Outreach: `permission_based_plain_language` if member shows reluctance;
   otherwise `standard_scripted_outreach`.
7. Source provenance:
   - `chart_facts`: data from observations/registry (risk_score, hba1c_percent,
     phosphorus_mg_dl, egfr, blood_pressure, active_medication_count,
     recent_admission, dialysis_schedule)
   - `member_disclosure_needed`: SDOH and member-reported items

### OBS-WINDOW-2026: Observation Window Interpretation

**Decision sequence:**

1. Case findings specify: target `patient_id`, `target_code`, window start/end,
   status rule (final only).
2. Filter observations from case composite:
   - `patient_id` matches target
   - `code` matches target code
   - `status` = `final` (NOT in excluded_statuses: preliminary, entered-in-error, canceled)
   - `effective_time` within window (inclusive start, exclusive end)
3. Sort matching observations by `effective_time` ascending, then
   `observation_id` ascending.
4. Collect `excluded_observation_ids`:
   - Same patient, same code, but before window or non-final status
   - Same patient, same window, but different code
5. `lab_found` = true if matching list non-empty.
6. `latest_final` = last entry in sorted matching list (null if empty).
7. Protocol gate from latest value:
   - K >= 3.5 → `satisfies_recent_final_normal`
   - 3.0 <= K < 3.5 → `recent_final_low_repletion_needed`
   - K < 3.0 → `recent_final_critical_or_urgent`
   - No final lab in window → `no_final_lab_in_window`
8. `repeat_lab.recommended` = true if gate indicates need for further testing;
   `scheduled_time` set accordingly, otherwise null.
