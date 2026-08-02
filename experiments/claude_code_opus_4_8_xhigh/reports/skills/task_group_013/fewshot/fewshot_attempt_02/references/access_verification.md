# Archetype A — New-patient access verification (roster intake)

**Recognize it by:** a `roster_id` (e.g. `NPI-…`), a list of target `patient_ids`, an
`answer_template.json` whose per-patient item has `insurance_status`, `prescription_status`,
`pharmacy_status`, `lifestyle_risk`, `overall_risk`, `registration_status`,
`blocked_reason_codes`, plus a `cohort_summary`. A `payloads/target_roster.json` may list the
patients and tell you to read `requested_service_date` / `service_line` from the roster record.

**Roster facts:** `SELECT requested_service_date, service_line FROM intake_rosters WHERE
roster_id=? AND patient_id=?`. Echo `roster_id` and `service_line` from the roster; use its
`requested_service_date` as the **service date** for every coverage/date test below.

Pull per patient: `patients`, `coverage`, `pbm`, `patient_pharmacy`+`pharmacies`, `lifestyle`,
`clinical_history`.

## Field rules

### insurance_status  (valid | invalid | missing)
Using the patient's `coverage` row and the roster service date `D` / service line `SL`:
- **missing** — no coverage row.
- **valid** — `status='active'` AND `effective_date <= D <= termination_date` AND `SL` is in the
  comma-separated `service_lines`.
- **invalid** — a coverage row exists but any of those fail (expired/pending status, out of date
  window, or service line not covered).

### prescription_status  (valid | invalid | missing)   ← from `pbm`
- **missing** — no pbm row.
- **valid** — `active=1` AND `formulary_status='covered'` AND `status='approved'` AND
  `specialty_required=0`.
- **invalid** — a pbm row exists but fails any of those.

### pharmacy_status  (in_network | out_of_network | unknown)
Use the **preferred** pharmacy = the `patient_pharmacy` row with `preference_rank=1`, joined to
`pharmacies`.
- **in_network** / **out_of_network** = that pharmacy's `network_status`.
- **unknown** — no preferred pharmacy row, or it does not resolve in `pharmacies`.

### lifestyle_risk  (low | medium | high)
Additive risk score over the `lifestyle` row, then band. Point directions (heavier habit → more
points):

| factor | points |
|---|---|
| smoking_status | Current = 2, Former = 1, Never = 0 |
| alcohol_use | Heavy = 2, Moderate = 1, Occasional/None = 0 |
| exercise_frequency | None or NULL = 2, `1-2` = 1, `3-4`/`5+` = 0 |
| sleep_hours | `< 6` = 2, `6 ≤ h < 7` = 1, `≥ 7` = 0 |

Band: **high** if score ≥ 4, **medium** if 2–3, **low** if 0–1.
> The exact weights/cutoffs are inferred from a training batch that was almost entirely "high";
> the *directions* (current smoker, heavy alcohol, no exercise, short sleep raise risk) are
> reliable. Re-examine if a batch's outcomes don't fit, but keep the monotonic direction.

### overall_risk  (low | medium | high)
A composite that takes the **worse** of lifestyle risk and clinical acuity. Escalate to **high**
when lifestyle_risk is high **or** clinical burden is high — clinical burden being high when any
of: `recent_hospitalization=1`, a non-empty `risk_flags` (e.g. `complex_medication_reconciliation`),
≥ 3 `chronic_conditions`, or a high `medication_count`. Otherwise fall back toward the lifestyle
band.
> In the training batch every patient resolved to `high`, so the low/medium boundary is inferred.
> The reliable, testable part: `overall_risk = high` ⇒ the blocked reason `overall_risk_high`
> is added, and high overall risk routes an otherwise-acceptable patient to `clinical_review`.

### blocked_reason_codes  (unordered set; only from the template's allowed list)
Emit each code whose trigger holds:

| code | trigger |
|---|---|
| coverage_expired | coverage `status='expired'` OR `termination_date < D` |
| coverage_pending | coverage `status='pending'` |
| excluded_service_line | roster `service_line` not in coverage `service_lines` |
| missing_address | `patients.address IS NULL` |
| emergency_contact_missing | `patients.emergency_contact_present=0` |
| pbm_missing | no pbm row |
| pbm_invalid | pbm exists and (`active=0` OR `status!='approved'` OR `formulary_status!='covered'`) |
| pbm_policy_mismatch | pbm otherwise valid but `specialty_required=1` |
| pharmacy_out_of_network | preferred pharmacy `network_status='out_of_network'` |
| pharmacy_unknown | no/undeliverable preferred pharmacy |
| preferred_contact_unavailable | preferred channel undeliverable: `email`→`email` NULL; `phone`/`sms`→`phone` NULL; `portal`→treat as always deliverable |
| overall_risk_high | `overall_risk == 'high'` |

### registration_status  (approved | hold | clinical_review | rejected)
Decision tree, first match wins:
1. **rejected** — a hard coverage failure: `coverage_expired` OR `excluded_service_line` present
   (missing coverage should also reject).
2. **clinical_review** — not rejected AND `overall_risk == 'high'`.
3. **hold** — not rejected, not high risk, but at least one soft blocker present
   (coverage_pending, any pbm_*, pharmacy_out_of_network / pharmacy_unknown, missing_address,
   emergency_contact_missing, preferred_contact_unavailable).
4. **approved** — no blockers at all.
> Steps 1–2 are confirmed by training data; `hold`/`approved` (steps 3–4) never occurred in the
> training batch and are the principled extrapolation.

## cohort_summary
- `total_patients` = number of roster patients.
- `counts_by_registration_status` over {approved, hold, clinical_review, rejected} (zero-filled).
- `counts_by_overall_risk` and `counts_by_lifestyle_risk` over {low, medium, high} (zero-filled).

## Ordering / shape
`patient_results` ascending by `patient_id`. Reason-code lists are unordered sets. Echo `task_id`
and `roster_id` exactly as the template requires.
