# EHR Governance Workflow Patterns

## Task Type 1: Duplicate Merge Readiness Packet

Prompt triggers include `duplicate-chart merge readiness packet`, `duplicate candidate`, and references to two patient IDs.

**Evidence collection sequence:**

1. Fetch the duplicate candidate: `GET /api/duplicates/{candidate_id}`
2. Fetch both patients: `GET /api/patients/{target_id}` and `GET /api/patients/{source_id}`
3. For each patient, fetch active lists: conditions, medications, allergies (filter `status=active`)
4. Fetch documents for both patients: `GET /api/patients/{patient_id}/documents`
5. Fetch audit logs: `GET /api/audit-logs`
6. Fetch provider directory: `GET /api/providers`

**Decision logic:**

- **Target patient**: the one with the more complete active record; the duplicate candidate's `possible_duplicate_patient_id` typically maps to the source.
- **Disposition rules**:
  - `ready_to_merge` / `merge_ready` when identity signals strongly match (same DOB, same insurance, same phone, name variants) and clinical records are complementary.
  - `needs_review` / `needs_manual_review` when there are both match signals and material conflicts (different names, opposite-laterality problems).
  - `do_not_merge` when the duplicate candidate is confirmed as not a duplicate.
- **Manual review**: set to `true` only when conflicts require a human to decide.
- **Active clinical unions**: union the `normalized_key` values from both patients' active condition/medication/allergy lists, sorted alphabetically.
- **Active list reconciliation**: compare the candidate preview's clinical lists against the live patient endpoint lists. Keys present in the live endpoints but missing from the preview are reported as `added_from_active_endpoints`.
- **Inactive keys**: list any conditions/medications from either patient with `status != active` as `excluded_distractors`.
- **Identity signals**:
  - Match: `same_dob`, `same_insurance`, `same_phone`, `same_given_name`, `similar_address`, `name_variant`, `shared_external_*_document`
  - Conflict: `different_given_name`, `different_dob`, `different_insurance`, `different_phone`, `different_address`, `address_abbreviation`, `opposite_laterality_problem`
- **Documents**: include documents that support identity verification or external continuity of care. Exclude `chart_summary` type and unrelated clinical documents.
- **Audit IDs**: select audit records relevant to the merge candidate.
- **Packet contact**: include the specialist provider linked to any external documents on the source record, plus the primary care provider from the target patient.

---

## Task Type 2: Referral Coordination Packet

Prompt triggers include `referral coordination packet`, `referral`, and a specific `REF-*` and patient ID.

**Evidence collection sequence:**

1. Fetch the referral: `GET /api/referrals/{referral_id}`
2. Fetch the patient: `GET /api/patients/{patient_id}`
3. Fetch active conditions, medications, allergies: patient-scoped endpoints
4. Fetch encounters: `GET /api/patients/{patient_id}/encounters`
5. Fetch documents: `GET /api/patients/{patient_id}/documents`
6. Fetch the receiving provider: `GET /api/providers/{receiving_provider_id}`
7. Look up the referral's diagnosis code: `GET /api/icd10/{code}`

**Decision logic:**

- **Active diagnoses**: list all active conditions with their code, description, normalized_key, and source. Mark `referral_relevant=true` for conditions matching the referral's clinical narrative (e.g., heart failure for a cardiology referral); mark others `false`. Sort by code ascending.
- **Referral code set**:
  - `primary_code`: the referral's diagnosis code.
  - `supporting_codes`: additional ICD-10 codes from the referral or active conditions that support the referral's clinical narrative.
  - `icd_validation`: `valid_matches_narrative` when the code exists in ICD-10 and its chapter/description align with the referral narrative. `valid_but_narrative_mismatch` when the code exists but the chapter or description contradicts the narrative. `invalid_code` for unknown codes. `wrong_service_chapter` when the chapter does not match the expected chapter for the service line.
  - `primary_code_chapter`: from the ICD-10 lookup response.
  - `narrative_match`: `true` when the ICD-10 description aligns with the referral's narrative and patient's condition descriptions.
- **Allergy readiness**:
  - `complete_documented` when active allergies are present and documented.
  - `incomplete_needs_clarification` for conflicting or unclear records.
  - `no_known_allergies` when no active allergies exist.
  - `conflicting_allergy_records` when records contradict.
  - `ready_for_letter` is `true` only when allergy information is sufficient.
- **Recent encounter evidence**: select the most recent encounter relevant to the referral. Report its encounter_id, date, type, provider, signed_status, diagnosis codes, medications mentioned, and care_plan_tag.
- **Required document evidence**: check for procedure-specific documents (e.g., echocardiogram for cardiology). Report whether each required type is received, its document_id, and status. List any missing required documents.
- **Receiving provider**: copy provider details from the provider lookup.
- **Authorization readiness**:
  - `overall_readiness`:
    - `ready_to_send` when authorization is approved, documents are present, and no blocking issues exist.
    - `hold_for_authorization` when authorization is pending or missing.
    - `hold_for_missing_documents` when required documents are absent.
    - `hold_for_clinical_clarification` when codes or allergies need review.
  - `blocking_issues`: list applicable enum values from the template.
- **Medication highlights**: list all active medications relevant to the referral's clinical context (e.g., diuretics for heart failure, antihypertensives). Mark each with the appropriate `highlight_reason`.
- **Referral letter fields**: select the single best enum choice for each letter field based on the evidence.

---

## Task Type 3: Care Transition Packet

Prompt triggers include `care transition packet`, a patient ID, and a recipient provider ID (e.g., orthopedic surgery).

**Evidence collection sequence:**

1. Fetch the patient: `GET /api/patients/{patient_id}`
2. Fetch the recipient provider: `GET /api/providers/{provider_id}`
3. Fetch active conditions, medications, allergies
4. Fetch all encounters: `GET /api/patients/{patient_id}/encounters`
5. Fetch immunizations: `GET /api/patients/{patient_id}/immunizations`
6. Fetch disclosures: `GET /api/patients/{patient_id}/disclosures`

**Decision logic:**

- **Patient**: populate patient_id, enterprise_mrn, display_name, dob.
- **Recipient**: populate provider_id, name, facility, service_line.
- **Active clinical keys**: sorted alphabetically by normalized_key, active status only.
- **Handoff encounters**: select the 4 most recent encounters relevant to the surgical handoff. Exclude encounters that are stale (outside the care window) or unrelated to the transition. Sort newest to oldest. Report the selection basis and list both selected and excluded encounter IDs.
- **Latest immunization**: the most recent immunization by date.
- **Disclosure**: filter to the disclosure matching the transition purpose (e.g., `surgical handoff` with status `permitted` and matching recipient provider).
- **Risk flags**: derive from active clinical data:
  - `cognitive_memory_loss` from condition keys like `memory_loss`
  - `fall_risk_note_required` from orthopedic conditions (e.g., knee OA, hip OA) combined with pain medications
  - `hypertension` from the `hypertension` condition key
  - `insulin_dependent_diabetes` from `diabetes_type_2` combined with insulin medications
  - `latex_allergy` from the `latex` allergy key
  - `perioperative_glucose_plan_needed` from diabetes conditions with insulin medications
  - Exclude flags that lack supporting evidence.
- **Risk flag evidence**: for each emitted flag, provide the supporting condition keys, medication keys, and encounter IDs. Sort each sub-array ascending.
- **Packet readiness**:
  - `ready` when all required components are present and no blocking issues.
  - `ready_with_risk_flags` when risk flags exist but no hard blockers.
  - `not_ready` when a required component is missing.

---

## Task Type 4: Duplicate-Review with ServiceRequest Validation

Prompt triggers include `duplicate-review`, `ServiceRequest`, and references to both a duplicate candidate and a service request.

**Evidence collection sequence:**

1. Fetch the duplicate candidate: `GET /api/duplicates/{candidate_id}`
2. Fetch both patients: `GET /api/patients/{patient_id}` for each
3. Fetch the ServiceRequest: `GET /api/patients/{patient_id}/service-requests` and locate by ID
4. Validate service code: `GET /api/service-codes/{code}`
5. Validate reason codes: `GET /api/icd10/{code}` for each reason code
6. Fetch the provider directory as needed

**Decision logic:**

- **Duplicate review**:
  - Decision is `merge` only when candidate status is `confirmed_duplicate`. Otherwise `review_hold` or `do_not_merge`.
  - `merge_target_patient_id` and `merge_source_patient_id` are `null` when not merging.
  - `match_signals` and `conflict_signals`: choose from the template's allowed enum values based on the candidate's signals.
  - `opposite_laterality_problem` conflict: when two patients have opposite-laterality conditions (e.g., left knee vs right knee).
- **ServiceRequest**:
  - `service_code_valid`: `true` if the service code exists in the service-codes directory.
  - `reason_code_validation`: for each reason code, look up the ICD-10 record. `valid` is `true` if the code exists. `chapter` is from the ICD-10 record. `matches_patient_evidence` is `true` when the ICD-10 description aligns with the patient's active conditions.
  - Sort reason_code_validation by code ascending.
- **SBAR coverage**: determine which SBAR sections are present in the ServiceRequest. `complete` is `true` only when all four sections (situation, background, assessment, recommendation) are present.

---

## Task Type 5: Referral Batch Audit

Prompt triggers include `referral audit`, a batch ID (following the pattern `{MONTH}{DD}-{SERVICE_LINE}-{BATCH_LETTER}`), and references to reviewing a batch of referrals.

**Evidence collection sequence:**

1. Fetch all referrals: `GET /api/referrals` and filter by batch_id
2. Load the full ICD-10 directory: `GET /api/icd10`
3. For each patient in the batch, fetch patient detail: `GET /api/patients/{patient_id}`
4. Fetch the provider directory: `GET /api/providers`

**Decision logic:**

- **Batch header**: record the batch_id, service_line, requested_date, record_count (rows in batch), and unique_patient_count (distinct patient IDs).
- **Invalid or out-of-range code referrals**:
  - For each referral, look up its `diagnosis_code` against ICD-10.
  - `unknown_code`: the code does not exist in ICD-10.
  - `out_of_range_chapter`: the code exists but its chapter is not `Musculoskeletal` (for orthopedic batches). Note the `actual_chapter` from ICD-10.
  - Sort results by referral_id ascending.
- **Laterality or narrative mismatch referrals**:
  - For each referral, compare the `diagnosis_narrative` against the ICD-10 code's description, laterality, and terms.
  - `laterality_mismatch`: the code specifies a laterality (left/right) that does not match the narrative's described site.
  - `narrative_mismatch`: the ICD-10 description and terms do not align with the narrative (e.g., lumbar radiculopathy vs meniscus tear, COPD vs knee pain).
  - `missing_laterality`: the narrative omits laterality when the code specifies it.
  - Report the `expected_terms` from the ICD-10 directory.
  - Sort results by referral_id ascending.
- **Duplicate groups**:
  - Identify referrals for the same patient appearing multiple times in the same batch.
  - `duplicate_type` is `same_patient_resubmission`.
  - `recommended_disposition` is `consolidate_under_original`.
  - Sort groups by group_id ascending.
- **Duplicate tiering policy**: assign all duplicate group referral IDs as `tier_1_duplicate_blocker_referral_ids`. List any same-patient referrals that are genuinely separate clinical reviews (different codes) in `separate_same_patient_referral_ids`.
- **Insurance patient anomalies**:
  - Detect referrals for different patients sharing the same `insurance_id`.
  - `recommended_disposition`: `verify_insurance_membership_do_not_merge`.
- **Follow-up queues**:
  - `authorization_missing`: referrals with no authorization status or `not_required` with other issues.
  - `authorization_pending`: referrals with `pending` authorization.
  - `records_request`: referrals missing office-note documents.
  - `imaging_follow_up`: referrals missing or with pending imaging.
  - Each queue: sorted referral_id array, ascending.
- **Action plan**:
  - Tier 1: referrals with urgent coding issues or duplicate blockers. Sort by referral_id.
  - Tier 2: referrals with routine coding, authorization, or document blockers. Sort by referral_id.
  - Tier 3: referrals needing only administrative document completion. Sort by referral_id.
  - Each entry includes referral_id, patient_id, tier label, primary_reason, and owner_provider_id.
- **Summary counts**: compute each integer count from the data. `validated_ready_no_follow_up_count` is the count of referrals that have no issues of any kind.

---

## General Patterns

### Parallelizing API Calls

When fetching data for multiple patients or multiple endpoints, parallelize `curl` calls. Example:

```bash
curl -s http://task-env:9015/api/patients/P-NNNNN | python3 -m json.tool > /tmp/patient_a.json &
curl -s http://task-env:9015/api/patients/P-NNNNN | python3 -m json.tool > /tmp/patient_b.json &
wait
```

### Using jq for Extraction

```bash
# Get active condition keys for a patient, sorted
curl -s http://task-env:9015/api/patients/P-NNNNN/conditions | jq -r '[.[] | select(.status=="active") | .normalized_key] | sort | .[]'
```

### Template-Driven Output

Always use the answer_template.json as the definitive schema. If a field is not present in the template, do not include it. If a field type is ambiguous, match the type shown in the template exactly.
