# Business Rules — Cedar Ridge Intake Coordination

Field-by-field mapping rules for mapping raw portal rows to the controlled values in each task's `answer_template.json`. Rules are stated generically (no per-record values). Where a threshold is inferred rather than certain, it is marked **(verify)** — confirm against the data distribution and the template before relying on it.

## 1. New-patient access verification (roster → per-patient)

### insurance_status — `valid | invalid | missing`
- `missing` — no row in `coverage` for the patient.
- `invalid` — coverage exists but is not usable for this service on the requested service date: status `expired`, status `pending`, OR the service line is **not** in `coverage.service_lines` (excluded service line), OR `termination_date` is before the requested service date.
- `valid` — status `active`, `network_status` in-network, service line IS in `service_lines`, and not terminated before the service date.

Reason codes that pair with insurance: `coverage_expired` (status expired / terminated before service date), `coverage_pending` (status pending), `excluded_service_line` (service line not in `service_lines`).

> An active policy that **excludes** the requested service line makes `insurance_status = invalid` — `excluded_service_line` is not merely a separate note; it invalidates coverage for that service.

### prescription_status — `valid | invalid | missing` (from `pbm`)
- `missing` — no `pbm` row.
- `invalid` — `active = 0`, OR `status != approved`, OR `formulary_status != covered`, OR the PBM `policy_number` does not match the coverage `policy_number` (policy mismatch).
- `valid` — `active = 1`, `status = approved`, `formulary_status = covered`, and policy matches coverage.

Reason codes: `pbm_invalid` (inactive / not approved / not covered), `pbm_policy_mismatch` (policy number differs from coverage), `pbm_missing` (no PBM row).

### pharmacy_status — `in_network | out_of_network | unknown` (from `patient_pharmacy` + `pharmacies`)
- Use the patient's rank-1 (`preference_rank = 1`) preferred pharmacy.
- `in_network` / `out_of_network` from that pharmacy's `network_status`.
- `unknown` — no preferred pharmacy on file.

Reason codes: `pharmacy_out_of_network`, `pharmacy_unknown`.

### Other access blockers (from `patients`)
- `emergency_contact_missing` — `emergency_contact_present = 0`.
- `missing_address` — `address` is null.
- `preferred_contact_unavailable` — the patient's `preferred_contact` method is not reachable (e.g., preferred `email` but `email` is null; preferred `sms` but `phone` is null).

### Risk (from `lifestyle` + `clinical_history`)
- `lifestyle_risk` — combine lifestyle factors: current smoker, heavy alcohol, no exercise, low sleep. **(verify thresholds)** A simple count of high-risk factors (current smoker, heavy alcohol, exercise = None, sleep < 6h) with 0 → low, 1 → medium, ≥2 → high is a reasonable starting point; treat a null exercise value as unknown (not a risk factor) unless the data says otherwise.
- `overall_risk` — combine lifestyle risk with clinical acuity from `clinical_history`: `recent_hospitalization = 1`, non-empty `risk_flags` (e.g., `recent_ed_visit`, `fall_risk`, `complex_medication_reconciliation`), and chronic-condition burden. **(verify)** Overall is typically high when lifestyle is high or a clinical risk flag is present.
- `overall_risk_high` reason code fires when `overall_risk = high`.

### registration_status — `approved | hold | clinical_review | rejected` **(verify priority)**
A reasonable priority order (hard blocks first):
1. `rejected` — hard coverage block (`coverage_expired`, `excluded_service_line`).
2. `clinical_review` — `overall_risk_high` (no harder block).
3. `hold` — resolvable admin blockers (`coverage_pending`, `pbm_*`, `pharmacy_*`, `missing_address`, `emergency_contact_missing`, `preferred_contact_unavailable`).
4. `approved` — no blockers.

List **all** applicable reason codes in `blocked_reason_codes` (unordered set), regardless of which one drives the status.

## 2. Referral readiness / activation (batch → per-referral)

### Per-referral issue / blocker codes (objective findings — get these right)
- `clinical_code_discrepancy` / icd discrepancy — the referral's `icd10_code` has `service_family` (in `icd_codes`) that does **not** match the batch's `service_line`. (Compare `icd_codes.service_family` to `referrals.service_line`; the ICD **chapter** is not enough — use `service_family`.) Also watch narrative/laterality mismatches between the referral narrative and the ICD description/laterality.
- `records_missing` — `records_received = 0`.
- `imaging_missing` — `imaging_received = 0`.
- `authorization_blocked` — `auth_required = 1` AND `auth_status != approved` (i.e., pending, denied, not_submitted).
- `duplicate_referral` / `duplicate_review` — same patient + same/similar ICD + same reason (often hinted by a "possible duplicate" note or a suspicious referring practice name).
- `shared_insurance_anomaly` — the same `insurance_id` appears across **different** patients.
- `already_scheduled` / `scheduled_before_clearance` — `appointment_scheduled = 1`.

### readiness_status — `ready | blocked | under_review | admin_followup`
A defensible mapping (verify per task):
- `ready` — no blockers.
- `blocked` — `records_missing`, `imaging_missing`, `authorization_blocked`.
- `under_review` — clinical-code discrepancy, duplicate review (needs verification).
- `admin_followup` — already-scheduled / administrative follow-up.
When a referral has multiple blockers, the readiness reflects the dominant one.

### Duplicate & shared-insurance handling
- `duplicate_groups` — group referrals that are true duplicates (same patient + same condition). For each group: `referral_ids` (ascending), `patient_id`, the primary/kept referral, and a recommendation (`consolidate_to_primary` or `keep_separate`).
- `cleared_duplicate_review_referrals` — referrals flagged for duplicate review (e.g., "possible duplicate" note) that were reviewed and determined **not** to be duplicates. These have no duplicate blocker and are ready (if no other blockers).
- `shared_insurance_anomalies` — group by shared `insurance_id` across different patients; disposition `verify_distinct_patient_policy_id` when patients differ, `legitimate_duplicate_same_patient` when it is the same patient.

### blocker_sets
Separate ascending lists of referral IDs for each hard blocker: authorization, records, imaging (and auth-status sub-list if the template wants it).

### ready_referral_chart_needs (ready referrals only)
- `chart_action`: `create_chart` if `existing_chart = 0`; `update_chart` if a chart exists but artifacts are stale/missing; `no_chart_action` if the chart is complete.
- `artifacts_to_create`: for `create_chart`, all chart artifacts; for `update_chart`, the artifacts that are absent or stale (per `chart_artifacts.status`).

### correspondence_queue & priority_order
- One correspondence item per non-ready referral, template chosen by the dominant blocker (`clinical_code_clarification`, `auth_records_request`, `duplicate_resolution`, `appointment_hold_notice`); reason codes mirror the blocker codes mapped to the template's reason vocabulary.
- `priority_order` ranks non-ready referrals: authorization blockers → tier 1 (immediate); records/imaging/clinical-code → tier 2 (short-term); already-scheduled/duplicate/admin → tier 3 (administrative). Rank highest priority first; tie-break by referral ID.

## 3. Transfer packet review (batch → per-transfer)

### packet completeness & missing docs
- Required document set is the template's `allowed_values` for `missing_required_documents`.
- A document is **missing** if it is absent OR a draft (`status = draft` / `finalized = 0`). Drafts count as missing — a non-finalized document is not acceptable for a complete packet.
- `transportation` is satisfied by the transfer's `transportation` field (null → missing), not by a separate document.
- `packet_completeness_status` = `complete` only when nothing is missing.

### stale documents
- Only the doc types the template lists as stale-able (e.g., `hbsag`, `hep_b_antibody_core`, `history_physical`, `monthly_labs`, `ppd_or_cxr`) are checked.
- A doc is stale when `(reference_date - received_date)` exceeds the doc type's `freshness_limit_days`. The reference date is the transfer's `requested_start_date` **(verify)**. Limits are doc-type-specific (monthly_labs ≈ 30d; annual docs ≈ 365d) — **verify the exact limits** against the data; report `received_date` and `freshness_limit_days` per stale doc.

### requested_start feasibility
- `capacity_status` / `open_chairs_total` from `facility_capacity` summed across locations for the `requested_start_date` and modality. If no capacity row exists for that date+modality, treat as unavailable / 0 open chairs.
- `feasibility`: `ready_on_requested_start` (packet complete + capacity available); `packet_not_ready_capacity_available`; `packet_not_ready_capacity_unavailable`; `capacity_unavailable` (packet complete but no capacity).

### final_intake_decision & next contact
- `accept` — ready on requested start.
- `clinical_review` — clinical risk flag in `clinical_history.risk_flags` (e.g., `fall_risk`, `complex_medication_reconciliation`) **(verify)**.
- `hold` — packet incomplete or capacity unavailable (no clinical flag).
- `next_contact_owner`/`route`: clinical flag → clinical nurse / phone patient; packet incomplete → intake coordinator / fax referring facility; capacity unavailable → scheduling coordinator / internal queue; accept → scheduling coordinator / internal queue. **(verify)**

## 4. Chronic-care enrollment panel (program → per-candidate)

### eligibility (boolean)
Eligible iff ALL of: `target_condition` matches the program's condition; `consent_status = signed`; `existing_chart = 1` and chart active; an active diagnosis for the target condition present (check `clinical_history.chronic_conditions` and `chart_artifacts.active_problems` status); recent vitals/labs/medications current (`chart_artifacts.status = current`).

### enrollment_status — `enroll | hold | reject`
- `enroll` — eligible.
- `reject` — hard disqualifier: wrong target condition, missing active diagnosis, consent declined.
- `hold` — fixable: consent missing, chart not active, stale/missing artifacts.

### reason codes
- Eligible/enrolled: `meets_dmhtn_criteria` plus monitoring-intensity flags (`recent_hospitalization_high_touch`, `recent_ed_high_touch`, `low_adherence_high_touch` from low adherence score, `ckd_biweekly_monitoring` when CKD present).
- Not eligible: `wrong_target_condition`, `missing_active_dmhtn_diagnosis`, `consent_declined`, `consent_missing`, `chart_not_active`, `stale_active_problems`, `missing_recent_vitals`, `missing_recent_labs`, `missing_medication_list`.

### follow-up cadence / monitoring package / outreach
- Cadence: high-touch (recent hosp/ED or low adherence) → weekly; CKD → biweekly; standard → monthly; hold → deferred; reject → none. **(verify)**
- Package: high-touch → `high_touch_dm_htn`; standard (incl. CKD-only) → `standard_dm_htn`; hold → `deferred`; reject → `not_applicable`. **(verify)**
- Outreach: use `preferred_outreach` when the corresponding contact field is present; otherwise fall back to an available channel; reject → none.
- `first_checkin_days`: weekly ≈ 7, biweekly ≈ 14, monthly ≈ 30; null for deferred/not_applicable.

### missing_chart_artifacts
Required artifact set is the template's allowed list. Missing = absent or stale artifact; include `chart_record` when `existing_chart = 0`. **(verify whether stale counts as missing for this list.)**

## General cautions

- **Objective findings are the substance of the answer.** Deterministic per-record findings (statuses, blocker/reason codes, missing-item lists, duplicate/insurance groups, capacity) must be exact. Derived rollup statuses and cohort summaries are secondary — but they must still be internally consistent with the per-record outputs.
- **Templates differ between tasks.** Always re-read the current task's `answer_template.json`; enum values and reason-code vocabularies change (e.g., referral blocker codes vs. transfer blocker codes). Never carry a vocabulary over from a different task.
- **Re-run schema introspection.** Verify the table/column set for the current portal before joining (see `reference/portal_schema.md`).
- **Watch the date semantics.** Coverage termination vs. requested service date; document received_date vs. requested_start_date freshness; capacity rows exist only for specific date+modality combinations (often only certain weekdays).
