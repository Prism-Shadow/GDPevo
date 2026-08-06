# Archetype D — Chronic-care enrollment panel (program candidates)

**Recognize it by:** a `program_code` and an `answer_template.json` about per-candidate
`eligible`, `enrollment_status`, `reason_codes`, `follow_up_cadence`, `missing_chart_artifacts`,
`outreach_channel`, `initial_monitoring_package`, plus a `summary`. Rules below are confirmed for
the diabetes+hypertension program (`DMHTN-2026A`, target `diabetes_hypertension`); for another
program keep the structure and re-map the target condition and code vocabulary from that task's
template.

- Candidate set = exactly `GET /programs/{program_code}/candidates` (equivalently
  `SELECT * FROM program_candidates WHERE program_code=?`). Include **every** candidate; do not
  filter by candidate_date. Output `patients[]` sorted ascending by `patient_id`.
- `as_of_date` is a panel label supplied by the task (not derivable from the DB and not
  `MAX(candidate_date)`). Use the value the task states; it does not affect the computed rows
  (freshness keys off `chart_artifacts.status`, below). Echo `program_code` verbatim.
- Join per candidate: `patients`, `clinical_history`, all `chart_artifacts` rows.

## Chart presence test (used throughout)
- `chart_record` is virtual: **present/active ⟺ `patients.existing_chart=1`**; `chart_not_active`
  ⟺ `existing_chart=0`.
- Any other artifact type (active_problems, vitals, labs, medications, consent) is
  **present & current** iff a `chart_artifacts` row of that type exists with `status='current'`.
  Absent, or status stale/draft, counts as **missing/stale**.

## eligible (boolean)
`eligible=true` iff BOTH: `program_candidates.target_condition` equals the program's target
(`diabetes_hypertension`) **and** `clinical_history.chronic_conditions` contains **both**
`diabetes` and `hypertension`. Otherwise false.

## enrollment_status (enroll | hold | reject)
1. not eligible → **reject**.
2. eligible AND `consent_status='declined'` → **reject**.
3. eligible AND `consent_status='missing'` → **hold**.
4. eligible AND `consent_status='signed'` AND chart fully active & current → **enroll**.
(An eligible, signed candidate with an incomplete/inactive chart most likely **holds** — inferred,
untested. All training enrollees had clean charts.)

## reason_codes (unordered set; only the template's allowed codes)
**Ineligibility codes** (only when ineligible), each emitted independently when true:
- `wrong_target_condition` — target_condition ≠ program target.
- `missing_active_dmhtn_diagnosis` — chronic_conditions missing diabetes and/or hypertension.

**Universal hard flags** (any candidate, eligible or not):
- `consent_declined` — consent_status='declined'.
- `chart_not_active` — existing_chart=0.

**Eligible-only codes** (suppressed entirely for ineligible candidates):
- For an enrolling candidate emit `meets_dmhtn_criteria` **plus at most one** acuity code, by
  priority (exactly one; lower ones suppressed):
  1. `recent_hospitalization_high_touch` — `clinical_history.recent_hospitalization=1`.
  2. `recent_ed_high_touch` — `risk_flags` contains `recent_ed_visit`.
  3. `low_adherence_high_touch` — `adherence_score < 50` (threshold in (49,67]; 50 the natural value).
  4. `ckd_biweekly_monitoring` — chronic_conditions contains `ckd`.
  5. none — plain criteria only.
- `consent_missing` — eligible AND consent_status='missing'.
- Chart-readiness codes (eligible, when the artifact is missing/stale): `stale_active_problems`,
  `missing_recent_vitals`, `missing_recent_labs`, `missing_medication_list`.

Net: **enroll** → meets_dmhtn_criteria + (one acuity). **hold** (consent missing) → consent_missing
+ chart_not_active + applicable chart-readiness codes. **reject (eligible, declined)** →
consent_declined + chart_not_active + applicable chart-readiness codes. **reject (ineligible)** →
wrong_target_condition and/or missing_active_dmhtn_diagnosis + any universal hard flag; no soft
chart codes.

## follow_up_cadence (weekly | biweekly | monthly | deferred | none)
- weekly — enroll with any high-touch acuity code.
- biweekly — enroll, CKD only (no high-touch).
- monthly — enroll, plain.
- deferred — hold.
- none — reject.

## missing_chart_artifacts (unordered set; chart_record/active_problems/vitals/labs/medications/consent)
- **Only for eligible candidates; ineligible → always `[]`** (even with an absent chart).
- For an eligible candidate include an item when not present-and-current: `chart_record`
  (existing_chart=0), and each of active_problems/vitals/labs/medications/consent whose artifact is
  absent or not `status='current'`. (Mirrors the eligible chart-readiness reason codes, plus
  `consent`, which appears here but has no matching reason code.)

## outreach_channel (phone | portal | sms | email | none)
Primary = `program_candidates.preferred_outreach`; fall back to `patients.preferred_contact` if the
primary channel is undeliverable; else `none`. Deliverability: phone/sms need `patients.phone`
non-null; email needs `patients.email` non-null; portal needs an active chart (`existing_chart=1`).

## initial_monitoring_package
`package_type`: enroll+high-touch → `high_touch_dm_htn`; enroll+non-high-touch (CKD or plain) →
`standard_dm_htn`; hold → `deferred`; reject → `not_applicable`.

`components` (unordered set):
- Every enrollee baseline: `bp_cuff`, `glucometer`, `lab_order_a1c_cmp_lipid`.
- + `medication_reconciliation` when cadence is biweekly or weekly (CKD or high-touch).
- + `care_plan_setup` when cadence is weekly (high-touch).
- deferred (hold): `consent_packet`, `chart_update_request`.
- not_applicable (reject): `[]`.

`first_checkin_days` keyed off cadence: weekly→7, biweekly→14, monthly→30, deferred→null, none→null.

## summary
- `total_candidates`; `eligible_count`; `ineligible_count`.
- `status_counts` over {enroll, hold, reject}.
- `follow_up_counts` over {weekly, biweekly, monthly, deferred, none}.
- `outreach_counts` over {phone, portal, sms, email, none}.
- `monitoring_package_counts` over {standard_dm_htn, high_touch_dm_htn, deferred, not_applicable}.
All keys present, zero-filled.
