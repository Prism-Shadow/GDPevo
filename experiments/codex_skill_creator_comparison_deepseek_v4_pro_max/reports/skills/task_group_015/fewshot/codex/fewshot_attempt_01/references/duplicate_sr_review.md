# Duplicate + ServiceRequest Quality Review Packet

Use when the task asks to validate a duplicate review outcome alongside a ServiceRequest quality signal, typically with a candidate ID, a primary patient, a possible duplicate, and a draft ServiceRequest.

## Input Signals

- A duplicate candidate ID, primary patient ID, possible duplicate patient ID, and ServiceRequest ID in the task prompt.
- An answer_template.json with keys: task_id, duplicate_review, service_request, sbar_coverage.

## Evidence Gathering Order

1. GET /api/duplicates/{candidate_id} - candidate detail, status, match/conflict signals.
2. GET /api/patients/{primary_id}, GET /api/patients/{duplicate_id} - demographics for comparison.
3. GET /api/patients/{primary_id}/service-requests - find the target ServiceRequest by ID.
4. GET /api/service-codes/{service_code} - validate the service code on the request.
5. GET /api/icd10/{code} for each reason code on the ServiceRequest.
6. GET /api/providers/{requester_id}, GET /api/providers/{performer_id}.
7. GET /api/patients/{primary_id}/conditions - cross-check ServiceRequest reason codes against patient conditions.

## Reconciliation Rules

### Duplicate Review

- candidate_status: from the duplicate candidate record status field.
- decision: merge when status is confirmed_duplicate and identity is strong; review_hold when needs_review; do_not_merge when not_duplicate.
- merge_target_patient_id and merge_source_patient_id: set when a merge decision is made; set to null when on review hold or do-not-merge.
- match_signals: from the candidate record. Use only the enum values listed in the template.
- conflict_signals: from the candidate record and demographic comparison. Include opposite_laterality_problem when the patients active conditions suggest opposite-laterality OA or injuries.

### ServiceRequest Validation

- Copy the ServiceRequest fields directly from the API response, mapping to template enums.
- service_code_valid: true when the service code exists in the service-codes directory.
- performer_service_line: from the performer provider service_line field.
- reason_code_validation: for each reason code, look up the ICD-10 code and report whether it is valid, its chapter, and whether it matches patient evidence (i.e., the code appears in the patients active conditions or encounter diagnoses).

### SBAR Coverage

- ServiceRequest records may carry an sbar_sections field listing which SBAR sections are present.
- complete: true when all four sections (situation, background, assessment, recommendation) are present.
- sections_present and missing_sections derive from the SBAR section list.

## Output Shape

Follow answer_template.json exactly. Arrays with set semantics should be sorted. Use null (not empty string) for absent merge target/source fields.
