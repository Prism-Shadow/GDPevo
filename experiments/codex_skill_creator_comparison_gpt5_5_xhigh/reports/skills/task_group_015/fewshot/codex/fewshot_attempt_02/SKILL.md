---
name: ehr-quality-packets
description: Build normalized JSON packets and audits from a read-only EHR quality environment. Use when a task provides TASK_ENV_BASE_URL or EHR API endpoints and asks for duplicate-review, referral coordination, care-transition, ServiceRequest validation, or referral-batch audit JSON conforming to input/payloads/answer_template.json.
---

# EHR Quality Packets

## Core Workflow

1. Read the user prompt and `input/payloads/answer_template.json` before querying data. Treat the template as the authoritative output contract.
2. Extract identifiers from the prompt: patient IDs, referral IDs, duplicate-candidate IDs, ServiceRequest IDs, provider IDs, batch IDs, service lines, and requested packet type.
3. Query the live EHR environment at `<TASK_ENV_BASE_URL>` for source evidence. Do not answer from memory or from prior examples.
4. Build the answer by replacing every template placeholder with evidence-derived values. Preserve required top-level keys and field types exactly.
5. Return JSON only. Do not include prose, markdown fences, notes, or fields that are not present in the template unless the prompt explicitly asks for them.

Use `scripts/ehr_fetch.py` as an optional evidence collector:

```bash
python skill/scripts/ehr_fetch.py --base-url "$TASK_ENV_BASE_URL" \
  --patient PATIENT_ID --referral REFERRAL_ID --candidate CANDIDATE_ID \
  --batch BATCH_ID --include-directories
```

The script only gathers endpoint evidence; it does not decide the answer.

## Endpoint Checklist

Use only endpoint families exposed by the task environment:

- Patients: `/api/patients`, `/api/patients/{patient_id}`
- Active lists: `/conditions`, `/medications`, `/allergies`
- Evidence: `/encounters`, `/documents`, `/immunizations`, `/disclosures`, `/service-requests`
- Workflow objects: `/api/duplicates/candidates`, `/api/duplicates/{candidate_id}`, `/api/referrals`, `/api/referrals/{referral_id}`
- Directories: `/api/providers`, `/api/providers/{provider_id}`, `/api/icd10`, `/api/icd10/{code}`, `/api/service-codes`, `/api/service-codes/{code}`
- Audits: `/api/audit-logs`

For a single patient packet, fetch the patient detail, active lists, encounters, documents, and any task-specific evidence endpoints. For a duplicate packet, fetch both patient records and both patients' active lists/documents. For a referral, fetch the referral, patient chart, receiving provider, ICD-10 record, relevant encounters, medications, allergies, and required documents. For a batch audit, fetch all referrals and filter by `batch_id`, then join ICD-10, patient, and provider data as needed.

## Normalization Rules

- Use `status == "active"` for active conditions, medications, and allergies. Exclude inactive, entered-in-error, stale, and unrelated records unless the template asks for excluded distractors.
- Use `normalized_key` for condition, medication, and allergy key arrays. Deduplicate keys and sort alphabetically unless the template specifies a different ordering.
- Keep stable IDs from source records: `patient_id`, `provider_id`, `referral_id`, `candidate_id`, `service_request_id`, `document_id`, `audit_id`, `encounter_id`, `immunization_id`, and `disclosure_id`.
- Compare and emit dates as `YYYY-MM-DD`. For latest evidence, sort by date descending.
- For set-semantics arrays, sort strings ascending for stable output. For object arrays, follow the template ordering rule; otherwise sort by the primary stable ID.
- Use booleans and `null` as JSON values, not strings.
- Prefer endpoint evidence over derived narrative. Use narrative fields only to classify match, mismatch, readiness, and tiering values requested by the template.

## Duplicate Review And Merge Packets

Evidence to fetch:

- Duplicate candidate detail and candidate list.
- Patient details for every candidate patient.
- Conditions, medications, allergies, and documents for each candidate patient.
- Audit logs filtered to the candidate patients and identity/merge/import events.
- Provider records for the primary care provider and any specialist mentioned by relevant continuity documents.

Decision rules:

- Use the candidate's `merge_preview.preferred_target_patient_id` and `source_patient_id` only after verifying patient details. A merge-ready target should be an active canonical record. A merge-ready source should be a duplicate record or explicitly point back to the target through `canonical_patient_id`.
- Emit a merge-ready disposition only when the candidate is open/confirmed, target and source are identified, strong identity signals are present, and conflicts are benign or reviewable. Hold for review when target/source are null, the candidate status requires review, or material conflicts exist such as different phones, different given names, opposite laterality problems, or contradictory demographics.
- Build active clinical unions from active patient endpoints, not from `merge_preview` alone. Use preview keys only to identify which active endpoint keys were omitted from the preview.
- Copy candidate `match_signals` and `conflict_signals` as normalized labels, sorted if the template treats them as sets.
- Derive demographic matches by comparing patient detail fields such as DOB, insurance, phone, sex, and primary care provider. Treat name variants and address abbreviations as conflicts or match aids according to candidate signals and normalized comparison.
- Select packet documents that are final and relevant to identity verification or external continuity. Exclude generic chart summaries unless the template explicitly asks for them.
- Select audit logs whose patient IDs and event summaries relate to the duplicate review, identity verification, merge state, or external import. Exclude unrelated historical merge logs.

## Referral Coordination Packets

Evidence to fetch:

- Referral detail by ID and, for batches, referral rows filtered by `batch_id`.
- Patient detail, active conditions, medications, allergies, encounters, and documents.
- Receiving provider detail.
- ICD-10 detail for each diagnosis or reason code.

Single-referral rules:

- Build patient/referral identity fields directly from the referral and patient endpoints.
- Include active diagnoses from active conditions. Mark `referral_relevant` true when the code is the referral diagnosis, a referral-intake/supporting diagnosis, a diagnosis in the selected encounter, or clearly tied to the service-line narrative.
- Validate ICD-10 by joining `/api/icd10/{code}`. Unknown codes are invalid. For service-line-specific reviews, mark a code out of range when its chapter does not match the expected service-line chapter in the template or prompt.
- Determine narrative match by checking whether the referral narrative contains an expected term from the ICD record. Normalize case and punctuation. If `requires_laterality` is true, also verify the expected side.
- Treat active allergy readiness as complete when active allergy records include allergen, reaction, severity, status, and source. Hold for clarification when required allergy detail is missing or conflicting.
- Use patient documents and referral `documents_received` together. A document type can be received from the referral row, while IDs/status/dates come from patient documents when available.
- Select the recent encounter whose diagnoses and care-plan notes best match the referral purpose, not merely the newest unrelated visit.
- Highlight active medications relevant to the service line, diagnosis, or selected encounter. Preserve dose, route, frequency, status, and use the closest allowed `highlight_reason`.
- Compute readiness from authorization status, referral status, provider resolution, document completeness, allergy readiness, and diagnosis validation.
- For template fields that are enum "choice" values, choose the most specific allowed option whose evidence conditions are satisfied. Use fallback options such as `other` or unresolved values only when no specific option matches.

## Care Transition Packets

Evidence to fetch:

- Patient detail and recipient provider detail.
- Active conditions, medications, allergies.
- Encounters, immunizations, disclosures, and documents.

Selection rules:

- Emit active key arrays from active endpoint records only.
- Select the requested number of handoff encounters by relevance to the transition service line and handoff window. Favor signed or amended encounters with matching diagnoses, care-transition types, perioperative/handoff notes, and medications mentioned. Exclude stale, unrelated, or distractor encounters and list their IDs when the template asks.
- Sort selected handoff encounters newest to oldest unless the template states otherwise.
- Choose the latest immunization by date.
- Use the disclosure whose recipient provider, purpose, and status match the packet. A permitted disclosure supports readiness; missing, expired, denied, or wrong-recipient disclosure blocks readiness when the template includes that blocker.
- Derive risk flags from active conditions, active medications, active allergies, and selected/relevant encounter notes. Emit only risk flags allowed by the template. For each flag, provide evidence arrays sorted as requested.
- Mark a transition packet ready when patient, recipient, active lists, required encounters, immunization, and permitted disclosure evidence are present. Use a risk-aware ready status when the packet is sendable but risk flags must travel with it.

## ServiceRequest Quality Packets

Evidence to fetch:

- Duplicate candidate and patient details if the prompt includes duplicate review.
- Patient ServiceRequests from `/api/patients/{patient_id}/service-requests`, then filter by `service_request_id`.
- Service-code directory entry and performer/requester provider records.
- ICD-10 details for every ServiceRequest reason code.
- Active patient conditions and encounters to verify that reason codes match patient evidence.

Rules:

- Validate duplicate review independently from the ServiceRequest. A duplicate hold does not automatically invalidate a ServiceRequest for the primary patient.
- A service code is valid when the directory entry exists, is active, and its service line matches the intended performer/service line.
- Validate each reason code with ICD-10. Set `matches_patient_evidence` true when the code appears in active conditions, selected encounters, documents, or directly matching clinical narrative.
- Sort reason-code validation objects by code when the template asks.
- SBAR coverage is complete only when situation, background, assessment, and recommendation are all present and non-empty.
- Preserve raw ServiceRequest administrative fields unless the prompt/template asks for a post-validation normalized status. For draft-quality reviews, a complete, valid order may be classified as ready/active according to the template's requested field semantics.

## Referral Batch Audits

Evidence to fetch:

- All referrals, filtered to the exact `batch_id`.
- ICD-10 directory entries for all diagnosis codes in the batch.
- Patient details for duplicate and insurance anomaly checks.
- Provider directory entries for action-plan ownership.

Audit rules:

- Batch counts come from filtered referral rows. `unique_patient_count` is the count of distinct patient IDs.
- For orthopedics audits, the expected ICD chapter is usually Musculoskeletal unless the template/prompt says otherwise. Injury, respiratory, circulatory, neoplasm, symptom, or unknown chapters are out of range for an orthopedics-only diagnosis-code audit even if the narrative seems clinically adjacent.
- Laterality and narrative mismatches are separate:
  - `laterality_mismatch`: the ICD expected side is left/right but the narrative states the opposite side.
  - `missing_laterality`: the ICD requires laterality and the narrative is otherwise compatible but omits the side.
  - `narrative_mismatch`: the narrative does not express an expected ICD term or expresses a different condition/body-site concept.
- Use ICD `expected_terms` as the canonical expected terms array in mismatch outputs when the template asks for it.
- Detect duplicate referral groups from same-patient resubmission evidence: same patient within the batch plus duplicate/resubmission cues in IDs or coordination notes, or clearly repeated referral intent. Include all rows in the duplicate group when the template policy says all group rows are blockers.
- Treat shared insurance across different patients as an insurance anomaly, not a merge recommendation, unless duplicate-candidate evidence independently supports merge.
- Fill follow-up queues from evidence:
  - Authorization missing/pending from `authorization_status`.
  - Records request when required office-note records are absent.
  - Imaging follow-up when expected imaging is missing, pending, or explicitly noted as pending.
- Tier action plans from the strongest blocker:
  - Tier 1: urgent coding blockers or duplicate blockers.
  - Tier 2: routine coding, authorization, clinical mismatch, records, or imaging blockers.
  - Tier 3: administrative document completion when no coding, duplicate, authorization, or clinical mismatch blocker remains.
- Use `receiving_provider_id` as the owner provider unless the template or prompt specifies another ownership rule.
- Recompute summary counts from emitted arrays and tier lists, not from assumptions.

## Final Check

Before returning the answer:

- Confirm every required top-level key from the template is present.
- Confirm no template placeholder strings remain.
- Confirm all arrays obey the template's ordering or set semantics.
- Confirm IDs and enum labels are copied exactly from source data or the template.
- Confirm excluded distractors are only included in fields that request excluded evidence.
- Confirm the response parses as one JSON object.
