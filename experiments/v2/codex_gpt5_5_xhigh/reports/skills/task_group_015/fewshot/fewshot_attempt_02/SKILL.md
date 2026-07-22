---
name: ehr-quality-packets
description: Use when producing normalized JSON packets or audits from a read-only EHR quality-governance API, including duplicate-chart merge readiness, referral coordination, care-transition handoffs, ServiceRequest quality checks, ICD-10/service-code validation, active-list reconciliation, document/audit evidence selection, provider contacts, follow-up queues, action tiers, and summary counts.
---

# EHR Quality Packets

## Core Workflow

1. Read the user prompt, every file under `input/payloads/`, and especially `answer_template.json`.
2. Read `environment_access.md` for the task environment base URL and allowed endpoints. Use only that base URL for network access; do not use outside medical knowledge or other network sources.
3. Extract all requested IDs and filters from the prompt and payloads: patient IDs, duplicate candidate IDs, referral IDs, batch IDs, ServiceRequest IDs, provider IDs, service lines, and requested output sections.
4. Fetch evidence from the API. Prefer object-detail endpoints when an ID is known. If a search/list endpoint returns more than the requested scope, filter locally by the requested ID, `batch_id`, patient, service line, or date.
5. Build the response directly from the template shape. Preserve required top-level keys, required constants, enums, nullability, and date formats. Do not include prose outside the JSON object.
6. Sort arrays with set semantics alphabetically or by the ordering rule in the template. Deduplicate normalized keys and IDs before output.

Useful endpoint families:

- Duplicate review: `/api/duplicates/candidates`, `/api/duplicates/{candidate_id}`, patient detail, active conditions/medications/allergies, documents, and `/api/audit-logs`.
- Referral detail or batch audit: `/api/referrals`, `/api/referrals/{referral_id}`, patient detail, ICD-10 lookup, provider directory, and active chart endpoints when clinical evidence is needed.
- Care transition: patient detail, active conditions/medications/allergies, encounters, immunizations, disclosures, documents, and recipient provider detail.
- ServiceRequest quality: `/api/patients/{patient_id}/service-requests`, `/api/service-codes/{code}`, `/api/icd10/{code}`, provider detail, active conditions, and encounters.

## Evidence Rules

- Active clinical lists are authoritative from the patient-scoped endpoints. Include only records whose status is `active` unless the template asks for excluded stale or inactive distractors.
- Use `normalized_key` for condition, medication, and allergy key sets. Do not infer a key from display text if the endpoint supplies `normalized_key`.
- For duplicate previews, reconcile preview keys against the full active-list endpoint union for both patients. Report active endpoint keys missing from the preview when the template asks for additions.
- Use final identity, consent, external-continuity, imaging, office-note, authorization, or transition documents when the requested packet needs evidence. Exclude unrelated chart summaries and stale/unrelated documents when the template asks for excluded evidence.
- Use audit logs only when the event, patient ID, and summary are relevant to the requested duplicate, import, disclosure, or identity-review packet.
- Provider contact fields must come from patient embedded PCP records or `/api/providers/{provider_id}`; do not synthesize phone or fax values.

## Duplicate Merge Logic

- A merge-ready case needs a live duplicate candidate, a non-null preferred target/source, patient records that agree with that direction, and no material identity conflicts.
- Choose the canonical target from the candidate preview when present, then confirm with patient `canonical_status` and `canonical_patient_id`.
- Treat exact DOB, insurance, phone, normalized address, same PCP, same sex, and name variants as match signals when supported by the candidate or demographics.
- Treat different DOB, phone, insurance, address, materially different given names, and opposite-laterality active problems as review-blocking conflicts when present.
- If the candidate status is review/needs-review, target/source is null, or conflicts affect identity or laterality, hold for manual review and set merge target/source to null if the template requires that.
- Populate disposition fields using the template’s allowed enum vocabulary. If there are parallel legacy and normalized disposition sections, keep them consistent.

## Referral Coordination

- For a single referral, fetch the referral detail, patient detail, active clinical lists, encounters, documents, receiving provider, and ICD-10 record for the referral diagnosis code.
- The referral diagnosis code is usually the primary code. Supporting codes come from active conditions or the selected encounter when they directly support the referral narrative or service line.
- Validate ICD-10 codes by lookup. Compare the returned chapter and expected terms to the referral service line and narrative. Mark invalid, wrong-chapter, laterality, missing-laterality, and narrative mismatches only when supported by the lookup and referral text.
- Select the recent encounter by referral relevance over raw recency: match care-plan notes, diagnosis codes, medications mentioned, service line, and signed/amended status. Ignore newer unrelated visits.
- Required document evidence comes from both referral `documents_received` and patient document records. Confirm document type and final status where a document object is needed.
- Allergy readiness is complete when active allergy details include allergen, reaction, severity, status, and source. Use the template’s no-known, incomplete, or conflicting allergy enums when records are empty, ambiguous, or contradictory.
- Medication highlights should be active medications relevant to the service line and referral narrative first, with dose/route/frequency copied from the medication endpoint.
- Readiness is blocked by missing authorization, pending/denied authorization, missing required documents, incomplete allergy details, provider resolution failure, invalid diagnosis codes, or clinical mismatch, according to the template’s allowed issue codes.

## Care Transition Packets

- Emit patient identity from the patient detail endpoint and recipient identity from the provider endpoint.
- Active condition, medication, and allergy key arrays are sorted unique active `normalized_key` values.
- Select handoff encounters by the service-line transition rule in the prompt/template: relevant care-plan text, matching diagnoses, transition/office-visit type, signed or amended status when allowed, and the requested recency window. Order selected encounters newest to oldest.
- Put reviewed but stale, outside-window, or unrelated encounters in the template’s excluded list when requested.
- Latest immunization is the immunization with the newest date unless the template names a vaccine-specific rule.
- Disclosure must match the patient and recipient provider or facility, and readiness requires a permitted disclosure when the template includes disclosure gating.
- Risk flags are derived from active conditions, medications, allergies, and handoff note text. Add evidence objects only for emitted flags, using sorted condition keys, medication keys, and encounter IDs.
- Readiness is `ready_with_risk_flags` when all required packet components are present and permitted but non-blocking clinical risks need communication.

## ServiceRequest Quality

- Fetch all patient ServiceRequests and filter to the requested ID. Validate the requested service code with `/api/service-codes/{code}` and each reason code with `/api/icd10/{code}`.
- `service_code_valid` means the code exists, is active, and matches the requested performer service line.
- `matches_patient_evidence` for a reason code is true when the code appears in an active condition, relevant encounter diagnosis, supporting document, or other prompt-requested evidence.
- SBAR is complete only when situation, background, assessment, and recommendation are all present and non-empty.
- When a task asks for a quality-governance normalized state for a draft order, classify an otherwise complete, valid draft consult as ready/active if the template’s expected status field represents the actionable order state. If the template asks for raw source status, preserve the endpoint value.

## Batch Referral Audits

- Fetch referrals, then filter locally to the requested `batch_id` and service line. Compute counts from the filtered rows, not the unfiltered endpoint response.
- Validate every diagnosis code with the ICD-10 directory. For service-line audits, compare the ICD chapter to the expected chapter implied by the template or service line.
- Laterality/narrative mismatch checks use the ICD `expected_terms` and `requires_laterality` fields:
  - `narrative_mismatch`: none of the expected terms appear in the referral narrative.
  - `laterality_mismatch`: the code expects one side and the narrative names the opposite side.
  - `missing_laterality`: laterality is required and the narrative lacks a side.
- Duplicate groups are same-patient resubmissions within the requested batch/service scope. Include all group rows if the template’s duplicate policy tiers all duplicate rows as blockers.
- Insurance anomalies are shared insurance IDs across different patients; treat them as verification issues, not proof of merge, unless the duplicate-candidate endpoint independently supports a merge.
- Follow-up queues are sorted referral IDs derived from status fields, authorization status, documents received, coordination notes, and service-specific required records or imaging.
- Tier 1 is for urgent coding problems or duplicate blockers. Tier 2 is for routine coding, authorization, clinical, or document blockers. Tier 3 is for administrative document completion without clinical/coding urgency. Use receiving or owner provider IDs from the referral/provider evidence.
- Summary counts must exactly match the emitted arrays and tier lists.

## Output Discipline

- Return JSON only. Do not include markdown, comments, citations, or procedural notes.
- Use `null` only where the template permits it; use empty arrays for absent set-valued evidence.
- Keep duplicate fields synchronized when the template contains overlapping legacy and normalized sections.
- Before finalizing, mentally validate the object against the template: required keys present, enums exact, dates `YYYY-MM-DD`, booleans booleans, counts consistent, and array ordering stable.
