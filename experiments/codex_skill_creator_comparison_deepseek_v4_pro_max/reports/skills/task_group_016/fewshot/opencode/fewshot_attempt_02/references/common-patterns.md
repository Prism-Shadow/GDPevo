# Common Clinical Protocol Patterns

This reference catalogs patterns that recur across different clinical domains in
the protocol solver tasks. Recognizing these patterns speeds up decision-making.

## Pattern 1: Respiratory protocol assessment

**Seen in:** tasks targeting `CASE-RESP-*`

**Typical template fields:** `primary_assessment`, `risk_level`, `disposition`,
`red_flags`, `recommended_tests`, `medication_plan` (with antibiotic strategy,
allergen avoidance), `stabilization_actions`, `follow_up`, `return_precautions`,
`safety_checks`

**Key data sources:** CXR imaging, SpO2 observations, allergy records,
respiratory protocol definition

**Decision logic:**
- CXR findings drive `primary_assessment` (infiltrate → CAP, clear → viral URI)
- SpO2 values drive `risk_level` and `red_flags` (92-93% → moderate, <90% → high
  with urgent escalation)
- Allergy data drives `avoid_allergens` and antibiotic selection
- Safety checks assert no false claims about normal CXR or clear lungs when
  imaging shows otherwise

## Pattern 2: Head injury / concussion protocol

**Seen in:** tasks targeting `CASE-HEAD-*`

**Typical template fields:** `primary_assessment`, `risk_tier`, `disposition`,
`imaging_recommendation`, `red_flags`, `absent_red_flags`, `restrictions`,
`follow_up`

**Key data sources:** GCS/neuro observations, head CT imaging (if done),
protocol definition for pediatric head injury decision rules

**Decision logic:**
- GCS score and neuro exam findings drive `primary_assessment` and `risk_tier`
- The protocol defines which red flags are present vs. explicitly absent
- Restrictions cover cognitive rest, return-to-learn, sports clearance, and
  driving
- `absent_red_flags` lists serious findings that were checked and NOT found —
  this is a documenting field, not a clinical finding

## Pattern 3: Electrolyte replacement protocol

**Seen in:** tasks targeting `CASE-K-*`

**Typical template fields:** `latest_potassium` (observation_id, value, time),
`replacement_required`, `potassium_plan`, `oral_dose_mEq`, `medication_order`
(NDC, name, route, frequency, status), `follow_up_lab`, `urgent_actions`,
`contraindications` (dialysis, arrhythmia, eGFR)

**Key data sources:** potassium observations (LOINC `2823-3`), eGFR observation,
protocol for potassium replacement thresholds

**Decision logic:**
- Serum K+ value under threshold → replacement required
- Level determines plan: mild-moderate hypokalemia → routine oral repletion;
  severe → urgent escalation
- eGFR and dialysis status are contraindication screens
- Follow-up lab timed per protocol (typically next morning)

## Pattern 4: Care management routing

**Seen in:** tasks targeting `CASE-CM-*`

**Typical template fields:** `risk_tier`, `program`,
`priority_problems` (clinical + social), `numeric_anchors` (risk score, labs,
BP, med count), `referrals`, `outreach_stance`, `care_plan_minima`,
`escalation_conditions`, `source_provenance` (chart_facts vs.
member_disclosure_needed)

**Key data sources:** care-registry (risk score, program eligibility), problems,
observations (HbA1c, phosphorus, BP, eGFR), medications, SDOH

**Decision logic:**
- Risk score and problem complexity drive `risk_tier` and `program` routing
- `numeric_anchors` pull exact values from observations
- `referrals` are domain-specific (pharmacist for polypharmacy, social worker for
  SDOH barriers, dialysis coordination for ESRD)
- `source_provenance` separates facts from the chart vs. facts that require
  member disclosure during outreach

## Pattern 5: Lab-result observation window gating

**Seen in:** tasks targeting `CASE-LAB-*`

**Typical template fields:** `window` (from/to), `target_code`, `lab_found`,
`matched_observation_ids`, `excluded_observation_ids`, `latest_final`,
`protocol_gate`, `repeat_lab`

**Key data sources:** observations filtered by patient, LOINC code, and date
window

**Decision logic:**
- Filter observations by target code within the stated window
- Separate final from preliminary/corrected results
- Sort matches ascending by time, excludes ascending
- The `excluded_observation_ids` list captures near-misses: observations outside
  the window, non-final status, or wrong code
- `protocol_gate` maps to one of four outcomes: normal, low/repletion-needed,
  critical/urgent, or no lab in window
- `repeat_lab` is recommended only when the gate demands follow-up testing

## Cross-pattern rules

- Every task has a `case_id` and `patient_id` — these are always the first API
  call targets
- Every task returns `evidence_ids` — always include the case ID plus the
  specific observation, imaging, or protocol IDs that supported your decisions
- `safety_checks` are boolean assertions about what was NOT found — they must be
  `true` when you verified the absence of a finding
- Empty lists (`[]`) are semantically different from null — use `[]` for
  stabilization_actions, avoid_allergens, urgent_actions when nothing applies
- Follow-up timing is expressed in whole hours from the current clinical review
  time
