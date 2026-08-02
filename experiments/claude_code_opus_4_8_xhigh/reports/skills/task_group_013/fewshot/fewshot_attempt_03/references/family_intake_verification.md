# Family A — New Patient Access Verification (intake roster)

**Recognize it by:** prompt mentions "New Patient Access / Verification", an
intake *roster* id (e.g. `NPI-JUN-01`), a target patient list, insurance /
prescription / pharmacy / lifestyle / overall risk / registration status.
Template top-level keys: `task_id, roster_id, requested_service_date,
service_line, patient_results, cohort_summary`.

**Scope:** the roster's patients. `requested_service_date` and `service_line`
come from the `intake_rosters` row (`WHERE roster_id=<roster>` — all rows share
them). `task_id` = the train/test id; `roster_id` = the roster.
`patient_results` sorted ascending by `patient_id`.

Pull per patient: `patients`, `coverage`, `pbm`, `patient_pharmacy`+`pharmacies`,
`lifestyle`, `clinical_history`.

## Per-patient fields

### insurance_status  {valid, invalid, missing}
- `missing` if no `coverage` row.
- Otherwise evaluate against the roster's `service_line` and
  `requested_service_date`:
  - `coverage_expired` if `coverage.status=='expired'` OR (`termination_date`
    present AND `termination_date < requested_service_date`).
  - `coverage_pending` if `coverage.status=='pending'`.
  - `excluded_service_line` if `service_line` NOT in the comma-split
    `coverage.service_lines`.
  - `insurance_status = invalid` if any of the three fired, else `valid`.

### prescription_status  {valid, invalid, missing}  (from `pbm`)
- `missing` if no `pbm` row → code `pbm_missing`.
- `pbm_policy_mismatch` if `pbm.policy_number != coverage.policy_number`
  (checked first; a policy-number that does not match the medical coverage).
- else `pbm_invalid` if `pbm.status!='approved'` OR `pbm.active==0` OR
  `pbm.formulary_status!='covered'`.
- `prescription_status = invalid` if either code fired, else `valid`.
  (`specialty_required==1` is a secondary flag; in the observed data it always
  co-occurred with a policy mismatch — do not emit a separate code for it.)

### pharmacy_status  {in_network, out_of_network, unknown}
- Use the **most-preferred** pharmacy = the `patient_pharmacy` row with the
  lowest `preference_rank` (rank 1), joined to `pharmacies.network_status`.
- `in_network` / `out_of_network` accordingly; `out_of_network` → code
  `pharmacy_out_of_network`.
- `unknown` (→ code `pharmacy_unknown`) if no pharmacy row / unknown network.

### lifestyle_risk  {low, medium, high}  (weighted score, from `lifestyle`)
Sum points:
- smoking_status: `Current`=2, `Former`=1, else 0
- alcohol_use: `Heavy`=2, `Moderate`=1, else (`Occasional`/`None`) 0
- exercise_frequency: `None`/null/`1-2`=1, `3-4`/`5+`=0
- sleep_hours: `< 6`=1, else 0

Band: `high` if score ≥ 3, `medium` if score == 2, `low` if ≤ 1.
(Derived heuristic — reproduced all training patients exactly. If a test patient
sits on a boundary, recompute carefully; the score→band cutoffs are the fixed part.)

### overall_risk  {low, medium, high}
`high` if `lifestyle_risk=='high'` **OR** clinical severity is high, where
clinical-high = any of: `recent_hospitalization==1`, non-empty `risk_flags`,
`medication_count >= 6`, or `>=3` comma-split `chronic_conditions`. Otherwise
`overall_risk = lifestyle_risk`. `overall_risk=='high'` → code `overall_risk_high`.
(The clinical-high thresholds are INFERRED — only exercised by one training
patient whose lifestyle was medium but clinical severe. Lifestyle-driven high is solid.)

### Other blocked_reason_codes (contact / demographics)
- `preferred_contact_unavailable`: the channel in `patients.preferred_contact`
  has no backing value — `phone`/`sms` require non-null `phone`; `email`/`portal`
  require non-null `email`.
- `missing_address`: `patients.address` null/empty.
- `emergency_contact_missing`: `patients.emergency_contact_present==0`.

### blocked_reason_codes (list, unordered set)
Union of every code triggered above:
`coverage_expired, coverage_pending, excluded_service_line, pbm_missing,
pbm_invalid, pbm_policy_mismatch, pharmacy_out_of_network, pharmacy_unknown,
preferred_contact_unavailable, missing_address, emergency_contact_missing,
overall_risk_high`. Emit only allowed values from the template.

### registration_status  {approved, hold, clinical_review, rejected}
First match wins:
1. `rejected` if a **hard coverage denial** — `excluded_service_line` OR
   `coverage_expired` OR `insurance_status=='missing'`.
2. else `clinical_review` if `overall_risk=='high'`.
3. else `hold` if any blocked_reason_code (other than `overall_risk_high`) is present.
4. else `approved`.
(All training patients hit branches 1–2; `hold`/`approved` are the natural
completion and are INFERRED.)

## cohort_summary
- `total_patients` = count.
- `counts_by_registration_status`: tally over {approved, hold, clinical_review,
  rejected} (all keys, incl. zeros).
- `counts_by_overall_risk`: tally over {low, medium, high}.
- `counts_by_lifestyle_risk`: tally over {low, medium, high}.
