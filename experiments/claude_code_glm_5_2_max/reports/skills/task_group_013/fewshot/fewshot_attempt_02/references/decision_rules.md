# Decision Rules — Evidence → Template Token

These rules map portal records onto the controlled tokens a task's `answer_template.json` defines. **The task's template is authoritative for the exact token spelling and the allowed set.** Emit only tokens that appear in that template's `allowed_values`. The rules below describe *which portal evidence triggers which token family*; confirm the spelling against the template before emitting.

When a novel task does not match any family below, use the same method: read the template's required fields and allowed tokens, fetch the corresponding portal tables, and map each policy signal to the closest token.

---

## Family A — New Patient Access Verification

**Objective:** for each patient on a roster, classify insurance / prescription / pharmacy / lifestyle risk / overall risk, set a registration status and blocked reason codes, and produce a cohort summary.

**Sources:** `intake_rosters` (gives `requested_service_date` + `service_line` + patient list for the roster), `patients`, `coverage`, `pbm`, `patient_pharmacy`+`pharmacies`, `lifestyle`, `clinical_history`.

### Field mappings

- **`insurance_status`**
  - `valid` — coverage row exists, `status=active`, `network_status=in_network`, `effective_date ≤ requested_service_date ≤ termination_date`, and `service_line` ∈ `coverage.service_lines`.
  - `invalid` — coverage exists but one condition fails. Sub-reason tokens:
    - `coverage_expired` — `termination_date < requested_service_date` (or `status` terminated).
    - `coverage_pending` — `status` not active / `effective_date` in the future.
    - `excluded_service_line` — `service_line` ∉ `coverage.service_lines`.
  - `missing` — no coverage row.

- **`prescription_status`** (from `pbm`)
  - `valid` — row exists, `active=1`, `status=approved`, `formulary_status=covered`.
  - `invalid` — row exists but `active=0`, `status=rejected`, or `formulary_status=not_found` (`pbm_invalid`); or a policy restriction such as `specialty_required` / formulary mismatch (`pbm_policy_mismatch`).
  - `missing` — no `pbm` row (`pbm_missing`).

- **`pharmacy_status`** (preferred pharmacy = `patient_pharmacy` row with `preference_rank=1`, joined to `pharmacies`)
  - `in_network` — preferred pharmacy's `network_status=in_network`.
  - `out_of_network` — preferred pharmacy exists but `network_status=out_of_network` → `pharmacy_out_of_network`.
  - `unknown` — no preferred pharmacy row, or pharmacy id not found → `pharmacy_unknown`.

- **`lifestyle_risk`** (from `lifestyle`)
  - `high` — current smoker, or heavy alcohol use, or (no exercise **and** low sleep hours).
  - `medium` — former smoker, or moderate risk factors.
  - `low` — otherwise.

- **`overall_risk`** — combine `lifestyle_risk` with `clinical_history.risk_flags` and eligibility failures. High lifestyle or any clinical risk flag or multiple eligibility failures → `high`; a single moderate factor → `medium`; clean → `low`. **When `overall_risk=high`, always include `overall_risk_high` in `blocked_reason_codes`.**

- **Contact / address completeness** (from `patients`)
  - `emergency_contact_present=0` → `emergency_contact_missing`.
  - chosen `preferred_contact` channel has a null value (e.g. `email` selected but `email` is null) → `preferred_contact_unavailable`.
  - `address` is null → `missing_address`.

### `registration_status` (severity routing)

- `rejected` — hard eligibility failure: `coverage_expired` or `excluded_service_line` (insurance invalid due to expiry/exclusion), or no insurance at all.
- `clinical_review` — salvageable problems with otherwise workable insurance: `coverage_pending`, or only pharmacy/PBM/contact blockers, or high overall risk needing clinician sign-off.
- `hold` — pending patient-side items (e.g. contact/address gaps) without a hard block.
- `approved` — no blocked reason codes.

`blocked_reason_codes` = the union of every token triggered above (insurance sub-reasons, PBM token, pharmacy token, contact/address tokens, and `overall_risk_high` when applicable). Treat as an unordered set; emit it sorted for determinism.

### Cohort summary
Count patients by `registration_status`, `overall_risk`, and `lifestyle_risk` using the template's count-key sets (include keys with value 0). `total_patients` = length of the roster.

---

## Family B — Referral Readiness Audit

**Objective:** per-referral readiness, ICD discrepancies, duplicate groups, shared-insurance anomalies, blocker sets, ready-to-schedule list, an action plan, and summary counts.

**Sources:** `referrals` (filter by `batch_id`), `icd_codes`/`GET /icd/{code}`, `patients`, `coverage`, `documents`.

### Per-referral issue detection

- **ICD discrepancy** (look up `referrals.icd10_code`):
  - `icd_chapter_mismatch` — the code's `chapter` does not match the chapter expected for `referrals.service_line` (e.g. an orthopedics referral whose code falls outside the musculoskeletal chapter).
  - `narrative_mismatch` — `diagnosis_description` / `referral_reason` inconsistent with the code's `description` or `service_family`.
  - `laterality_mismatch` — code's `laterality` conflicts with the referral narrative (e.g. code says left, reason says right).
- `duplicate_referral` — another referral with same `patient_id` + same `service_line` (+ close `date_received` or same `icd10_code`). Group them; primary = lowest `referral_id`; `recommendation=consolidate_to_primary` (or `keep_separate` if clinically distinct).
- `shared_insurance_anomaly` — same `insurance_id` across referrals for **different** `patient_id`s → `verify_distinct_patient_policy_id`; same patient → `legitimate_duplicate_same_patient`.
- `missing_records` — `records_received=0`.
- `missing_imaging` — `imaging_received=0`.
- `auth_blocker` — `auth_required=1` and `auth_status` ∈ {pending, denied, not_submitted}.
- `already_scheduled` — `appointment_scheduled=1`.

### `readiness_status`

- `ready` — no issues: records + imaging present, auth ok, no ICD discrepancy, not scheduled, no duplicate, no shared-insurance anomaly.
- `blocked` — any hard blocker: `missing_records`, `missing_imaging`, or `auth_blocker`.
- `under_review` — soft issues only: ICD discrepancy, `duplicate_referral`, or `already_scheduled`.
- `admin_followup` — `shared_insurance_anomaly` and nothing harder.

### `priority_tier` and `action_plan`
- `tier_1_immediate` — urgent referrals with a clinical/code discrepancy (safety). `tier_2_short_term` — routine blocked/under_review. `tier_3_administrative` — admin_followup only. `null` when ready.
- `action_plan`: one entry per non-ready referral. `action_codes` derive from the issue set — `request_corrected_icd` (ICD mismatch), `confirm_narrative`, `confirm_laterality`, `consolidate_duplicate`, `verify_insurance_id` (shared insurance), `request_records`, `request_imaging`, `resolve_authorization`, `review_existing_appointment` (already scheduled).

### Cross-referral sections
- `icd_discrepancies` — referrals with any ICD issue, with `icd10_code`, `issue_types`, `observed_chapter` (the code's chapter), `expected_chapter` (the chapter for the service line).
- `duplicate_groups` — `group_id`, ascending `referral_ids`, `patient_id`, `primary_referral_id`, `recommendation`.
- `shared_insurance_anomalies` — `insurance_id`, ascending `referral_ids` and `patient_ids`, `disposition`.
- `blocker_sets` — `{missing_records, missing_imaging, auth_blockers}` as ascending `referral_id` lists; `auth_blockers` carries `auth_status`.
- `ready_to_schedule` — ascending `referral_id` list of ready referrals.

### Summary
`counts_by_urgency` from `referrals.urgency` (urgent/routine; admin only if the template's set includes it). `counts_by_readiness_status` over the four statuses. `counts_by_urgency_and_status` lists **only non-zero** urgency×readiness combinations, ordered urgency then readiness_status. `issue_counts` counts referrals touched by each issue category and the number of duplicate groups / shared-insurance anomalies.

---

## Family C — Transfer Packet Review (e.g. dialysis transfers)

**Objective:** per-transfer packet completeness, missing/stale documents, requested-start feasibility vs. chair capacity, final intake decision, next-contact owner/route, and a cohort summary.

**Sources:** `transfer_requests` (filter by `batch_id`), `documents` (join on `transfer_id`), `facility_capacity`, `patients`, `coverage`.

### Packet completeness
- Required document set is the template's `allowed_values` for `missing_required_documents` (e.g. `allergy_list, face_sheet, flu_vaccine, hbsag, hep_b_antibody_core, history_physical, insurance_proof, medication_list, monthly_labs, physician_orders, pneumonia_vaccine, ppd_or_cxr, transportation, treatment_flowsheets, vascular_access_report`).
- `packet_completeness_status` = `complete` if every required `doc_type` is present and `finalized=1`; else `incomplete`.
- `missing_required_documents` = required `doc_type`s absent or not finalized, alphabetical by code.
- `stale_documents` = present docs whose `received_date` is older than the doc type's freshness limit. **Freshness policy:** `hbsag`, `hep_b_antibody_core`, `monthly_labs`, `ppd_or_cxr` → 30 days; `history_physical` → 365 days. Emit `doc_type`, `received_date`, `freshness_limit_days`.

### Requested-start feasibility (from `facility_capacity`)
- `date` = `transfer_requests.requested_start_date`.
- `open_chairs_total` = sum of `facility_capacity.open_chairs` across `location_id` for that `date` + `modality` (in-center hemodialysis).
- `capacity_status` = `available` if `open_chairs_total > 0` else `unavailable`.
- `feasibility`:
  - `ready_on_requested_start` — packet complete **and** capacity available.
  - `packet_not_ready_capacity_available` — packet incomplete **and** capacity available.
  - `capacity_unavailable` — packet complete **and** capacity unavailable.
  - `packet_not_ready_capacity_unavailable` — packet incomplete **and** capacity unavailable.

### Decision and next contact
- `final_intake_decision`: `accept` when `ready_on_requested_start`; `hold` when exactly one dimension is unresolved; `clinical_review` when both packet and capacity are unresolved (or clinical complexity). Map to the template's allowed set.
- `next_contact_owner` / `next_contact_route`: packet gaps → `clinical_nurse` + `fax_referring_facility`; ready → `scheduling_coordinator` + `internal_queue`; patient-side gaps → `intake_coordinator` + `phone_patient`; accept → `none` + `none`.

### Cohort summary
Count transfers: total, complete-packet count, patients with missing docs, patients with stale docs, capacity-available count, requested-start-ready count, plus `decision_counts` and `next_contact_owner_counts` over the template's key sets.

---

## Family D — Chronic-Care Enrollment Panel

**Objective:** per-candidate eligibility, enrollment disposition, reason codes, follow-up cadence, missing chart artifacts, outreach channel, initial monitoring package, and summary counts.

**Sources:** `program_candidates` (filter by `program_code`), `patients`, `chart_artifacts`, `clinical_history`, `coverage`.

### Eligibility & reason codes
- `eligible=true` requires: `target_condition` matches the program's target **and** an active program-relevant diagnosis present (in `clinical_history.chronic_conditions` / active problems) **and** `consent_status=signed`.
- `wrong_target_condition` — `target_condition` does not match the program.
- `missing_active_dmhtn_diagnosis` (or program-equivalent) — no active target diagnosis on file.
- Consent: `signed` → ok; `declined` → `consent_declined`; anything else → `consent_missing`.
- `chart_not_active` — `patients.existing_chart=0` or `chart_record` artifact missing/stale.
- `missing_chart_artifacts` from `chart_artifacts`: artifact types ∈ {chart_record, active_problems, vitals, labs, medications, consent} that are missing or stale. Map to reason codes: `stale_active_problems`, `missing_recent_vitals`, `missing_recent_labs`, `missing_medication_list` (and `consent_missing`/`chart_not_active` as above).
- High-touch reasons: `recent_hospitalization_high_touch` (`recent_hospitalization=1`), `recent_ed_high_touch` (ED visit in `risk_flags`), `low_adherence_high_touch` (`adherence_score` below threshold), `ckd_biweekly_monitoring` (CKD in `chronic_conditions`). `meets_dmhtn_criteria` (or program-equivalent) when eligibility is satisfied.

### `enrollment_status`
- `enroll` — eligible, consent signed, chart active, artifacts current.
- `hold` — eligible but `consent_missing` or stale/missing artifacts (salvageable).
- `reject` — `consent_declined`, or not eligible (`wrong_target_condition` / missing diagnosis), or `chart_not_active` with declined consent.

### Cadence, outreach, monitoring package
- `follow_up_cadence`: `weekly` (high-touch), `biweekly` (CKD biweekly monitoring), `monthly` (standard enroll), `deferred` (hold), `none` (reject).
- `outreach_channel` from `program_candidates.preferred_outreach`; `none` for rejects without a channel.
- `initial_monitoring_package`:
  - `high_touch_dm_htn` — high-touch enrollees; components `{bp_cuff, glucometer, lab_order_a1c_cmp_lipid, medication_reconciliation, care_plan_setup}`; `first_checkin_days=7`.
  - `standard_dm_htn` — standard enrollees; components `{bp_cuff, glucometer, lab_order_a1c_cmp_lipid}` (+ `medication_reconciliation` when CKD); `first_checkin_days` = 14 (biweekly) or 30 (monthly).
  - `deferred` — hold; components `{consent_packet, chart_update_request}`; `first_checkin_days=null`.
  - `not_applicable` — reject; components `[]`; `first_checkin_days=null`.

### Summary
Counts: total candidates, eligible/ineligible, `status_counts` (enroll/hold/reject), `follow_up_counts`, `outreach_counts`, `monitoring_package_counts` — each over the template's key sets, including zero-valued keys.

---

## Family E — Referral-to-Chart Activation

**Objective:** per-referral readiness + blocker codes, clinical-code discrepancy list, blocker sets, duplicate handling, ready-referral chart needs, a correspondence queue, and a priority order.

**Sources:** `referrals` (filter by `batch_id`), `icd_codes`, `patients`, `chart_artifacts`, `documents`.

### `readiness_by_referral` + `blocker_codes`
- `clinical_code_discrepancy` — ICD chapter/service_family/laterality mismatch vs. `service_line`/narrative (same method as Family B).
- `records_missing` — `records_received=0`.
- `imaging_missing` — `imaging_received=0`.
- `authorization_blocked` — `auth_required=1` and `auth_status` ∈ {pending, denied, not_submitted}.
- `duplicate_review` — member of a duplicate group.
- `scheduled_before_clearance` — `appointment_scheduled=1` while not ready.
- `readiness_status`: `ready` (no blockers), `blocked` (records/imaging/auth hard blockers), `under_review` (clinical code discrepancy / duplicate), `admin_followup` per template.

### Cross-referral sections
- `clinical_code_discrepancy_referrals` — ascending `referral_id` list with a code discrepancy.
- `blocker_sets` — `{authorization, records, imaging}` as ascending `referral_id` lists.
- `duplicate_handling` — `duplicate_groups` (`group_id`, ascending `referral_ids`, `keep_referral_id`=primary) and `cleared_duplicate_review_referrals` (ascending `referral_id` list reviewed and cleared).

### `ready_referral_chart_needs` (ready referrals only)
- `chart_action`: `create_chart` if `patients.existing_chart=0`; `update_chart` if a chart exists but artifacts are missing; `no_chart_action` if the chart is complete.
- `artifacts_to_create` = missing chart artifact types ∈ {demographics, active_problems, medications, allergies, vitals, labs, consent}, alphabetical.

### `correspondence_queue` (non-ready referrals)
- `template_type`: `clinical_code_clarification` (code discrepancy), `auth_records_request` (auth/records blockers), `duplicate_resolution` (duplicate), `appointment_hold_notice` (scheduled before clearance).
- `reason_codes` from the template's allowed set (e.g. `wrong_service_family`, `clinical_reason_mismatch`, `records_missing`, `authorization_denied`, `duplicate_review`, `appointment_already_scheduled`) — unordered set.

### `priority_order`
Non-ready referrals only, **highest priority first**, `rank` from 1. `priority_tier`: `tier_1_immediate` (urgent + clinical discrepancy), `tier_2_short_term` (routine blockers/under review), `tier_3_administrative` (admin only).
