# Cedar Ridge Business Rules

This reference contains the decision logic used across all task types. Load it when making any patient-level or referral-level determination.

---

## Insurance Status Determination

From `chart.coverage` (array of coverage records):

| Condition | insurance_status |
|---|---|
| Coverage array empty or null | `missing` |
| All coverage records have `status != "active"` | `invalid` |
| Active coverage exists but `termination_date` is in the past | `invalid` |
| Active coverage exists but `service_lines` does not include the task's service line | `invalid` |
| Active coverage exists, `network_status` is not "in_network" for any active record | `invalid` |
| Active coverage exists, in-network, service line included, not terminated | `valid` |

**Blocked reason codes for insurance:**
- `coverage_expired`: active coverage past termination_date
- `coverage_pending`: coverage exists but not active
- `excluded_service_line`: service_line not in coverage's service_lines field
- `missing_address`: patient address is null

---

## Prescription (PBM) Status Determination

From `chart.pbm` (array of PBM records):

| Condition | prescription_status |
|---|---|
| PBM array empty or null | `missing` |
| All PBM records have `active == 0` | `invalid` |
| Any PBM record has `status != "approved"` and it is the only relevant one | `invalid` |
| At least one PBM record is active and approved | `valid` |

**Blocked reason codes for PBM:**
- `pbm_missing`: no PBM records
- `pbm_invalid`: PBM exists but not active/approved
- `pbm_policy_mismatch`: policy_number mismatch between coverage and PBM

---

## Pharmacy Status Determination

From `chart.pharmacies` (array of pharmacy records):

| Condition | pharmacy_status |
|---|---|
| Pharmacy array empty or null | `unknown` |
| At least one pharmacy has `network_status == "in_network"` | `in_network` |
| All pharmacies have `network_status == "out_of_network"` | `out_of_network` |

**Blocked reason codes for pharmacy:**
- `pharmacy_unknown`: no pharmacy records
- `pharmacy_out_of_network`: all pharmacies are out_of_network

---

## Lifestyle Risk Determination

From `chart.lifestyle`:

Risk is evaluated cumulatively. Count the number of elevated factors:

- `smoking_status == "Current"` → elevated
- `alcohol_use == "Heavy"` or `"Moderate"` → elevated
- `exercise_frequency == "None"` → elevated
- `sleep_hours < 6.0` → elevated

| Total elevated factors | lifestyle_risk |
|---|---|
| 0 | `low` |
| 1 | `medium` |
| 2+ | `high` |

If `chart.lifestyle` is null, treat as `low`.

---

## Overall Risk Determination

| Condition | overall_risk |
|---|---|
| lifestyle_risk is high | `high` |
| lifestyle_risk is medium AND any other status is non-ideal (insurance invalid/missing, prescription invalid/missing, pharmacy out_of_network/unknown) | `high` |
| lifestyle_risk is medium AND all other statuses normal | `medium` |
| lifestyle_risk is low AND any status is non-ideal | `medium` |
| All statuses normal (insurance valid, prescription valid, pharmacy in_network, lifestyle low) | `low` |

**Blocked reason code for overall risk:**
- `overall_risk_high`: when overall_risk is high

---

## Registration Status (Patient Access Verification)

| Condition | registration_status |
|---|---|
| overall_risk is high | `clinical_review` |
| insurance_status is invalid and service line is excluded | `rejected` |
| insurance_status is invalid (not excluded) | `clinical_review` |
| Any blocker exists that is not auto-reject | `hold` |
| No blockers, all statuses valid/normal | `approved` |

**Additional blocked reason codes for patient-level issues:**
- `emergency_contact_missing`: `emergency_contact_present == 0`
- `preferred_contact_unavailable`: preferred_contact is "phone" but phone is null, or "email" but email is null, or "sms" but phone is null

---

## ICD Chapter / Service Family Mapping

The expected ICD chapter for each service line:

| service_line | Expected ICD Chapter |
|---|---|
| `orthopedics` | M00-M99 |
| `pulmonary` | J00-J99 |
| `cardiology` | I00-I99 |
| `primary_care` | (any) |
| `neurology` | G00-G99 |
| `dermatology` | L00-L99 |

When the ICD code's chapter (from `/icd/{code}`) does not match the expected chapter for the referral's service_line, flag `icd_chapter_mismatch`.

When the ICD code's `service_family` (from `/icd/{code}`) does not match the referral's `service_line`, flag `clinical_code_discrepancy` / `wrong_service_family`.

When the referral reason or diagnosis description conflicts with the ICD code's description, flag `narrative_mismatch` / `clinical_reason_mismatch`.

When a laterality-aware ICD code (laterality is non-null) does not match lateral information in the referral, flag `laterality_mismatch`.

---

## Duplicate Detection

Two referrals for the **same patient** (`patient_id`) AND **same ICD-10 code** (`icd10_code`) are treated as duplicates. This covers both exact matches and cases where a second practice faxes the same referral.

Referrals with `notes == "possible duplicate"` are suspected duplicates. Apply the patient+ICD grouping test:
- If they share both patient_id and icd10_code → true duplicate, `consolidate_to_primary`
- If they differ in patient_id or icd10_code → reviewed and cleared (not a duplicate)

The primary referral is the one with the lower (earlier) referral_id.

**Blocked reason code:** `duplicate_referral`

---

## Shared Insurance Anomalies

When two (or more) referrals share the same `insurance_id` but have different `patient_id` values, flag as a shared insurance anomaly.

For each anomaly:
- `disposition`: `verify_distinct_patient_policy_id` when different patients share the same insurance ID (possible data error)
- `disposition`: `legitimate_duplicate_same_patient` when the same patient_id is involved (already covered by duplicate logic)

---

## Authorization Blockers

From referral fields:

| auth_status | Blocker |
|---|---|
| `denied` | auth_blocker |
| `pending` | auth_blocker |
| `not_required` | not a blocker |
| `approved` | not a blocker |

**For correspondence:** `auth_status == "denied"` → reason code `authorization_denied`

---

## Records and Imaging Blockers

| Referral field value | Blocker |
|---|---|
| `records_received == 0` | `records_missing` or `missing_records` |
| `imaging_received == 0` | `imaging_missing` or `missing_imaging` |

---

## Priority Tiers

| Condition | Priority Tier |
|---|---|
| `urgency == "urgent"` | `tier_1_immediate` |
| `urgency == "routine"` and not admin-level issue | `tier_2_short_term` |
| Purely administrative issues (shared insurance anomaly only, no clinical blockers) | `tier_3_administrative` |
| `urgency == "admin"` | `tier_3_administrative` |

---

## Readiness Status (Referral Audits)

| Condition | readiness_status |
|---|---|
| No blockers, no issues, not already scheduled | `ready` |
| Has authorization, records, or imaging blockers | `blocked` |
| Has ICD discrepancy but no hard blockers | `under_review` |
| Has insurance anomaly (only), no hard blockers | `admin_followup` |
| Already scheduled (`appointment_scheduled == 1`) | `under_review` |

---

## Dialysis Transfer Required Documents

The fifteen required document types for a complete transfer packet:

1. `allergy_list`
2. `face_sheet`
3. `flu_vaccine`
4. `hbsag`
5. `hep_b_antibody_core`
6. `history_physical`
7. `insurance_proof`
8. `medication_list`
9. `monthly_labs`
10. `physician_orders`
11. `pneumonia_vaccine`
12. `ppd_or_cxr`
13. `transportation`
14. `treatment_flowsheets`
15. `vascular_access_report`

For each transfer, fetch `GET /documents?patient_id={patient_id}&transfer_id={transfer_id}` (or `/chart/{patient_id}` documents section). A document is considered received only if `finalized == 1`. A document with `status == "draft"` or `finalized == 0` is not received.

**Missing required documents** = required documents not present (or present as unfinalized) in the patient's document list for that transfer.

### Document Freshness / Staleness

Time-sensitive document types and their freshness limits:

| doc_type | Freshness Limit (days) |
|---|---|
| `hbsag` | 30 |
| `hep_b_antibody_core` | 30 |
| `history_physical` | 365 |
| `monthly_labs` | 30 |
| `ppd_or_cxr` | 30 |

A document is stale if `(current_date - received_date) > freshness_limit_days`. Use the as-of date from the task context or the current date per the task. For train tasks, use the implied date from the task description.

---

## Feasibility for Transfer Requested Start

From transfer `requested_start_date` and `chair_window`:

1. Query all transfers for the same `requested_start_date` and `chair_window` using SQL.
2. Count existing scheduled transfers for that date+window.
3. Determine `capacity_status`: compare against capacity. If transfers for that date+window reach capacity, `unavailable`. Otherwise `available`.
4. `open_chairs_total` = capacity - scheduled_count for that date+window.

Feasibility is a combination of packet readiness and capacity:

| Packet complete? | Capacity? | feasibility |
|---|---|---|
| Yes | Available | `ready_on_requested_start` |
| No | Available | `packet_not_ready_capacity_available` |
| Yes | Unavailable | `capacity_unavailable` |
| No | Unavailable | `packet_not_ready_capacity_unavailable` |

---

## Transfer Final Intake Decision

| Condition | final_intake_decision |
|---|---|
| Packet complete and capacity available | `accept` |
| Packet incomplete or capacity unavailable but fixable | `clinical_review` |
| Severe issues requiring escalation | `hold` |

---

## Transfer Next Contact

| Decision | next_contact_owner | next_contact_route |
|---|---|---|
| clinical_review (missing docs) | `clinical_nurse` | `fax_referring_facility` |
| clinical_review (capacity) | `scheduling_coordinator` | `internal_queue` |
| accept | `scheduling_coordinator` | `phone_patient` |
| hold | `intake_coordinator` | `internal_queue` |

---

## Program Eligibility (example program)

For a diabetes+hypertension program:

| Condition | eligible |
|---|---|
| `target_condition == "diabetes_hypertension"` | true |
| `target_condition != "diabetes_hypertension"` | false (wrong_target_condition) |

Additional eligibility checks:
- `consent_status == "signed"` required for enrollment
- `consent_status == "declined"` → reject with `consent_declined`
- `consent_status == "missing"` → hold with `consent_missing`
- Patient must have an active chart (`existing_chart == 1` and chart artifacts are current)
- Missing chart artifacts (`chart_record` if no chart, individual artifacts if stale/missing) go in `missing_chart_artifacts`

---

## Enrollment Status

| Condition | enrollment_status |
|---|---|
| Eligible, consent signed, chart active, no issues | `enroll` |
| Eligible but consent missing or chart issues | `hold` |
| Consent declined, or wrong target condition, or missing active program diagnosis | `reject` |

---

## Enrollment Reason Codes

| Code | When applied |
|---|---|
| `meets_dmhtn_criteria` | target_condition matches, consent not declined |
| `recent_hospitalization_high_touch` | `recent_hospitalization == 1` |
| `low_adherence_high_touch` | `adherence_score < 50` |
| `ckd_biweekly_monitoring` | `chronic_conditions` contains "ckd" |
| `recent_ed_high_touch` | risk_flags include recent ED visit |
| `consent_declined` | `consent_status == "declined"` |
| `consent_missing` | `consent_status == "missing"` |
| `chart_not_active` | `existing_chart == 0` or chart artifacts stale |
| `stale_active_problems` | active_problems artifact missing or status == "stale" |
| `missing_recent_vitals` | vitals artifact missing |
| `missing_recent_labs` | labs artifact missing |
| `missing_medication_list` | medications artifact missing |
| `wrong_target_condition` | `target_condition` doesn't match program |
| `missing_active_dmhtn_diagnosis` | active_problems doesn't show diabetes or hypertension |

---

## Follow-Up Cadence

| Trigger | cadence |
|---|---|
| High touch (recent_hospitalization, low_adherence, recent ED) | `weekly` |
| CKD monitoring | `biweekly` |
| Standard enrollment (meets criteria, no high-touch triggers) | `monthly` |
| Hold (consent missing, chart issues) | `deferred` |
| Rejected | `none` |

---

## Outreach Channel

Use the candidate's `preferred_outreach` field:
- `portal` → `portal`
- `phone` → `phone`
- `email` → `email`
- `sms` → `sms`

For rejected patients still needing notification, use their preferred_outreach anyway.

---

## Initial Monitoring Package

| Package Type | When | Components | first_checkin_days |
|---|---|---|---|
| `high_touch_dm_htn` | High-touch enrollment (weekly) | bp_cuff, glucometer, lab_order_a1c_cmp_lipid, medication_reconciliation, care_plan_setup | 7 |
| `standard_dm_htn` | Standard enrollment (biweekly or monthly) | bp_cuff, glucometer, lab_order_a1c_cmp_lipid, medication_reconciliation | 14 for biweekly, 30 for monthly |
| `deferred` | Hold | consent_packet, chart_update_request | null |
| `not_applicable` | Rejected | [] (empty) | null |

---

## Chart Activation (Referral-to-Chart)

For ready referrals, determine what chart artifacts need creation:

1. Check `GET /chart/{patient_id}` → `chart_artifacts`
2. Missing artifact types → add to `artifacts_to_create`
3. Stale artifacts (status == "stale") → add to `artifacts_to_create`
4. `chart_action`:
   - `create_chart` if `existing_chart == 0`
   - `update_chart` if chart exists but artifacts missing/stale
   - `no_chart_action` if chart is complete and current

The seven possible artifact types: `demographics`, `active_problems`, `medications`, `allergies`, `vitals`, `labs`, `consent`

---

## Correspondence Templates (Referral-to-Chart)

| Condition | template_type | reason_codes |
|---|---|---|
| ICD chapter/service_family mismatch | `clinical_code_clarification` | `wrong_service_family` or `clinical_reason_mismatch` |
| Authorization denied or records missing | `auth_records_request` | `authorization_denied`, `records_missing` |
| Duplicate referral needs resolution | `duplicate_resolution` | `duplicate_review` |
| Already scheduled with blockers | `appointment_hold_notice` | `appointment_already_scheduled` plus other blockers |

---

## Priority Order (Referral-to-Chart)

For non-ready referrals only, rank highest priority first:

1. `tier_1_immediate` referrals first (urgency == urgent, clinical_code_discrepancy or any urgent blocker)
2. `tier_2_short_term` referrals second
3. `tier_3_administrative` referrals last

Within the same tier, order by referral_id ascending.
