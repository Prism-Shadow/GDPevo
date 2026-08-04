# EHR Quality-Governance Skill

## Overview

This skill supports generating normalized EHR quality-governance packets from a read-only FHIR-style API. It covers duplicate-chart merge readiness, referral coordination, care transition packets, referral audits, and service-request quality validation. All answers must conform strictly to supplied JSON templates.

## General Principles

### API Interaction

- Use the provided base URL for all GET requests. No POST, PUT, or DELETE endpoints are available.
- Replace path placeholders (`{patient_id}`, `{referral_id}`, `{candidate_id}`, `{code}`, `{provider_id}`) with runtime IDs from the staged input or from prior API responses.
- Supported query parameters:
  - `/api/patients`: `q`, `family`, `given`, `dob`, `insurance_id`
  - `/api/patients/{patient_id}/encounters`: `status`, `limit`
  - Patient collection endpoints: `status`
  - `/api/audit-logs`: `patient_id`, `event`, `date_from`, `date_to`
  - `/api/referrals`: `batch`, `urgency`, `patient`, `status`

### Answer Templates

- Every task provides an `answer_template.json` in `input/payloads/`. Read it first.
- The template defines all required top-level keys, field types, enum values, and ordering rules.
- Arrays described as "sets" should be sorted alphabetically unless the template explicitly overrides ordering.
- Dates use `YYYY-MM-DD` format.
- Boolean fields must be JSON `true`/`false`, not strings.
- Nullable fields must use JSON `null`, not the string `"null"` or omission.
- Enum fields must match one of the allowed values exactly (case-sensitive).

### Distractor Detection

- Items with `normalized_key` values of `baseline_med` or `baseline_allergy` are system-level distractors. Exclude them from clinical key unions, active medication lists, active allergy lists, and risk-flag evidence unless the template or prompt explicitly requires them.
- Inactive records (`status: "inactive"` or `"entered-in-error"`) should be excluded from active-key unions and placed in excluded-distractor arrays when the template provides them.
- Document types like `chart_summary` are generally excluded from merge-packet evidence unless the document is an identity-verification or external-continuity document.

### Evidence Reconciliation

- When a task provides both a preview/summary (e.g., duplicate `merge_preview`) and raw endpoint data (e.g., patient conditions), treat the raw patient-active-list endpoints as authoritative for the complete union.
- Use the preview/summary as a baseline and reconcile by adding keys present in patient endpoints but absent from the preview.
- Reconcile condition, medication, and allergy lists independently.

## Task-Type Patterns

### Duplicate-Chart Merge Readiness

1. Fetch the duplicate candidate (`GET /api/duplicates/{candidate_id}`).
2. Fetch both patients (`GET /api/patients/{patient_id}`) for demographics, canonical status, and primary-care provider.
3. Fetch active conditions, medications, and allergies for both patients.
4. Fetch documents and audit logs for both patients.
5. The merge preview provides preferred target/source and a preview union. Reconcile against active endpoint unions.
6. Identity signals come from the duplicate candidate's `match_signals` and `conflict_signals`.
7. Demographic matches/conflicts derive from comparing patient fields (dob, insurance, phone, address, name).
8. Document selection policy: prefer identity-verification and external-continuity documents. Exclude chart summaries.
9. Specialist provider contact: identify the provider associated with shared external documents (e.g., cardiology import author).

### Referral Coordination

1. Fetch the referral (`GET /api/referrals/{referral_id}`).
2. Fetch the patient, their active conditions, medications, allergies, encounters, and documents.
3. Validate the referral diagnosis code against ICD-10 directory (`GET /api/icd10/{code}`).
4. Check for laterality mismatches: compare the ICD-10 expected laterality with the referral narrative.
5. Check for narrative mismatches: verify that key terms from the ICD-10 description appear in the narrative.
6. Identify the most recent encounter relevant to the referral reason (look at care-plan notes and diagnoses).
7. Classify medications by highlight reason based on clinical relevance to the referral service line.
8. Allergy readiness: check coordination notes for allergy-confirmation instructions.
9. Authorization readiness follows from the referral's authorization and document-receipt status.

### Care Transition Packets

1. Fetch the patient and the recipient provider.
2. Collect active conditions, medications, allergies; exclude `baseline_*` keys.
3. Select the most recent encounters relevant to the transition specialty. Prefer encounters whose diagnoses and care-plan notes align with the target service line.
4. Use exactly the number of handoff encounters the template specifies.
5. Identify the latest immunization by date.
6. Identify the applicable disclosure; check it is `permitted` for the recipient.
7. Derive risk flags from active conditions, medications, allergies, and encounter care-plan notes.
8. For each risk flag, provide evidence linking to condition keys, medication keys, and encounter IDs.

### Referral Batch Audits

1. Fetch all referrals in the batch (`GET /api/referrals?batch={batch_id}`).
2. For each referral, validate the diagnosis code against ICD-10.
3. Codes not in the expected chapter are `out_of_range_chapter`. Codes returning 404 or no entry are `unknown_code`.
4. For codes in the expected chapter, check laterality and narrative alignment.
5. Detect duplicate groups: same patient with multiple referrals for the same clinical issue (check coordination notes and diagnosis codes).
6. Detect insurance anomalies: different patients sharing the same insurance ID.
7. Build follow-up queues: missing authorization, pending authorization, missing office-note records, missing/pending imaging.
8. Assign action-plan tiers: Tier 1 for urgent or duplicate-blocker items, Tier 2 for routine coding/auth/document issues, Tier 3 for administrative document completion.
9. Compute summary counts that are internally consistent with the categorized arrays.

### Service-Request Quality Validation

1. Fetch the service request from the patient's endpoint.
2. Validate the service code against the service-codes directory.
3. Validate each reason code against ICD-10: check validity, chapter, and whether patient evidence supports it (the patient has an active condition with that code).
4. Evaluate SBAR coverage: check that all four sections (situation, background, assessment, recommendation) have non-empty content.
5. For duplicate-review tasks, cross-reference the duplicate candidate's match/conflict signals with the service request's patient and clinical context.

## Sorting and Ordering Conventions

- Arrays of strings (IDs, keys, codes): sort ascending alphabetically unless the template specifies otherwise.
- Arrays of objects with a natural key (referral_id, encounter_id, etc.): sort ascending by that key.
- Handoff encounters: newest to oldest by date.
- Risk flag evidence: sort ascending by risk flag code.
- Referral letter fields and medication highlights: follow template-specified ordering rules.

## Common Pitfalls

- Do not include inactive/entered-in-error records in active-key unions.
- Do not confuse `baseline_med` or `baseline_allergy` normalized keys with clinically meaningful keys.
- Do not include chart-summary documents as merge-packet evidence unless they are identity or external-continuity documents.
- For laterality checks, compare the ICD-10 expected laterality (right/left in expected terms) against the narrative text, not against other code fields.
- Ensure summary counts are arithmetically consistent with the lengths of the arrays they describe.
- Do not double-count referrals that appear in both invalid-code lists and duplicate groups; apply the most specific classification.

