# Cedar Ridge Business Rules Reference

This reference documents the clinical and administrative rules used to derive controlled values from raw portal data. Every rule is reusable across tasks in the same domain.

---

## Insurance & PBM Rules

### Insurance status

Derive `insurance_status` from the patient's insurance record:

| Finding | Status | Reason code |
|---|---|---|
| Active coverage, not expired, matches expected | `valid` | — |
| Coverage expired or past termination date | `invalid` | `coverage_expired` |
| Coverage pending, application in progress | `invalid` | `coverage_pending` |
| No insurance record found for patient | `missing` | — |
| Service line excluded from coverage | `invalid` | `excluded_service_line` |

### Prescription benefit (PBM) status

Derive `prescription_status` from the PBM/benefit record associated with the patient:

| Finding | Status | Reason code |
|---|---|---|
| Active PBM, valid policy | `valid` | — |
| PBM record present but invalid/expired | `invalid` | `pbm_invalid` |
| PBM record present but policy mismatch | `invalid` | `pbm_policy_mismatch` |
| No PBM record found | `missing` | `pbm_missing` |

---

## Pharmacy Network Rules

Derive `pharmacy_status` by checking the patient's preferred pharmacy against the `/pharmacies` endpoint:

| Finding | Status | Reason code |
|---|---|---|
| Pharmacy ID in network list | `in_network` | — |
| Pharmacy ID not in network list | `out_of_network` | `pharmacy_out_of_network` |
| No pharmacy data or ID unknown | `unknown` | `pharmacy_unknown` |

---

## Risk Classification Rules

### Lifestyle risk

Assessed from the patient chart. Factors include smoking status, BMI, documented substance use, and activity level. Use clinical judgment based on available chart data:

- `low`: No risk factors documented
- `medium`: One or moderate risk factors
- `high`: Multiple or severe risk factors (smoking + high BMI, documented substance use)

### Overall risk

Composite of lifestyle risk, insurance stability, clinical status, and social determinants visible in the chart:

- `low`: All domains clear
- `medium`: One domain has concerns
- `high`: Multiple domains have concerns or any hard blocker exists

A patient with `excluded_service_line`, `coverage_expired`, or multiple missing chart artifacts is typically `overall_risk: high`. A patient whose only issue is a stale document might be `overall_risk: medium`.

Add `overall_risk_high` to blocked reason codes whenever overall_risk is `high`.

---

## Patient Access Verification: Registration Status Rules

The final `registration_status` is determined by the most severe finding:

| Status | Condition |
|---|---|
| `approved` | Insurance valid, PBM valid, pharmacy in network, no risk flags |
| `hold` | Minor issues only (missing address, emergency contact missing, preferred contact unavailable, pharmacy unknown but not blocking) |
| `clinical_review` | Significant issues (pharmacy out of network, PBM invalid, coverage pending, overall risk high, missing required contact info) |
| `rejected` | Hard blockers (coverage expired, excluded service line, PBM policy mismatch with no alternative) |

### Blocked reason codes (patient access verification)

The full set of reason codes for registration tasks is defined by the answer template. Apply codes based on findings:

| Code | Trigger |
|---|---|
| `coverage_expired` | Insurance expired |
| `coverage_pending` | Insurance pending, not yet active |
| `emergency_contact_missing` | No emergency contact in chart |
| `excluded_service_line` | Service line not covered by insurance |
| `missing_address` | No address in patient record |
| `pbm_invalid` | PBM exists but invalid/expired |
| `pbm_missing` | No PBM record |
| `pbm_policy_mismatch` | PBM policy doesn't match requirements |
| `pharmacy_out_of_network` | Pharmacy not in network |
| `pharmacy_unknown` | Pharmacy unknown |
| `preferred_contact_unavailable` | Preferred contact method missing or unreachable |
| `overall_risk_high` | Overall risk assessed as high |

---

## Referral Readiness Rules

### Readiness status determination

Used in referral audit and chart activation tasks. Derive `readiness_status` from the referral record and associated patient/chart/document data:

| Status | Condition |
|---|---|
| `ready` | No issues: ICD matches, records present, imaging present (if needed), auth cleared, not a duplicate, not already scheduled |
| `blocked` | Hard blockers: authorization denied, records missing, imaging missing, scheduled before clearance, or any combination that prevents progress |
| `under_review` | ICD discrepancies, duplicates needing resolution, referral already scheduled elsewhere — needs clinical or operational review |
| `admin_followup` | Insurance anomalies, missing contact info, administrative flags only — no clinical blockers |

### Issue/Blocker codes (referral domain)

| Code | Trigger |
|---|---|
| `icd_chapter_mismatch` | ICD code belongs to wrong chapter for service line |
| `narrative_mismatch` | Referral narrative doesn't match ICD description |
| `laterality_mismatch` | Referral specifies wrong side |
| `duplicate_referral` | Patient has multiple referrals for same service |
| `shared_insurance_anomaly` | Insurance ID shared across different patients |
| `missing_records` | Required medical records not in `/documents` |
| `missing_imaging` | Required imaging studies not in `/documents` |
| `auth_blocker` | Authorization denied or pending |
| `already_scheduled` | Referral has an existing appointment |

---

## ICD Discrepancy Rules

### Chapter mismatch detection

1. Fetch the ICD code metadata from `/icd/{code}`
2. Note the chapter from the metadata response
3. Determine the expected chapter based on the service line:
   - Orthopedic → Chapter 13 (M00-M99, Musculoskeletal)
   - Pulmonary → Chapter 10 (J00-J99, Respiratory)
   - Primary care → varies, usually multiple chapters acceptable
4. If the observed chapter differs from the expected chapter, flag `icd_chapter_mismatch`

### Narrative mismatch detection

Compare the referral narrative text against the ICD code description from `/icd/{code}`. If the narrative describes a substantially different condition, flag `narrative_mismatch`.

### Laterality mismatch detection

If the ICD code has a laterality component (left/right/bilateral indicators in the code or description), check whether the referral narrative confirms the same side. If the referral mentions a conflicting side, flag `laterality_mismatch`.

---

## Duplicate Detection Rules

### Finding duplicate groups

1. Group referrals by `patient_id`
2. Within each patient's group, look for referrals to the same service line or with overlapping ICD codes
3. A duplicate group exists when a patient has multiple referrals that appear to be for the same clinical need

### Determining the primary referral

The primary is the earliest referral (lowest `referral_id` by default, or earliest received date if available). The recommendation is `consolidate_to_primary` — keep the primary and close the duplicates — unless there is a clinical reason to keep them separate (`keep_separate`).

---

## Shared Insurance Anomaly Rules

If two or more referrals with different `patient_id` values share the same insurance/policy identifier:

1. Check if the patients are related (same household, family plan — use chart data)
2. If clearly different patients with no documented relationship, flag `verify_distinct_patient_policy_id`
3. If a legitimate family/same-patient relationship exists, flag `legitimate_duplicate_same_patient`

---

## Authorization Rules

Authorization status is read from the referral record:

| Status | Meaning | Blocker? |
|---|---|---|
| `pending` | Auth submitted but not yet decided | Yes — `auth_blocker` |
| `denied` | Auth denied | Yes — `auth_blocker` |
| `not_submitted` | Auth never submitted | Yes — `auth_blocker` |
| `approved` | Auth granted | No |

An auth blocker means the referral cannot proceed (`readiness_status: blocked`) regardless of other findings.

---

## Document Completeness & Staleness Rules

Applies to transfer packets (dialysis reviews) and any task where document requirements are specified.

### Completeness

A packet is `complete` when every required document type is present in the API's `/documents` records for that patient/transfer. It is `incomplete` when any required document is absent.

Required documents for dialysis transfers include: `allergy_list`, `face_sheet`, `flu_vaccine`, `hbsag`, `hep_b_antibody_core`, `history_physical`, `insurance_proof`, `medication_list`, `monthly_labs`, `physician_orders`, `pneumonia_vaccine`, `ppd_or_cxr`, `transportation`, `treatment_flowsheets`, `vascular_access_report`.

### Staleness

A document is stale when:

```
as_of_date − received_date > freshness_limit_days
```

Typical freshness windows:

| Document type | Freshness limit |
|---|---|
| `hbsag` | 30 days |
| `hep_b_antibody_core` | 30 days |
| `history_physical` | 365 days |
| `monthly_labs` | 30 days |
| `ppd_or_cxr` | 30 days |

Use the task's effective date (today or the as_of_date from the template) as `as_of_date`. The portal's document records include `received_date`.

---

## Capacity & Feasibility Rules

For transfer reviews where chair capacity matters:

1. Determine the requested start date for each transfer from the transfer record
2. Check the portal's capacity data for that date — total open hemodialysis chairs across all Cedar Ridge locations
3. `capacity_status` is `available` if `open_chairs_total >= 1`, otherwise `unavailable`
4. Feasibility combines capacity with packet readiness:

| Packet ready? | Capacity available? | Feasibility |
|---|---|---|
| Yes | Yes | `ready_on_requested_start` |
| No | Yes | `packet_not_ready_capacity_available` |
| No | No | `packet_not_ready_capacity_unavailable` |
| Yes | No | `capacity_unavailable` |

---

## Transfer Decision Rules

The `final_intake_decision` for a transfer:

| Condition | Decision |
|---|---|
| Packet complete, capacity available, no clinical flags | `accept` |
| Minor issues, pending items, capacity may be tight | `hold` |
| Packet incomplete, stale documents, or clinical concerns | `clinical_review` |

---

## Program Eligibility Rules

For chronic-care enrollment panels (e.g., DMHTN programs):

### Eligibility determination

A candidate is `eligible` when:
- The patient has an active diagnosis matching the program's target condition (check chart active problems)
- The patient's chart is active (not archived or inactive)
- The candidate appears in the program's candidate list

A candidate is `ineligible` (`eligible: false`) when:
- The patient has the wrong target condition (`wrong_target_condition`)
- No active diagnosis for the program condition exists (`missing_active_dmhtn_diagnosis`)

### Enrollment status

| Status | Condition |
|---|---|
| `enroll` | Eligible, consent present, chart active, no blockers |
| `hold` | Eligible but missing consent, chart, or key data — can be resolved with outreach |
| `reject` | Ineligible (wrong condition), or consent declined, or chart not active with no path to resolution |

### Reason codes (enrollment domain)

| Code | Meaning |
|---|---|
| `meets_dmhtn_criteria` | Has correct diagnosis and qualifies |
| `recent_hospitalization_high_touch` | Recent hospitalization — needs intensive monitoring |
| `low_adherence_high_touch` | Documented low medication adherence — needs intensive monitoring |
| `ckd_biweekly_monitoring` | CKD comorbidity — biweekly follow-up needed |
| `recent_ed_high_touch` | Recent ER visit — needs intensive monitoring |
| `consent_declined` | Patient declined program consent |
| `consent_missing` | No consent on file |
| `chart_not_active` | Chart is inactive/archived |
| `stale_active_problems` | Active problems list is outdated |
| `missing_recent_vitals` | No recent vitals in chart |
| `missing_recent_labs` | No recent labs in chart |
| `missing_medication_list` | No medication list in chart |
| `wrong_target_condition` | Patient doesn't have DM/HTN diagnosis |
| `missing_active_dmhtn_diagnosis` | No active DM/HTN diagnosis on problem list |

---

## Chart Activation Rules

Used in enrollment panels and referral-to-chart activation tasks.

### Chart action

| Action | Condition |
|---|---|
| `create_chart` | No chart exists for this patient (`/chart/{patient_id}` returns empty or 404) |
| `update_chart` | Chart exists but is missing required artifacts |
| `no_chart_action` | Chart is complete with all required artifacts present |

### Chart artifacts

The standard artifacts to check: `demographics`, `active_problems`, `medications`, `allergies`, `vitals`, `labs`, `consent`.

For a ready referral or an enrolling patient, every missing artifact is one that needs to be created/updated. List them alphabetically as the template directs.

Required artifacts vary by context:
- Enrollment tasks may require consent and medication reconciliation
- Chart activation tasks typically require demographics, active problems, allergies, vitals, labs, consent (and medications if missing)

---

## Monitoring Package Rules

For enrollment panels, the `initial_monitoring_package` depends on the patient's risk and clinical profile:

| Package type | When to use | Typical components | First checkin |
|---|---|---|---|
| `standard_dm_htn` | Routine eligible patients, no high-touch triggers | bp_cuff, glucometer, lab_order_a1c_cmp_lipid, +/- medication_reconciliation | 14–30 days |
| `high_touch_dm_htn` | Recent hospitalization, ED visit, or low adherence | standard components + medication_reconciliation + care_plan_setup | 7 days |
| `deferred` | Patient on hold — needs consent/chart resolution first | consent_packet, chart_update_request | null |
| `not_applicable` | Rejected or ineligible patients | none | null |

---

## Priority Tier Rules

For tasks that rank non-ready referrals:

| Tier | Criteria |
|---|---|
| `tier_1_immediate` | ICD mismatches or clinical discrepancies needing immediate clinician review — these could affect patient safety |
| `tier_2_short_term` | Authorization issues, missing records/imaging — can be resolved in days with outreach |
| `tier_3_administrative` | Insurance verification, contact updates, duplicate resolution — administrative work, no clinical urgency |

Order within a tier by ascending referral_id. Rank 1 is the highest priority item.

---

## Correspondence Template Rules

For chart activation tasks, the correspondence template type matches the primary issue:

| Primary issue | Template type |
|---|---|
| ICD code discrepancy, wrong service family, clinical reason mismatch | `clinical_code_clarification` |
| Authorization denied, records missing, imaging missing | `auth_records_request` |
| Duplicate referral group | `duplicate_resolution` |
| Appointment already scheduled before clearance | `appointment_hold_notice` |

The `reason_codes` in the correspondence entry are the specific reasons this correspondence is needed — use the template's allowed values.

---

## Cohort Summary Rules

Every summary block must be derived from the per-item results, never guessed. The process is:

1. Complete all per-patient/per-referral processing first
2. Count each status/category across the cohort
3. Verify that `total` matches the number of items processed
4. Verify that sub-counts sum to the correct totals

For cross-tabulations like `counts_by_urgency_and_status`, iterate over all items, produce the (urgency, status) pairs, and count each combination. Include only combinations that have count > 0, ordered as the template specifies.
