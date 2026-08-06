---
name: ehr-quality-packets
description: Build normalized JSON packets and audits from a read-only GDPEVO EHR quality/referral API. Use when Codex must prepare duplicate-chart merge readiness packets, referral coordination packets, care-transition handoff summaries, ServiceRequest quality reviews, ICD/referral batch audits, or provider/patient evidence reconciliation using TASK_ENV_BASE_URL and an answer_template.json schema.
---

# EHR Quality Packets

## Core Workflow

1. Read the task prompt, every file in `input/payloads/`, and especially `input/payloads/answer_template.json`.
2. Read `environment_access.md` for the base URL and allowed endpoints. Use only those endpoints for network access.
3. Extract all IDs and scope constraints from the prompt and payloads: patient IDs, referral IDs, duplicate candidate IDs, ServiceRequest IDs, batch IDs, provider IDs, service line, requested recipient, and required output sections.
4. Fetch detail records, not just list records, for every in-scope object:
   - `/api/patients/{patient_id}` plus relevant patient child endpoints.
   - `/api/referrals/{referral_id}` or `/api/referrals` filtered by `batch_id`.
   - `/api/duplicates/{candidate_id}` for duplicate reviews.
   - `/api/providers/{provider_id}` for requester, performer, recipient, PCP, and receiving provider records.
   - `/api/icd10/{code}` or `/api/icd10` for diagnosis validation and expected terms.
   - `/api/service-codes/{code}` for ServiceRequest service-code validation.
   - `/api/audit-logs` when merge or identity evidence is requested.
5. Build an evidence table before writing output. Keep raw API values separate from normalized output choices; some schemas ask for readiness or quality-normalized values rather than verbatim source values.
6. Emit only one JSON object conforming to the answer template. Do not add prose, comments, Markdown, or fields that the template does not request.

## Normalization Rules

- Treat arrays described as sets as deduplicated sets. Sort strings alphabetically unless the template gives a different ordering.
- Preserve template-specific object ordering rules, such as newest-to-oldest encounter lists or arrays sorted by `referral_id`, `group_id`, risk flag, or code.
- Use active clinical list records only when the schema asks for current conditions, medications, or allergies. Filter out inactive, entered-in-error, cancelled, stale, unrelated, or distractor records unless an exclusion/evidence section asks for them.
- Prefer stable IDs and normalized keys over narrative summaries.
- Use exact enum strings from the current `answer_template.json`. When the template offers choice fields, select the enum whose label matches the evidence; do not invent synonyms.
- Use `null` only where the template allows it. Otherwise use empty arrays, booleans, or `"unknown"`-style enum values if provided by the template.
- Validate date strings as `YYYY-MM-DD`.

## Duplicate Merge Packets

For duplicate candidate tasks, fetch the duplicate candidate, both patient details, active conditions/medications/allergies for each patient, relevant documents, audit logs, and provider records.

- Determine target/source from candidate `merge_preview.preferred_target_patient_id` and `source_patient_id`, then verify against patient `canonical_status` and `canonical_patient_id`.
- Mark merge-ready only when the candidate is open/confirmed, the target is the active canonical record, the source is a duplicate or otherwise points to that target, and no blocking identity conflicts remain.
- If target/source are absent or identity conflicts are clinically meaningful, hold for manual review and leave merge target/source null when the schema allows.
- Active list unions must come from the patient active-list endpoints, not only from the duplicate preview. If the schema asks for reconciliation, report keys present in endpoint-derived unions but missing from the preview.
- Use duplicate candidate `match_signals` and `conflict_signals` directly, sorted as sets. Derive demographic matches/conflicts from patient details, including DOB, phone, insurance, sex, PCP, address normalization, name variants, suffixes, or given-name differences.
- Select merge evidence documents that support identity or external continuity and are final. Exclude generic chart exports or unrelated summaries when the task asks for identity/continuity packet evidence.
- Select audit logs tied to the in-scope patients and relevant identity review/import/merge events; exclude logs for unrelated merges.
- Populate provider contact from the relevant specialist/receiving external-continuity provider and PCP/provider directory details.

## Referral Coordination Packets

For single-referral coordination tasks, fetch referral detail, patient detail, active conditions/medications/allergies, encounters, documents, ICD details for referral and encounter codes, and the receiving provider.

- Patient/referral identity fields come from referral detail and patient detail.
- Active diagnoses usually combine active condition records with referral-intake or encounter diagnosis codes that are directly relevant to the referral. Mark `referral_relevant` true only for the primary referral problem or supporting symptoms/findings.
- Validate referral diagnosis code with ICD metadata:
  - Invalid/missing code: use the invalid-code enum.
  - Valid but wrong service-line chapter: use the wrong-chapter enum when present.
  - Valid chapter but narrative does not match expected terms/laterality: use the narrative-mismatch enum.
  - Valid code and narrative match: use the valid-match enum.
- Evaluate narrative matching case-insensitively against ICD `expected_terms`. Treat common clinical abbreviations as equivalent when medically clear, and handle laterality separately from the underlying body-site/problem match.
- Choose recent encounter evidence by referral relevance, signed/amended status, diagnosis-code overlap, care-plan text, medications mentioned, and date. Do not choose an unrelated latest visit over a clearly referral-specific encounter.
- Required document evidence comes from both referral `documents_received` and patient document records. Use document records for IDs, dates, type, and final/preliminary status.
- Allergy readiness is complete when active allergy records include enough allergen/reaction/severity/status detail and no conflict. Use follow-up states only for missing, incomplete, or conflicting records; do not let a stale coordination note override complete active allergy data.
- Authorization readiness is ready only when authorization, provider, code validation, required documents, and allergy readiness have no blockers. Fill blocking issue arrays from the failed checks.
- Medication highlights should be active medications relevant to the referral service line and diagnosis. Prefer directly relevant therapy first; include other active medications only if the template or clinical context calls for them.
- For referral-letter choice fields, map evidence to the most specific enum labels in the template.

## Care Transition Packets

For handoff or transition summaries, fetch patient detail, recipient provider, active clinical lists, encounters, immunizations, disclosures, and relevant documents if requested.

- Patient and recipient sections come directly from patient and provider detail.
- Active condition, medication, and allergy key arrays come from active endpoint records, deduplicated and sorted.
- Select handoff encounters by the requested specialty/transition purpose, diagnoses, medications mentioned, care-plan notes, signed status, and recency. Use the template’s required count and ordering. Exclude reviewed encounters that are stale, outside the handoff window, unsigned/draft if signed alternatives exist, or unrelated to the transition.
- Latest immunization is the newest immunization by date unless the template narrows vaccine type.
- Disclosure must match the patient, recipient provider, purpose, and permitted/current status. If missing or not permitted, mark the corresponding readiness blocker.
- Risk flags come only from the template’s allowed values. Derive them from active conditions, medications, allergies, and encounter notes. If an allergy-only risk flag has no allergy evidence slot in the template, emit empty evidence arrays for that evidence object.
- Packet readiness is `not_ready` when required patient/recipient/list/encounter/immunization/disclosure data is missing or blocked. Use `ready_with_risk_flags` when all required packet elements are present but risk flags must travel with the packet.

## ServiceRequest Quality Reviews

For ServiceRequest review tasks, fetch the patient’s ServiceRequests, select the requested ID, and validate it with service-code, provider, ICD, duplicate-candidate, and patient evidence.

- Service-code validity requires an active service code whose service line matches the performer provider and requested service.
- Provider fields should come from the ServiceRequest requester/performer IDs and provider directory detail.
- Validate each reason code against ICD. Include ICD chapter and whether it matches patient evidence from active conditions, encounters, documents, or relevant clinical narrative.
- SBAR coverage is complete only when situation, background, assessment, and recommendation are all non-empty.
- If the schema asks for normalized readiness/status rather than raw draft state, promote the output status only when required quality checks are complete; otherwise preserve or report the blocked/draft state according to the template.
- Combine duplicate-review and ServiceRequest conclusions without cross-contaminating them: a duplicate hold can coexist with a clinically valid ServiceRequest.

## Referral Batch Audits

For batch audit tasks, fetch all referrals and filter by the requested `batch_id`. Then fetch ICD, patient, provider, and any needed detail records for the filtered rows.

- Batch counts:
  - `record_count` is filtered referral row count.
  - `unique_patient_count` is distinct patient count.
  - Urgent/routine counts come from referral `urgency`.
- Invalid or out-of-range code referrals include unknown ICD codes and codes whose ICD chapter does not match the expected chapter for the audited service line. Use the template’s expected chapter if supplied.
- Laterality/narrative mismatches:
  - Compare referral narrative to ICD expected terms case-insensitively.
  - If the code requires laterality and the narrative contains the opposite side, include a laterality mismatch.
  - If the code requires laterality and the narrative omits side while matching the general condition, include missing laterality.
  - Include narrative mismatch when the underlying body site/problem does not match expected terms after accounting for laterality.
- Duplicate groups are same-patient resubmissions within the batch, especially rows flagged by duplicate language, duplicate IDs, or repeated same-patient same-service clinical submissions. Include all rows in the duplicate group, not only the later duplicate row.
- Insurance/patient anomalies are shared insurance IDs across different patients within the batch. Keep these separate from same-patient duplicate groups.
- Follow-up queues:
  - Authorization missing/pending from referral authorization status.
  - Records request for missing required office-note or equivalent clinical documentation.
  - Imaging follow-up for missing required imaging or coordination notes indicating imaging is pending.
- Tiering:
  - Tier 1: urgent referrals and all duplicate-blocker group rows.
  - Tier 2: nonurgent referrals with coding, authorization, clinical narrative, laterality, or non-administrative document blockers.
  - Tier 3: administrative-only document completion when no clinical/coding/auth/duplicate blocker is present.
  - Owner/provider assignment should come from each referral’s receiving provider unless the template states another owner rule.
- Summary counts must equal the lengths of the emitted arrays/queues plus urgency and readiness counts from the audited referral rows.

## Final Self-Check

Before responding:

1. Re-open the answer template and confirm every required top-level key is present.
2. Confirm no task-specific fields from training examples have been copied into the output.
3. Confirm every ID, enum, boolean, count, and normalized key is supported by fetched evidence.
4. Confirm all set-like arrays are deduplicated and sorted, and all ordered arrays follow the template rule.
5. Return JSON only.
