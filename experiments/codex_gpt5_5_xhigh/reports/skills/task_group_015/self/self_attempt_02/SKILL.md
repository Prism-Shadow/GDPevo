---
name: ehr-governance-json-packets
description: Build normalized JSON packets and audits from a read-only EHR quality/referral API. Use when Codex must prepare duplicate-chart merge readiness packets, referral coordination packets, care transition summaries, ServiceRequest quality reviews, or referral batch audits from prompt IDs, environment_access.md, and answer_template.json.
---

# EHR Governance JSON Packets

## Core Workflow

1. Read the user prompt and the referenced `answer_template.json` before querying data.
2. Read `environment_access.md` for the base URL and allowed endpoints. Use only those endpoints and the supplied files.
3. Extract all concrete IDs from the prompt and payloads: patient IDs, duplicate candidate IDs, referral IDs, batch IDs, provider IDs, and service request IDs.
4. Fetch direct records by ID first, then fetch related patient chart endpoints as needed: conditions, medications, allergies, encounters, immunizations, documents, disclosures, service requests, duplicate candidates, referrals, ICD-10 records, service-code records, and providers.
5. Treat list/search endpoints as broad result sets. Filter client-side by exact `batch_id`, `referral_id`, `candidate_id`, `patient_id`, or provider ID.
6. Build an evidence map before writing JSON. Record which source supplied each ID, status, code validation result, provider contact, active-list key, document, encounter, disclosure, and audit entry.
7. Return JSON only, matching the template's exact top-level keys, field types, enum strings, nullability, and ordering instructions.

## Normalization Rules

- Use exact IDs and enum values from source records and the template.
- Deduplicate set-like arrays, sort alphabetically unless the template gives another order, and preserve specified object ordering such as newest-to-oldest encounters or `sort_by_code`.
- Use active chart endpoints as authoritative for current conditions, medications, and allergies. Include only records with active status unless the template asks for excluded distractors.
- Use `normalized_key` values for clinical-key arrays. Do not invent keys from descriptions.
- Exclude inactive, entered-in-error, stale, unrelated, cancelled, preliminary, or non-matching records when the output asks for active lists, packet evidence, readiness evidence, or final document evidence.
- Prefer structured endpoint fields over narrative notes. Use narrative fields only to classify relevance, missing follow-up, SBAR coverage, laterality mismatch, or care-plan context.
- Do not output explanatory prose, SOP text, confidence notes, or citations outside the JSON object.

## Duplicate Chart Review

- Fetch the duplicate candidate and both patient detail records.
- Use candidate `match_signals` and `conflict_signals` directly, then add demographic match/conflict labels only when the template asks for them.
- Determine merge readiness from the candidate status, patient canonical statuses, `canonical_patient_id`, and merge preview:
  - A populated preferred target/source plus an active target and duplicate source usually supports merge readiness.
  - A candidate marked `needs_review`, null target/source, or conflicts such as different identity fields or opposite laterality should produce a review hold/manual-review disposition.
  - Do not force a merge when conflict signals explain separate clinical identities.
- Compute active condition, medication, and allergy unions from each patient's active list endpoints. Compare these unions with the duplicate preview and report keys added from active endpoints when requested.
- For merge-packet evidence, select final identity-verification and external-continuity documents. Exclude generic chart summaries and unrelated documents unless the template explicitly asks for them.
- Select audit evidence by matching patient IDs, candidate summaries, merge/identity events, or external-import events relevant to the duplicate pair.
- Select provider contact from the relevant specialist/external-continuity service line when requested; include the canonical patient's primary care provider separately when the template includes it.

## Referral Coordination

- Fetch referral detail, patient detail, active conditions/medications/allergies, encounters, documents, receiving provider, and ICD-10 records for referral diagnosis codes.
- Use the referral's diagnosis code as the primary code unless the template explicitly asks to override it. Supporting codes should come from active conditions or relevant encounters that support the referral narrative.
- Validate ICD codes by existence, chapter, expected terms, and laterality requirements from the ICD-10 endpoint.
- For `active_diagnoses`, include active condition records and mark `referral_relevant` by service line, ICD match, narrative terms, encounter support, or medication/care-plan context.
- Select the recent encounter by relevance first and recency second. A newer unrelated encounter should not replace the most recent signed/amended encounter that matches the referral diagnosis, narrative, medications, or care plan.
- For required documents, use document endpoint records for IDs, dates, type, and final status. Use referral `documents_received` as receipt evidence when the template asks only whether a required document was received and no document ID is available.
- Allergy readiness is complete when active allergies have allergen, reaction, severity, status, and source. Empty active allergy lists support `no_known_allergies` only when there are no conflicting records. Incomplete, conflicting, or clarification-only records should set follow-up or blocking fields as the template allows.
- Authorization readiness should combine referral status, authorization status, provider resolution, code validation, allergy readiness, and required-document completeness. Populate blocking issue arrays from actual blockers, not from resolved warning notes.
- Medication highlights should prioritize active medications relevant to the service line and diagnoses, then include other active medications only when the template asks.

## Care Transition Packets

- Fetch patient detail, recipient provider, active clinical lists, encounters, immunizations, disclosures, and documents.
- Output patient and recipient identity fields from their direct endpoints.
- Sort active condition, medication, and allergy keys ascending after deduplication.
- Select handoff encounters by the requested service line and transition purpose. Choose the requested count of the newest relevant encounters and order them newest to oldest.
- Exclude encounters that are stale, outside the relevant window, or unrelated to the transition even if they are recent.
- Select the latest immunization by maximum date.
- Select the disclosure matching the recipient provider or facility and packet purpose. A permitted disclosure is required for send readiness when the template includes disclosure blockers.
- Derive risk flags from active clinical evidence and relevant encounter notes. Emit only allowed risk codes and include matching condition keys, medication keys, and encounter IDs as evidence.
- Readiness is ready only when patient, recipient, active lists, required handoff encounters, latest immunization, and permitted disclosure evidence are present. Use a risk-flag status when non-blocking risks remain.

## ServiceRequest Quality Review

- Fetch the patient's service-request list and filter to the requested ServiceRequest ID.
- Validate service code through the service-code endpoint. A code is valid when it exists, is active, and matches the performer provider's service line.
- Resolve requester and performer providers by ID. Use provider `service_line` for performer service-line fields.
- Validate each reason code through ICD-10 lookup. For each code, include validity, chapter, and whether patient active conditions, encounters, or SBAR text support the code and required laterality.
- Sort reason-code validation objects by code.
- Treat SBAR as complete only when situation, background, assessment, and recommendation are all present and non-empty. Report missing sections exactly with template enum values.
- Pair duplicate-review output with ServiceRequest output when both are requested, but do not let a review-hold duplicate decision invalidate an otherwise valid ServiceRequest unless the template has a blocker field for that relationship.

## Referral Batch Audits

- Fetch referrals and filter to the exact batch ID. Confirm service line and requested date from the filtered rows.
- Compute `record_count`, `unique_patient_count`, urgency counts, queue counts, tier counts, and ready counts from the filtered rows only.
- For service-line code audits, compare each diagnosis code to the ICD-10 directory:
  - `unknown_code`: no ICD-10 record.
  - `out_of_range_chapter`: ICD-10 chapter does not match the template's expected chapter or service-line rule.
  - narrative mismatch: referral narrative lacks any expected term for the code.
  - laterality mismatch: referral narrative names the opposite side from a laterality-specific code.
  - missing laterality: the ICD record requires laterality but the narrative has no side.
- Use the ICD directory's `expected_terms` as the matching vocabulary. Do not infer broad clinical equivalence unless terms or template rules support it.
- Build duplicate groups from same-patient resubmissions in the same batch with duplicate/resubmission signals, same date, and overlapping clinical intent. Include every row in a duplicate group when the template says all duplicate-group rows are blockers.
- Treat same patient referrals with distinct clinical intent as separate clinical reviews, not duplicate groups.
- Flag shared insurance across different patient IDs as an insurance/patient anomaly when demographics or duplicate-review evidence do not support automatic merge.
- Populate follow-up queues from structured fields: missing/pending authorization, required office-note absence, missing imaging, or coordination notes indicating pending imaging.
- Assign action tiers from blocker severity:
  - Tier 1: urgent coding blockers or duplicate-group blockers.
  - Tier 2: routine coding, authorization, or document blockers.
  - Tier 3: administrative document completion without urgent clinical/coding blockers.
- Use the receiving or owning provider ID from the referral as the action-plan owner unless the template specifies another owner source.
- Reconcile summary counts directly against the emitted arrays before finalizing JSON.
