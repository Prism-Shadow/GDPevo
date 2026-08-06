# Cedar Ridge Intake Coordination — Business Rules

Reusable decision logic for each intake workflow. Apply these rules to the data fetched from the API to populate the answer template.

---

## 1. Patient Access Verification (roster-based)

### Insurance status determination
- If the patient record has `insurance_status: "valid"` and insurance is not expired → `valid`
- If the patient record shows expired coverage → `invalid` (reason: `coverage_expired`)
- If coverage is in a pending state → `invalid` (reason: `coverage_pending`)
- If no insurance record exists → `missing`

### Prescription benefit status
- If `prescription_status` is `valid` and PBM is compatible → `valid`
- If PBM is incompatible or policy mismatch → `invalid` (reason: `pbm_invalid` or `pbm_policy_mismatch`)
- If no prescription coverage → `missing` (reason: `pbm_missing`)

### Pharmacy network status
- Cross-reference the patient's `pharmacy_id` against `/pharmacies`.
- `in_network` if the pharmacy's `network_status` is `in_network`.
- `out_of_network` if it exists but is not in network (reason: `pharmacy_out_of_network`).
- `unknown` if the pharmacy cannot be found (reason: `pharmacy_unknown`).

### Registration status decision tree (ordered; first match wins)

| Condition | Registration status | Blocked reason codes |
|---|---|---|
| `insurance_status` is `invalid` AND `service_line` not applicable | `rejected` | `coverage_expired`/`coverage_pending`, `excluded_service_line` |
| `insurance_status` is `invalid` (expired) AND `pharmacy_status` is `out_of_network` | `rejected` | `coverage_expired`, `pharmacy_out_of_network` |
| Multiple blocking issues (3+) | `rejected` | (all applicable codes) |
| `overall_risk` is `high` + any other blocker | `clinical_review` | `overall_risk_high`, (other applicable codes) |
| Any single blocker present | `hold` | (the applicable code) |
| No blockers | `approved` | empty list |

### Blocked reason code triggers

| Trigger | Reason code |
|---|---|
| Insurance expired | `coverage_expired` |
| Insurance pending | `coverage_pending` |
| Emergency contact missing | `emergency_contact_missing` |
| Service line excluded for this patient | `excluded_service_line` |
| Address missing from record | `missing_address` |
| PBM invalid | `pbm_invalid` |
| PBM missing | `pbm_missing` |
| PBM policy mismatch | `pbm_policy_mismatch` |
| Pharmacy out of network | `pharmacy_out_of_network` |
| Pharmacy unknown | `pharmacy_unknown` |
| Preferred contact unavailable | `preferred_contact_unavailable` |
| Overall risk high | `overall_risk_high` |

### Risk scoring
- `lifestyle_risk` and `overall_risk` are taken directly from the patient record.
- If either is elevated above `low`, include `overall_risk_high` in blocked reason codes when the registration decision would otherwise be `approved` or `hold`.

---

## 2. Referral Audit / Readiness

### ICD discrepancy detection
For each ICD code on a referral, fetch `/icd/{code}` and compare:

| Check | Issue code |
|---|---|
| ICD chapter does not match the expected chapter for the service line (e.g., orthopedic referrals expect M00-M99, not S00-T88) | `icd_chapter_mismatch` |
| ICD narrative/description contradicts the referral narrative text | `narrative_mismatch` |
| ICD laterality does not match the referral's documented laterality | `laterality_mismatch` |

### Duplicate detection
- Two or more referrals for the same patient_id with overlapping ICD codes or same clinical context → create a duplicate group.
- Primary referral = earliest non-duplicate or lowest referral_id.
- Recommendation: `consolidate_to_primary` unless the referrals are for distinct anatomical sites with different laterality.

### Shared insurance anomaly
- If two referrals for **different** patient_ids share the same `insurance_id`, flag as `shared_insurance_anomaly`.
- Disposition: `verify_distinct_patient_policy_id` (could be family plan or error).

### Readiness status decision

| Condition | Readiness status |
|---|---|
| Has `auth_blocker` AND `missing_records`/`missing_imaging` | `blocked` |
| Has `missing_imaging` only | `blocked` |
| Has `missing_records` only with auth denied | `blocked` |
| Has `icd_chapter_mismatch` / `narrative_mismatch` / `laterality_mismatch` (coding issue) | `under_review` |
| Has `duplicate_referral` | `under_review` |
| Has `already_scheduled` | `under_review` |
| Has `shared_insurance_anomaly` with no coding issues | `admin_followup` |
| No issues | `ready` |

### Priority tier assignment

| Urgency + context | Priority tier |
|---|---|
| `urgent` referrals with coding or clinical issues | `tier_1_immediate` |
| `routine` referrals with coding issues, network gaps, or missing documents | `tier_2_short_term` |
| `admin` urgency or purely administrative issues (insurance verification, already-scheduled review) | `tier_3_administrative` |

### Action code mapping

| Issue | Action code |
|---|---|
| `icd_chapter_mismatch`, `narrative_mismatch`, `laterality_mismatch` | `request_corrected_icd`, `confirm_narrative`, or `confirm_laterality` as appropriate |
| `duplicate_referral` | `consolidate_duplicate` |
| `shared_insurance_anomaly` | `verify_insurance_id` |
| `missing_records` | `request_records` |
| `missing_imaging` | `request_imaging` |
| `auth_blocker` (pending, denied, not_submitted) | `resolve_authorization` |
| `already_scheduled` | `review_existing_appointment` |

---

## 3. Transfer Review (dialysis / packet-based)

### Packet completeness
A transfer packet is `complete` when all required document types are present. Required documents are listed in the answer template's `missing_required_documents.allowed_values`. Any missing document → `incomplete`.

### Document staleness
Each document type has a `freshness_limit_days`. A document is stale when:
```
(today or as_of_date) - received_date > freshness_limit_days
```
Typical freshness limits (from the portal's document metadata):
- `hbsag`: 30 days
- `hep_b_antibody_core`: 30 days
- `history_physical`: 365 days
- `monthly_labs`: 30 days
- `ppd_or_cxr`: 30 days

### Capacity feasibility

| Packet status | Capacity status | Feasibility |
|---|---|---|
| Complete + all documents fresh | Available chairs > 0 | `ready_on_requested_start` |
| Incomplete or stale documents | Available chairs > 0 | `packet_not_ready_capacity_available` |
| Incomplete or stale documents | No chairs available | `packet_not_ready_capacity_unavailable` |
| Complete | No chairs available | `capacity_unavailable` |

### Final intake decision

| Condition | Decision |
|---|---|
| `ready_on_requested_start` feasibility | `accept` |
| Any `capacity_available` feasibility with packet gaps | `hold` |
| Any `capacity_unavailable` feasibility | `clinical_review` |

### Next contact assignment

| Decision | Owner | Route |
|---|---|---|
| `clinical_review` | `clinical_nurse` | `fax_referring_facility` |
| `hold` (documents needed) | `intake_coordinator` | `fax_referring_facility` |
| `accept` | `scheduling_coordinator` | `phone_patient` |
| No action needed | `none` | `none` |

---

## 4. Program Enrollment Panel (chronic care)

### Eligibility

A candidate is eligible when:
- The patient's chart has an active DM/HTN diagnosis (`has_dmhtn_diagnosis: true`).
- The patient's condition matches the program's target condition.

Ineligible when:
- `wrong_target_condition`: chart diagnosis does not match the program.
- `missing_active_dmhtn_diagnosis`: chart has no active DM/HTN diagnosis.

### Enrollment status

| Condition | Status |
|---|---|
| Eligible AND consent signed AND chart active AND chart artifacts current | `enroll` |
| Eligible but consent missing or chart inactive or stale artifacts | `hold` |
| Consent declined | `reject` |
| Ineligible (wrong condition / missing diagnosis) | `reject` |

### Follow-up cadence

| Clinical context | Cadence |
|---|---|
| Recent hospitalization or ED visit (high-touch flag) | `weekly` |
| Low adherence flag | `weekly` |
| CKD comorbidity | `biweekly` |
| Standard enrollment, no flags | `monthly` |
| On hold (waiting for consent/chart) | `deferred` |
| Rejected | `none` |

### Monitoring package

| Enrollment status + flags | Package type | Components |
|---|---|---|
| `enroll` + high-touch flags | `high_touch_dm_htn` | bp_cuff, glucometer, lab_order_a1c_cmp_lipid, medication_reconciliation, care_plan_setup |
| `enroll` + standard | `standard_dm_htn` | bp_cuff, glucometer, lab_order_a1c_cmp_lipid, medication_reconciliation (care_plan_setup optional) |
| `hold` | `deferred` | consent_packet, chart_update_request |
| `reject` | `not_applicable` | empty |

### First check-in days
- `high_touch_dm_htn`: 7 days
- `standard_dm_htn` with biweekly cadence: 14 days
- `standard_dm_htn` with monthly cadence: 30 days
- `deferred`: `null`
- `not_applicable`: `null`

### Missing chart artifacts
Check the chart response for presence/recency of: `chart_record` (chart_active flag), `active_problems`, `vitals`, `labs`, `medications`, `consent`. Report any that are missing or stale.

### Outreach channel
- `phone` for patients with high-touch flags or low adherence.
- `portal` for patients with portal access and standard enrollment.
- `email` for patients preferring electronic communication.
- `sms` for patients with SMS consent.
- `none` for rejected/deferred.

---

## 5. Referral-to-Chart Activation (pulmonary / chart-focused)

### Readiness assessment
Same as Referral Audit (§2) but with pulmonary-specific blocker codes: `clinical_code_discrepancy`, `records_missing`, `imaging_missing`, `authorization_blocked`, `duplicate_review`, `scheduled_before_clearance`.

### Chart action determination
For referrals that are `ready`:
- If the patient has no active chart → `create_chart`.
- If the patient has an active chart but missing artifacts → `update_chart`.
- If the patient has a complete chart → `no_chart_action`.

### Artifacts to create
Check each of: `demographics`, `active_problems`, `medications`, `allergies`, `vitals`, `labs`, `consent`. List any that are missing from the chart. Sort alphabetically.

### Correspondence queue
For non-ready referrals, determine the template type and reason codes:

| Blocker | Template type | Reason code |
|---|---|---|
| `clinical_code_discrepancy` with wrong service family | `clinical_code_clarification` | `wrong_service_family` |
| `clinical_code_discrepancy` with clinical reason mismatch | `clinical_code_clarification` | `clinical_reason_mismatch` |
| `authorization_blocked` + `records_missing` | `auth_records_request` | `authorization_denied`, `records_missing` |
| `duplicate_review` | `duplicate_resolution` | `duplicate_review` |
| `scheduled_before_clearance` + other blockers | `appointment_hold_notice` | `appointment_already_scheduled` + other codes |

### Priority ordering
Rank non-ready referrals highest-priority first:
1. `tier_1_immediate` referrals with clinical discrepancies
2. `tier_2_short_term` referrals with combined clinical + authorization/records issues
3. `tier_2_short_term` referrals with single-issue blockers
4. Ready referrals are excluded from the priority order list.

---

## General aggregation rules

For all `summary` / `cohort_summary` objects:
- `total_*` must equal the length of the corresponding list, or the sum of status buckets.
- Every bucket key from the template must be present, even if the count is zero.
- Counts are integers.
- `counts_by_urgency_and_status`: a cross-product list, ordered by urgency then readiness_status. Include only combinations with count > 0 (or all combinations with zero — check the template for the convention).
