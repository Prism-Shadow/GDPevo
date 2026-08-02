# Family E — Referral-To-Chart Activation

**Recognize it by:** prompt asks which referrals may move forward, which need
referral-office follow-up, and what *chart activation* work remains
(e.g. `PULM-JUN-02`). Template top-level keys: `batch_id, readiness_by_referral,
clinical_code_discrepancy_referrals, blocker_sets, duplicate_handling,
ready_referral_chart_needs, correspondence_queue, priority_order`.

**Scope:** `referrals WHERE batch_id=<batch>`, ordered ascending `referral_id`.
Join `icd_codes`, `patients`, `chart_artifacts`. The batch service line
(e.g. pulmonary) is the expected `service_family`. Records/imaging/auth truth
comes from the **referrals integer flags**, not the documents table.

## Per-referral blocker_codes (independent predicates; collect all)
- **records_missing**: `records_received == 0`.
- **imaging_missing**: `imaging_received == 0`.
- **authorization_blocked**: `auth_required == 1` AND `auth_status != 'approved'`.
- **clinical_code_discrepancy**: the coded diagnosis is inconsistent with the
  batch service line, via either sub-case (use **service_family**, not chapter —
  a symptom code like `R06.02`/`R00-R99` with `service_family=='pulmonary'` is
  accepted):
  - (a) `icd_codes.service_family != <batch service line>` (code belongs to
    another specialty).
  - (b) service_family matches BUT `referral_reason` is a chief complaint
    incompatible with the service line (confirmed instance: `pain evaluation`
    on a pulmonary referral). Compatible reasons seen: `transfer of care`,
    `worsening symptoms`, `previsit clearance`.
- **scheduled_before_clearance**: `appointment_scheduled == 1` AND the referral
  has ≥1 other blocker.
- **duplicate_review**: referral is a non-kept member of an *active* duplicate
  group (see below). A merely-flagged-then-cleared referral does NOT get this.

## readiness_status (first match wins)
1. `ready` if no blockers.
2. else `blocked` if any of {records_missing, imaging_missing,
   authorization_blocked, scheduled_before_clearance}.
3. else `under_review` if clinical_code_discrepancy (no hard blocker).
4. else `admin_followup` (only duplicate_review) — INFERRED.

## clinical_code_discrepancy_referrals
All referral_ids with the clinical_code_discrepancy blocker, ascending.

## blocker_sets (ascending referral_id lists)
- `authorization` = authorization_blocked referrals.
- `records` = records_missing referrals.
- `imaging` = imaging_missing referrals.
(clinical/duplicate/scheduled blockers are reported elsewhere, not here.)

## duplicate_handling
- Candidate flag = `referrals.notes == 'possible duplicate'`.
- An **active duplicate_group** = ≥2 candidate referrals sharing the same
  `patient_id` (and same `icd10_code`/reason). `group_id`=`"DUP-"+batch+"-"+NNN`,
  `referral_ids` asc, `keep_referral_id` = earliest `date_received` / lowest
  `referral_id`. Non-kept members get the `duplicate_review` blocker. (INFERRED —
  no active group in the observed batch.)
- `cleared_duplicate_review_referrals` = candidate (flagged) referrals with NO
  real duplicate partner in the batch → cleared, ascending. These add no blocker.

## ready_referral_chart_needs  (readiness_status == ready only; ascending referral_id)
- `chart_action`: `patients.existing_chart==1` → `update_chart`; `==0` →
  `create_chart`; (`no_chart_action` INFERRED — nothing to create).
- `artifacts_to_create`: over the 7 enum types {demographics, active_problems,
  medications, allergies, vitals, labs, consent}, include a type iff the patient
  has **no `chart_artifacts` row of that type with `status=='current'`**
  (absent OR stale/draft both qualify). Ignore non-enum artifact types
  (`care_plan`, `outreach_preference`). Output **alphabetical**.

## correspondence_queue (one row per NON-ready referral; ascending referral_id)
- `template_type` = dominant blocker by precedence (highest first):
  1. scheduled_before_clearance → `appointment_hold_notice`
  2. duplicate_review → `duplicate_resolution` (INFERRED)
  3. authorization_blocked / records_missing / imaging_missing → `auth_records_request`
  4. clinical_code_discrepancy → `clinical_code_clarification`
- `reason_codes` (unordered set) = union over the referral's blockers:
  - authorization_blocked → `authorization_denied`
  - records_missing → `records_missing`
  - scheduled_before_clearance → `appointment_already_scheduled`
  - clinical_code_discrepancy → `wrong_service_family` (sub-case a) OR
    `clinical_reason_mismatch` (sub-case b)
  - duplicate_review → `duplicate_review` (INFERRED)

## priority_order (NON-ready referrals; highest priority first)
- `priority_tier`: `urgency=='urgent'` → `tier_1_immediate`; `urgency=='routine'`
  → `tier_2_short_term`; administrative-only → `tier_3_administrative` (INFERRED).
- Sort key (ascending rank starting at 1):
  1. priority_tier (tier_1 < tier_2 < tier_3)
  2. most-severe single blocker, by this severity order:
     `scheduled_before_clearance(1) < clinical_code_discrepancy(2) <
      authorization_blocked(3) < records_missing(4) < imaging_missing(5) <
      duplicate_review(6)` (lower number = higher priority)
  3. `referral_id` ascending (final tie-break; INFERRED).
- Emit `{rank, referral_id, priority_tier}`.
