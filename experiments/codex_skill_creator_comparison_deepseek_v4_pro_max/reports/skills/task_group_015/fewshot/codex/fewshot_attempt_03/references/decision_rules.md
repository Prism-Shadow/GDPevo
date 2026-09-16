# Decision Rule Reference

This catalog covers every deterministic rule needed across the five task families.
Apply rules in the order listed when multiple rules could apply.

## Merge Disposition

Determine the merge outcome from the duplicate candidate and patient records:

1. If the duplicate candidate status is `confirmed_duplicate` or `needs_review`, the candidate record's `possible_duplicate_patient_id` field points to the other patient, and identity match signals outnumber or match conflict signals: disposition is `ready_to_merge` / `merge_ready`, canonical target is the primary patient (the one with more active records), source is the possible duplicate.
2. If the duplicate candidate has sufficient match signals but also non-trivial conflicts (different given_name, different phone, opposite laterality): disposition is `needs_review` / `needs_manual_review` / `review_hold`, target and source are null.
3. If the candidate is `not_duplicate` or has no meaningful match signals: disposition is `do_not_merge`.

## Match and Conflict Signals

Extract signals from the duplicate-candidate record's `match_signals` and `conflict_signals` arrays. The standard controlled signal vocabulary:

**Match signals:** `name_variant`, `same_dob`, `same_insurance`, `same_phone`, `same_given_name`, `similar_address`, `shared_external_cardiology_document`.

**Conflict signals:** `address_abbreviation`, `different_given_name`, `different_phone`, `opposite_laterality_problem`, `different_dob`, `different_insurance`, `different_address`.

**Demographic matches:** Map each match signal to the underlying demographic field: `same_dob` -> `dob`, `same_insurance` -> `insurance_id`, `same_phone` -> `phone`, etc.

**Demographic conflicts:** Map each conflict signal to the underlying field: `different_given_name` -> `given_name_variant`, `address_abbreviation` -> `address_abbreviation`, etc.

## Clinical Union Reconciliation

When building clinical unions for a merge packet:

1. Fetch the duplicate candidate's preview lists (conditions, medications, allergies).
2. Independently fetch each patient's active-list endpoints.
3. The union is the sorted, deduplicated set of all normalized keys from both patients' active endpoints.
4. Record keys present in the patient endpoints but absent from the duplicate preview as `added_from_active_endpoints`.
5. Any keys in the preview but not in either patient's active lists are inactive — include in excluded distractors.

## Document Selection for Merge Packets

Select only documents that are identity-relevant or represent external clinical continuity (outside specialists, labs). Exclude internal chart summaries. The canonical packet document basis is `identity_or_external_continuity_documents_only`.

## ICD-10 Chapter Validation for Referrals

For each referral, look up the diagnosis code via `/api/icd10/{code}`:

1. If the code returns a 404 or is not found: `issue_type` = `unknown_code`.
2. If the code exists but its chapter does not match the service line's expected chapter: `issue_type` = `out_of_range_chapter`. The `actual_chapter` is from the ICD-10 response. The `expected_chapter` is the service-line chapter (e.g., `Musculoskeletal` for orthopedics).
3. For orthopedic referrals specifically: codes in the Injury chapter (S00-T88) that describe knee-related injuries (S80-S89 range) are still out-of-range because the expected chapter is Musculoskeletal.

## Laterality and Narrative Mismatch Detection

For each referral, compare the diagnosis code's ICD-10 description against the referral's `diagnosis_narrative`:

1. **Laterality mismatch:** The code implies a specific side (right/left) via its final digit, but the narrative mentions the opposite side. Flag: `laterality_mismatch`.
2. **Narrative mismatch:** The code description and the narrative describe different conditions or body sites entirely. Flag: `narrative_mismatch`.
3. **Missing laterality:** The code has an implied laterality but the narrative uses a generic term without side qualifier. Flag: `missing_laterality`.

The `expected_terms` array should list the key terms from the ICD-10 code description that the narrative should match.

## Authorization Readiness for Referrals

1. If `authorization_status` is `approved` and no required documents are missing: overall readiness is `ready_to_send`.
2. If authorization is missing or pending: `hold_for_authorization`.
3. If required documents are missing: `hold_for_missing_documents`.
4. If there are clinical mismatches or allergy issues: `hold_for_clinical_clarification`.

## Referral Letter Field Selection

Select each field based on the assembled evidence:

- `diagnosis_summary_choice`: Match to the primary diagnosis narrative (selecting the enum choice that best describes the condition and clinical context).
- `allergy_statement_choice`: Based on allergy readiness status — choose the enum that matches the documented allergy state (e.g., `active_X_Y_Z` when allergies are documented and ready, `no_known_allergies` when the patient has no known allergies, `allergy_details_incomplete` when follow-up is needed).
- `recent_encounter_choice`: Reference the most recent encounter whose care_plan_tag matches the referral intent.
- `document_packet_choice`: Based on whether required documents are received.
- `medication_summary_choice`: Include medications with highlight reasons relevant to the referral service line.
- `recipient_choice`: Based on the receiving provider identified from the referral.
- `authorization_statement_choice`: Direct mapping from authorization_status.
- `readiness_choice`: Direct mapping from overall_readiness.

## Encounter Selection for Care Transitions

For care transition (handoff) packets:

1. Fetch all encounters for the patient.
2. Filter to the service-line window (e.g., orthopedic surgical handoff: last 3 months).
3. Select the 4 most recent encounters by date that are signed and relevant to the transition reason.
4. Order newest to oldest.
5. Exclude encounters that are unsigned, draft, older than the window, or clearly unrelated (wrong service line, non-clinical types).

## Risk Flag Derivation

From the patient's active conditions, medications, and allergies:

- `cognitive_memory_loss`: Any condition with normalized_key matching `memory_loss`.
- `fall_risk_note_required`: Conditions containing hip or knee OA + pain-related medications.
- `hypertension`: Condition with normalized_key `hypertension`.
- `insulin_dependent_diabetes`: `diabetes_type_2` condition + any insulin medication (match by medication normalized_key containing `insulin`).
- `latex_allergy`: Allergy with `latex` in the allergen or normalized key.
- `perioperative_glucose_plan_needed`: `diabetes_type_2` condition + insulin medication.

Each risk flag entry includes the contributing condition_keys, medication_keys, and encounter_ids.

## Disclosure Validation

For care transitions: check the patient's disclosures for a record matching the recipient provider. The disclosure must have status `permitted` for the packet to be ready to send. If missing or not permitted, add a blocking issue.

## Service Code and Reason Code Validation

For ServiceRequest quality review:

1. Look up the service code via `/api/service-codes/{code}`. If found and the service_line matches the performer's service line, `service_code_valid` is true.
2. For each reason code: look up in ICD-10. Validate the code exists, note its chapter, and check whether it matches patient evidence (the code appears in the patient's active conditions or recent encounter diagnoses).
3. The reason code array should include all codes from the ServiceRequest. Sort the validation array by code.

## SBAR Coverage

Check whether the ServiceRequest or associated documentation contains all four SBAR sections: `situation`, `background`, `assessment`, `recommendation`. The presence of each section can be inferred from the ServiceRequest's narrative fields, supportingInfo, or note attachments. Flag missing sections.

## Duplicate Group Detection (Batch Audits)

1. Scan all referrals in the batch for the same patient_id appearing more than once.
2. Group by patient_id. Each group with >1 referral is a duplicate group with `duplicate_type` = `same_patient_resubmission`.
3. The original referral (earliest requested_date or lowest referral_id sort) is the canonical. The duplicates are `tier_1_duplicate_blocker_referral_ids`.
4. Recommended disposition for the group: `consolidate_under_original`.

## Insurance Anomaly Detection

If two different patients share the same insurance_id, flag as `shared_insurance_different_patients`. The recommended disposition is `verify_insurance_membership_do_not_merge`. Do not merge patients solely on shared insurance.

## Follow-Up Queue Classification

For each referral in the batch:

- `authorization_missing`: authorization_status is null, missing, or not_required and the referral is active.
- `authorization_pending`: authorization_status is `pending`.
- `records_request`: office_note document status is `missing` or not received.
- `imaging_follow_up`: imaging document (radiology report, MRI, CT) status is `missing` or not received.

## Action Plan Tier Assignment

For each referral with issues:

- **Tier 1 (Immediate):** Urgent coding issues (invalid chapter for the service line) or duplicate-blocker referrals. Primary reason: `urgent_coding_or_duplicate_blocker`.
- **Tier 2 (Short-term):** Routine coding mismatches, authorization gaps, or document gaps. Primary reason: `routine_coding_auth_or_document_blocker`.
- **Tier 3 (Administrative):** Referrals with only documentation completion needs and no coding or authorization blockers. Primary reason: `administrative_document_completion`.

The owner_provider_id is the performing/receiving provider from the referral, or the batch's default provider.

## Summary Counts

Every batch audit must include:

- Total referral rows, unique patients, urgent vs routine counts.
- Counts for each issue category (invalid codes, mismatches, duplicates, insurance anomalies).
- Counts for each follow-up queue.
- Counts for each action-plan tier.
- `validated_ready_no_follow_up_count`: referrals with no issues at all.
