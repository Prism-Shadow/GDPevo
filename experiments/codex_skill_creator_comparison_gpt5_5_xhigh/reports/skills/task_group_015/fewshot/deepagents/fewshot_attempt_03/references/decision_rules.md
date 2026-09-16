# Decision Rules

Use these rules for read-only EHR quality-governance packet tasks. They are reusable heuristics; always let the task prompt and `answer_template.json` override them.

## Evidence Collection

- Duplicate candidates: fetch `/api/duplicates/{candidate_id}`, then fetch every patient in `patient_ids`.
- Patient chart evidence: fetch `/api/patients/{patient_id}` and the patient-scoped `conditions`, `medications`, `allergies`, `encounters`, `immunizations`, `documents`, `disclosures`, and `service-requests` endpoints as needed.
- Referrals: fetch `/api/referrals/{referral_id}` for specific referrals. For batch audits, fetch `/api/referrals` and filter locally to exact `batch_id`; do not assume server query parameters narrow results.
- ServiceRequests: fetch from `/api/patients/{patient_id}/service-requests` and select the exact `service_request_id`.
- Directories: fetch `/api/providers/{provider_id}`, `/api/icd10/{code}`, and `/api/service-codes/{code}` for validation rather than inferring names, chapters, service lines, or contact data.
- Audit logs: when used, filter `/api/audit-logs` by involved patient IDs, candidate IDs, event summaries, and requested evidence purpose.

## General Normalization

- Active clinical lists use records whose `status` is `active`. Emit `normalized_key` values, not display names, when the template asks for keys.
- Patient-scoped active endpoints are authoritative over previews embedded in duplicate candidates or referral summaries. If a template asks for keys added from active endpoints, compute `active_endpoint_union - preview_keys`.
- Use exact provider directory fields for provider output. Use embedded primary-care provider data only when the template asks for it and direct lookup is not needed.
- Use final/signed/current evidence for primary packet fields. Treat inactive clinical records, stale encounters, cancelled/preliminary documents, unrelated chart summaries, and unrelated audit rows as exclusions or distractors when the template requests them.
- Compare text case-insensitively after trimming whitespace and normalizing obvious punctuation. Do not invent codes or IDs absent from the environment.

## Duplicate Review and Merge Readiness

- A candidate is merge-ready only when the candidate provides a preferred target and source, the target patient is an active canonical chart, the source is a duplicate or otherwise points to the target, and identity match signals outweigh only minor conflicts.
- Use manual review or review hold when the candidate has no preferred target/source, status indicates review is needed, or conflicts include substantive identity or clinical laterality conflicts.
- Do not emit merge target/source IDs for a hold unless the template explicitly asks for proposed values; use `null` where allowed.
- Match signals come from the candidate plus demographic comparisons such as DOB, phone, insurance, sex, PCP, and equivalent normalized names or addresses.
- Conflict signals include direct mismatches and business-normalized variants. Name nicknames and address abbreviations can be noted as conflicts while still allowing merge if canonical status and identity evidence are strong.
- Evidence documents for merge packets should be identity or external-continuity documents. Exclude generic chart summaries unless the template says otherwise.

## Referral Coordination Packets

- Reconcile referral detail with patient chart evidence. The referral gives requested service line, receiving provider, primary diagnosis, authorization status, urgency, and received-document summary; the patient chart supplies active diagnoses, medications, allergies, encounters, and document IDs.
- Validate every diagnosis code with `/api/icd10/{code}`. Prefer active patient conditions and referral-intake conditions that match the referral narrative as referral-relevant. Supporting codes should be clinically tied to the referral narrative or recent encounter, not every active diagnosis.
- Allergy readiness is complete when active allergy records supply the allergen, reaction, severity, status, and source needed by the template. Empty allergy lists imply no known allergies only if the evidence and template support that interpretation.
- Choose recent encounter evidence by service-line relevance, signed status, diagnosis codes, care-plan text, and medication mentions. Do not pick the latest encounter if it is unrelated.
- Required documents must match requested types and acceptable status, usually `final`; missing, preliminary, cancelled, or unrelated document types belong in missing or excluded fields. Combine referral `documents_received` summaries with patient document records: booleans can be satisfied by the referral summary, while document IDs, dates, and statuses require a matching document record.
- Medication highlights should include active medications relevant to the referral service line or diagnosis. Preserve dose, route, frequency, status, and normalized reason labels from evidence.
- Overall readiness is blocked by missing authorization, missing required documents, provider resolution failure, invalid primary diagnosis code, or clinical mismatch when the template defines those blockers.

## Care Transition Packets

- Emit patient identity from `/api/patients/{patient_id}` and recipient identity from `/api/providers/{provider_id}`.
- Select handoff encounters by relevance to the transition service line, requested window/count, diagnosis match, care-plan text, and acceptable signed status. Sort selected encounters newest to oldest; sort excluded encounter IDs as directed.
- Use the latest immunization by date unless the template requests a vaccine-specific selection.
- Select the disclosure matching the recipient provider or facility and packet purpose. A non-permitted or missing disclosure is a readiness blocker when disclosure is required.
- Derive risk flags from active conditions, active medications, active allergies, and encounter notes. If the risk evidence schema lacks allergy fields, emit empty condition/medication/encounter arrays for allergy-only flags unless another evidence source supports them. Risk flags usually do not block sending if all required packet evidence is present; use the template's non-blocking risk-flag readiness status when available.

## ServiceRequest Quality Validation

- Find the exact ServiceRequest in the patient-scoped endpoint. Validate service code activity and service line via `/api/service-codes/{code}`.
- Validate requester and performer through the provider directory. Performer service line should match the requested service line or service code.
- Validate each reason code with `/api/icd10/{code}` and mark whether it matches active patient conditions, encounter diagnoses, documents, or narrative evidence.
- SBAR coverage is complete only when situation, background, assessment, and recommendation are present and nonempty.
- If the task asks for a quality-normalized request state, a raw draft can be emitted as active when all activation-quality checks pass. If the template clearly asks for raw source status, preserve the raw value.

## Referral Batch Audits

- Filter the exact batch before computing counts. `record_count` is referral rows in the batch; `unique_patient_count` is distinct patient IDs in those rows.
- Invalid or out-of-range codes are codes missing from ICD lookup or whose ICD chapter does not match the expected chapter from the template/service line.
- Laterality and narrative mismatch checks use ICD `expected_terms` and `requires_laterality`:
  - `laterality_mismatch`: the code expects one side and the narrative names the opposite side.
  - `missing_laterality`: the code requires a side and the narrative has no side while otherwise describing the same broad problem.
  - `narrative_mismatch`: the narrative does not describe the expected condition family or expected terms.
- Detect duplicate referral groups by same patient within the same batch/service line where coordination notes or IDs indicate resubmission of the same clinical request. When the template's policy says all duplicate rows are blockers, tier every row in that group as a duplicate blocker.
- Detect insurance anomalies by shared insurance IDs across different patient IDs in the audited scope. Do not convert those into duplicate merges without duplicate-candidate evidence.
- Follow-up queues usually map directly from referral fields: missing authorization, pending authorization, missing office-note records, and service-line-specific imaging requirements. Determine document requirements from the template, service line, diagnosis family, and `documents_received`.
- Tiering: Tier 1 is for urgent coding issues or duplicate blockers. Tier 2 is for routine coding, authorization, or clinical-document blockers. Tier 3 is for administrative document completion when coding/authorization/duplicate blockers are absent.
- Summary counts must equal the final emitted arrays and batch rows: urgent/routine rows, invalid rows, mismatch rows, duplicate groups, anomalies, each follow-up queue length, each tier length, and rows with no follow-up.

## Final Checks

- Walk the template top to bottom and fill every required key.
- Use `null` only where the schema permits it.
- Recompute set unions, excluded lists, and summary counts after all filtering.
- Parse the final object with `jq` or Python JSON before returning.
