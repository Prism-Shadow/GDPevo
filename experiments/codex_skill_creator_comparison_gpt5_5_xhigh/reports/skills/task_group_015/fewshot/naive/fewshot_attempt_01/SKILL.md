---
name: ehr-quality-packet-solver
description: Solve EHR quality-governance tasks that require normalized JSON from a read-only task API, including duplicate-chart merge readiness, referral coordination, care-transition packets, ServiceRequest quality checks, and referral batch audits. Use when prompts mention EHR/referral/duplicate/care-transition/audit endpoints, `<TASK_ENV_BASE_URL>`, or an `answer_template.json` schema.
---

# EHR Quality Packet Solver

Use this skill to produce schema-conformant JSON for EHR quality tasks backed by a read-only HTTP API.

## Core Workflow

1. Read the prompt and `input/payloads/answer_template.json` before calling the API.
2. Extract every explicit ID, batch ID, service line, provider ID, candidate ID, referral ID, ServiceRequest ID, and patient ID from the prompt and payloads.
3. Use only documented read-only `GET` endpoints at `<TASK_ENV_BASE_URL>`. If a list endpoint has no documented query syntax, fetch the list and filter locally.
4. Fetch detail records for the extracted objects, then fetch related patient active lists, encounters, documents, immunizations, disclosures, providers, audit logs, ICD-10 entries, and service-code entries as required by the template.
5. Populate only the keys requested by the template. Do not include template metadata fields such as descriptions, ordering hints, or schema descriptions in the final answer unless the template explicitly requires them as answer fields.
6. Return exactly one JSON object and no prose. Parse the final JSON before responding.

Suggested endpoint families:

- Patient chart: `/api/patients/{patient_id}`, `/conditions`, `/medications`, `/allergies`, `/encounters`, `/immunizations`, `/documents`, `/service-requests`, `/disclosures`
- Duplicate review: `/api/duplicates/{candidate_id}`, `/api/duplicates/candidates`, `/api/audit-logs`
- Referral work: `/api/referrals`, `/api/referrals/{referral_id}`
- Validation directories: `/api/icd10/{code}`, `/api/icd10`, `/api/service-codes/{code}`, `/api/service-codes`
- Provider contacts: `/api/providers/{provider_id}`, `/api/providers`

## Evidence Rules

- Treat patient active-list endpoints as authoritative for active condition, medication, and allergy keys. Use duplicate or referral previews only as hints; reconcile them against active endpoints.
- Include only active clinical records unless the template asks for excluded, stale, inactive, or distractor records.
- Use stable IDs from API records for evidence fields. Do not invent IDs from narrative text.
- Use final/signed/amended clinical evidence when the task asks for packet readiness. Draft, cancelled, preliminary, unrelated, or stale records are blockers or exclusions depending on the template.
- Use provider directory records for provider names, facilities, service lines, phone, and fax. Do not copy contact details from free text if a provider ID can be resolved.
- Validate ICD-10 and service codes through their directory endpoints. A code can be syntactically valid but still wrong for a service line, chapter, laterality, narrative, or patient evidence.
- When the template provides enum labels, emit the exact matching label from the template; never paraphrase enum values.
- If evidence is absent and the template permits null, use `null`. If a required boolean or status depends on missing evidence, mark the appropriate incomplete, hold, blocked, or manual-review status from the template.

## Sorting And Normalization

- Sort arrays described as sets alphabetically or by the ordering rule in the template.
- Sort diagnosis/service-code validation objects by code when requested.
- Sort referral object arrays by referral ID and duplicate groups/anomalies by group or anomaly ID when requested.
- For encounter handoff packets, keep selected handoff encounters newest-to-oldest unless the template says otherwise.
- Normalize clinical key arrays from `normalized_key` fields, not display text.
- Deduplicate IDs and normalized keys after filtering.
- Derive summary counts from the records actually emitted in the final JSON, plus batch totals from the audited batch evidence.

## Task Patterns

### Duplicate Merge Readiness

Use this pattern when the template asks for `merge`, `merge_decision`, active clinical unions, identity signals, evidence, or packet contact.

1. Fetch the duplicate candidate and both patient details.
2. Determine target/source only from candidate fields, patient canonical/active status, or explicit duplicate-to-target evidence.
3. Emit a merge-ready disposition only when identity match evidence is strong and there are no material conflicts requiring review. Name, DOB, phone, insurance, PCP, sex, external continuity documents, and candidate match signals are match evidence; conflicting given name, DOB, phone, insurance, address, or clinically incompatible laterality can require review.
4. Build active condition, medication, and allergy unions from both patients' active endpoints. Compare these with any duplicate preview and list keys added from active endpoints when the template asks for reconciliation.
5. Select packet documents only when they establish identity, merge review, or external continuity relevant to the duplicate. Exclude routine chart summaries and unrelated patient documents when the template asks for distractors or exclusion policy.
6. Include audit IDs that directly support candidate creation, review, duplicate linkage, or merge-readiness status.
7. Resolve requested specialist and primary-care contacts through the provider directory.

### Referral Coordination

Use this pattern when the template asks for `patient_referral`, `active_diagnoses`, `referral_code_set`, allergy readiness, recent encounter evidence, required documents, receiving provider, authorization readiness, medication highlights, or referral-letter choices.

1. Fetch referral detail first, then patient detail, active chart lists, encounters, documents, provider, and ICD-10 records for all referral and encounter reason codes.
2. Build active diagnoses from active problem-list conditions plus referral-intake or encounter diagnosis codes that are clinically relevant to the referral.
3. Choose the primary code from referral evidence when it matches the narrative, service line, ICD lookup, and patient evidence. Put additional relevant codes in supporting codes.
4. Mark narrative/code validation by comparing ICD lookup terms, chapter, and laterality with the referral narrative and recent encounter assessment.
5. Use active allergy records or referral-form allergy evidence to decide whether allergies are complete, conflicting, absent, or need clarification.
6. Choose the recent encounter that supports the referral reason: signed or amended, recent, relevant diagnosis codes, and a care plan that points to the requested service.
7. Required-document readiness depends on the specific documents named by the template, their status, and whether an office note or authorization is required.
8. Medication highlights should include only active medications relevant to the service-line reason or required letter summary; do not dump the full medication list unless the template asks for it.
9. Letter-choice fields are normalized enum selections. Select the enum whose meaning matches the evidence already emitted elsewhere in the JSON.

### Care Transition Packet

Use this pattern when the template asks for a patient, recipient, active clinical key arrays, handoff encounters, immunization, disclosure, risk flags, and packet readiness.

1. Fetch patient and recipient provider details, then active clinical lists, encounters, immunizations, disclosures, and documents if referenced by the template.
2. Emit active condition, medication, and allergy keys from active endpoints only.
3. Select the service-line-specific handoff encounter window from signed or amended transition notes and recent relevant visits. Exclude stale, unrelated, draft, or outside-window encounters and list their IDs if requested.
4. Use the latest immunization by date.
5. Use the disclosure that is permitted for the recipient provider and transition purpose. A missing, expired, denied, or pending disclosure is a readiness blocker when disclosure is required.
6. Emit only risk flags allowed by the template and back each flag with active condition keys, medication keys, and/or encounter IDs. Allergy-only flags may have empty evidence arrays if the allergy key itself is already emitted in the active allergy list and the template separates allergy evidence from risk evidence.
7. Packet status is ready only when required patient, recipient, active lists, handoff encounters, immunization, and disclosure evidence are present. Risk flags can make the status "ready with risk flags" rather than blocked when no required evidence is missing.

### Duplicate Plus ServiceRequest Quality

Use this pattern when the template combines duplicate review with a ServiceRequest and SBAR coverage.

1. Fetch the duplicate candidate, both patients, the ServiceRequest, requester and performer providers, service-code directory record, ICD-10 records for reason codes, and relevant encounters/conditions.
2. For duplicate review, use candidate status, match signals, and conflict signals. Do not set merge target/source when conflicts require review hold.
3. For ServiceRequest fields, copy status, intent, priority, patient, requester, performer, authored date, occurrence date, service code, and reason codes from the API evidence.
4. Mark service-code validity from the service-code directory. Mark each reason code valid from ICD lookup and `matches_patient_evidence` from active conditions, encounter diagnoses, or narrative evidence.
5. SBAR coverage is complete only when situation, background, assessment, and recommendation are all present in structured or clearly labeled request evidence.

### Referral Batch Audit

Use this pattern when the template asks for batch metadata, invalid/out-of-range codes, laterality/narrative mismatches, duplicate groups, anomalies, follow-up queues, action tiers, and summary counts.

1. Fetch the referral list, filter to the requested batch ID, and fetch detail for each row if needed. Resolve patient, provider, ICD-10, and authorization/document evidence required by the template.
2. Batch totals come from audited rows and distinct patient IDs.
3. Invalid or out-of-range code referrals are rows where ICD lookup is missing or the ICD chapter is outside the chapter expected by the template or service-line audit.
4. Laterality and narrative mismatches come from comparing the referral diagnosis narrative against ICD lookup expected terms. Use missing-laterality when the ICD terms encode laterality but the narrative omits it; use laterality mismatch when left/right disagree; use narrative mismatch when the body site or diagnosis concept disagrees.
5. Duplicate groups are same-patient resubmissions for the same clinical request. When the template says all duplicate-group rows are blockers, assign every row in the duplicate group to the duplicate-blocker tier, including the original.
6. Insurance anomalies are not duplicate groups by themselves. Shared insurance across different patients is an insurance-verification anomaly and should not cause a merge recommendation without duplicate evidence.
7. Follow-up queues come directly from referral authorization status and missing/pending required documents or imaging.
8. Tier assignment is evidence-driven: urgent coding issues and duplicate blockers are immediate; routine coding, authorization, and clinical-document blockers are short-term; purely administrative document completion is administrative. Ready rows with no follow-up should not appear in action tiers.
9. Summary counts must equal the emitted invalid, mismatch, duplicate, anomaly, queue, tier, and ready-row sets.

## Final Checks

- Ensure every required top-level key from the template is present.
- Ensure no train/example IDs or values are reused unless they came from the current task API evidence.
- Ensure every non-constant answer value is backed by fetched evidence or by a deterministic count/sort over fetched evidence.
- Ensure no explanatory text appears before or after the JSON.
