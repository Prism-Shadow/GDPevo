# EHR Quality-Governance Skill

## Purpose
Prepare normalized JSON packets for EHR quality-governance tasks: duplicate-chart merge readiness, referral coordination, care-transition handoffs, duplicate-review with ServiceRequest validation, and referral-batch audits.

## Core Principles

### 1. API-First Data Gathering
Query the EHR environment exhaustively before constructing any answer. Every answer field must be grounded in data returned by the API. Do not guess or interpolate values.

**Standard data-gathering sequence:**
- Read the task prompt to identify the primary entities (patient IDs, referral IDs, duplicate candidate IDs, batch IDs).
- Query the primary entity endpoints first (patient detail, referral detail, duplicate candidate detail).
- Then query all related clinical endpoints (conditions, medications, allergies, encounters, immunizations, documents, service-requests, disclosures).
- Query reference directories (providers, ICD-10 codes, service codes) for every code or provider ID referenced.
- For batch audits, query the full referral list and filter by batch_id; then look up every distinct diagnosis code in the ICD-10 directory.

### 2. Template-Driven Output
Every task includes an `answer_template.json` that is authoritative for field names, types, and enum values. Study it before building the answer.

**Template rules:**
- Required top-level keys must all be present. Missing a required key is a hard failure.
- Enum fields must use exactly one of the listed `allowed_values`. Do not invent new enum values.
- Arrays marked with `set_semantics: true` should be sorted alphabetically unless the template explicitly says otherwise.
- Arrays of objects should be sorted by the field specified in `ordering_rules` or the template annotations (e.g., "Sort by referral_id ascending").
- Date fields use `YYYY-MM-DD` format.
- Boolean fields use `true`/`false` (not strings).

### 3. Normalized Keys
Clinical records carry a `normalized_key` field. Use these keys for all set-union and array fields — never use raw description text or record IDs.

**Key sources:**
- Conditions: use `normalized_key` from each record with `status: "active"`.
- Medications: use `normalized_key` from each record with `status: "active"`.
- Allergies: use `normalized_key` from each record with `status: "active"`.

**Inactive records:** Records with `status: "inactive"` must be excluded from active-key sets and placed in `excluded_distractors` when the template calls for it. Always verify status before including a key.

### 4. Cross-Reference Data Sources
Many answers require reconciling information from multiple endpoints. Common reconciliation patterns:

**Duplicate merge readiness:**
- Compare the duplicate candidate's `merge_preview` keys against the union of active keys from both patients' individual endpoints. The `active_key_unions` should be the full union from patient endpoints. The `active_list_reconciliation` captures what the endpoints add beyond the merge preview.
- Match and conflict signals come from the duplicate candidate API response. Do not invent additional signals.
- Demographic match/conflict fields should reflect the actual match and conflict signals from the duplicate system, expressed as field-level descriptors.

**Referral coordination:**
- Compare the referral's `diagnosis_code` against the patient's active condition list. A code is `referral_relevant` when it relates to the referral's service line or appears in the referral narrative.
- Validate the primary diagnosis code against the ICD-10 directory: check chapter, expected terms, and narrative match. Supporting codes should include other active diagnoses relevant to the referral reason.
- Document evidence: check `documents_received` on the referral against the patient's document list to identify specific document IDs, types, dates, and statuses.

**Referral batch audit:**
- Look up every distinct diagnosis code in the ICD-10 directory. A code whose chapter is not the expected chapter for the service line is `out_of_range_chapter`.
- For laterality/narrative mismatches: compare the ICD-10 `expected_terms` against the referral's `diagnosis_narrative`. A mismatch exists when the narrative describes a different body part, condition, or laterality than the code's expected terms.
- Duplicate detection: group referrals by `patient_id` and check coordination notes for markers like "duplicate resubmission."

### 5. Evidence-Based Classifications
Every classification (risk flag, readiness status, blocking issue, highlight reason) must be supported by explicit data from the API.

**Risk flags:** Map only to the `allowed_values` in the template. Each flag needs evidence drawn from conditions (by normalized_key), medications (by normalized_key), and encounters (by encounter_id) that support it. Evidence arrays should be sorted alphabetically.

**Readiness statuses:** Choose the status that best describes the aggregate evidence. If any required element is missing or incomplete, the status should reflect that — but do not invent blockers. If a referral has approved authorization, received documents, and no clinical mismatches, it is ready unless a coordination note explicitly states a hold.

### 6. Distractor Exclusion
When the template includes `excluded_distractors`, identify records that are:
- Inactive (status is not "active").
- Unrelated to the primary task entities (e.g., audit logs about different patients, documents not related to the merge/referral/transition).
- Stale encounters outside the relevant time window or not relevant to the service line.

### 7. Validated-Ready Classification
For batch audits, a referral is `validated_ready_no_follow_up` only when ALL of these hold:
- Diagnosis code is in the expected chapter for the service line.
- No laterality or narrative mismatch.
- Authorization is approved (not missing or pending).
- All required documents are received (including office_note).
- Not part of a duplicate group.
- No imaging follow-up pending.
- Coordination note does not indicate a clinical concern or hold.

### 8. Action Plan Tiering
Assign each non-validated referral to exactly one tier:
- **Tier 1 (immediate):** urgent referrals with coding issues or duplicate-blocker status. Reason: `urgent_coding_or_duplicate_blocker`.
- **Tier 2 (short-term):** routine referrals with coding, authorization, or document issues. Reason: `routine_coding_auth_or_document_blocker`.
- **Tier 3 (administrative):** referrals that only need document completion or have no clinical issues. Reason: `administrative_document_completion`.

Every referral in the batch must appear in exactly one action-plan tier or be counted as validated-ready. The sum of all tier counts plus validated-ready must equal the total referral row count.

### 9. Provider Contact Selection
When the template requires provider contact information:
- Copy provider details exactly from the provider directory endpoint response — do not modify names, phone numbers, or fax numbers.
- Select the specialist based on the service line of the referral or the external document source referenced in match/audit signals.
- The primary care provider comes from the patient's `primary_care_provider` field.

### 10. Iterative Refinement
After constructing an answer, verify:
- Every required top-level key is present.
- Every enum field uses an allowed value.
- All arrays marked as sets are alphabetically sorted.
- All referenced IDs (patient, provider, document, audit, encounter) exist in the API responses.
- Count fields in `summary_counts` are consistent with the lengths of the corresponding arrays.
- The tier assignments cover every referral exactly once.
- No data was fabricated — every value traces back to an API response.
