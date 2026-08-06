# Family D — Chronic-Care Program Enrollment Panel

**Recognize it by:** prompt asks to prepare an *enrollment panel* for a program
code (e.g. `DMHTN-2026A`), with eligibility, enrollment disposition, reason
codes, follow-up cadence, missing chart artifacts, outreach channel, monitoring
package. Template top-level keys: `program_code, as_of_date, patients, summary`.

**Scope / row set:** `GET /programs/{program_code}/candidates` (or
`program_candidates WHERE program_code=<code>`). Emit **one output patient per
candidate**, sorted ascending `patient_id`. All returned candidates are included
(no filtering by date). Per candidate pull `patients` (existing_chart, phone,
email, preferred_contact), `clinical_history` (chronic_conditions,
recent_hospitalization, risk_flags), and `chart_artifacts` (via `/chart/{id}`).

**Program parameters** (from the `program_code`, not the data). For
`DMHTN-2026A`: target token `diabetes_hypertension`; required active diagnoses
`{diabetes, hypertension}` (ALL required); reason-code slug family `dmhtn`
(`meets_dmhtn_criteria`, `missing_active_dmhtn_diagnosis`). A sibling program
substitutes its own token / required-diagnosis set / slug.

**as_of_date:** an exogenous program *reporting date* (a fixed YYYY-MM-DD supplied
for the program; it is NOT the run date and NOT derivable from candidate rows).
Look for it in the prompt/roster/program config; echo it in output. None of the
derived logic depends on it — staleness uses the artifact `status` field directly.

## Eligibility (independent sub-checks)
- `wrong_target_condition` ⟺ `program_candidates.target_condition != program token`.
- `missing_active_<slug>_diagnosis` ⟺ `clinical_history.chronic_conditions`
  (comma tokens) lacks ANY required diagnosis. **Source is
  clinical_history.chronic_conditions**, not the active_problems chart artifact.
- `eligible = NOT wrong_target_condition AND NOT missing_diagnosis`. Emit each
  failing code independently.

## enrollment_status  {enroll, hold, reject}  (precedence, first match wins)
1. NOT eligible → `reject`.
2. `consent_status == 'declined'` → `reject`.
3. `consent_status ∈ {missing, null}` → `hold`.
4. eligible + signed but `existing_chart==0` or any core artifact not current →
   `hold` (INFERRED; untested).
5. else → `enroll`.

## reason_codes (unordered set) — assembly
**Enroll-only** (iff status==enroll):
- `meets_<slug>_criteria` — always for enrolled.
- Exactly ONE high-touch/cadence code, by precedence (top match only):
  1. `recent_hospitalization_high_touch` ⟺ `recent_hospitalization==1`
  2. `recent_ed_high_touch` ⟺ `risk_flags` contains `recent_ed_visit`
  3. `low_adherence_high_touch` ⟺ `adherence_score < 50` (threshold INFERRED)
  4. `ckd_biweekly_monitoring` ⟺ `chronic_conditions` contains `ckd`
  5. none → only the meets-criteria code.

**For ALL candidates (any eligibility):**
- `consent_declined` ⟺ `consent_status=='declined'`.
- `chart_not_active` ⟺ `patients.existing_chart==0` (independent of artifacts).

**For ELIGIBLE candidates only** (skipped entirely when ineligible):
- `consent_missing` ⟺ `consent_status ∈ {missing, null}`. (Key asymmetry:
  `declined` surfaces regardless of eligibility; `missing` only when eligible.)
- Granular artifact codes, each ⟺ the core artifact is **not current** (no row of
  that type, OR `status != 'current'`): `stale_active_problems` (active_problems),
  `missing_recent_vitals` (vitals), `missing_recent_labs` (labs),
  `missing_medication_list` (medications). No stale-vs-missing distinction.

Ineligible candidates emit ONLY their eligibility code(s) plus (for-all)
`consent_declined`/`chart_not_active`; no consent_missing, no artifact codes.

## follow_up_cadence  {weekly, biweekly, monthly, deferred, none}
enroll: `weekly` if the high-touch code is hospitalization/ED/low-adherence;
`biweekly` if ckd; `monthly` if plain (meets-criteria only).
hold → `deferred`; reject → `none`.

## missing_chart_artifacts  (subset; ELIGIBLE only, else `[]`)
- `chart_record` ⟺ `existing_chart==0`.
- `active_problems`/`vitals`/`labs`/`medications`/`consent` ⟺ that artifact type
  is not current (missing OR `status!='current'`).
Only these 6 map (ignore demographics, allergies, care_plan, outreach_preference).
1:1 with reason codes except `consent` has no paired reason code.

## outreach_channel  {phone, portal, sms, email, none}  (computed for ALL statuses)
Primary = `program_candidates.preferred_outreach` (identity map). Deliverability
fallback (INFERRED, but reproduces every case + all summary counts): if the
primary channel's prerequisite fails, use `patients.preferred_contact`; if
neither deliverable, `none`. Prerequisites: `portal`→`existing_chart==1`;
`phone`/`sms`→`phone` non-null; `email`→`email` non-null.

## initial_monitoring_package  (keyed by status + cadence)
- enroll+weekly → `high_touch_dm_htn`: `[bp_cuff, glucometer,
  lab_order_a1c_cmp_lipid, medication_reconciliation, care_plan_setup]`,
  first_checkin_days=7.
- enroll+biweekly → `standard_dm_htn`: `[bp_cuff, glucometer,
  lab_order_a1c_cmp_lipid, medication_reconciliation]`, first_checkin_days=14.
- enroll+monthly → `standard_dm_htn`: `[bp_cuff, glucometer,
  lab_order_a1c_cmp_lipid]`, first_checkin_days=30.
- hold → `deferred`: `[consent_packet, chart_update_request]`, first_checkin_days=null.
- reject → `not_applicable`: `[]`, first_checkin_days=null.
Component logic: base `{bp_cuff, glucometer, lab_order_a1c_cmp_lipid}` for every
enrolled patient; `+medication_reconciliation` when weekly or biweekly;
`+care_plan_setup` only when weekly. (Package slugs `*_dm_htn` are the DMHTN
program's; a sibling uses its own package names.)

## summary
- `total_candidates` = # candidate rows.
- `eligible_count`/`ineligible_count` = tally of `eligible`.
- `status_counts`{enroll,hold,reject}, `follow_up_counts`{weekly,biweekly,monthly,
  deferred,none}, `outreach_counts`{phone,portal,sms,email,none},
  `monitoring_package_counts`{standard_dm_htn,high_touch_dm_htn,deferred,
  not_applicable} = tallies over the patient rows (all enum keys, zero-filled).
