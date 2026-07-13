---
name: healthcare-ehr-quality-governance
description: Use when solving healthcare EHR quality governance tasks against a remote HTTP EHR API, including duplicate chart reconciliation, referral batch audits, handoff packet completeness reviews, service request/order validation, and referral chart-update or send-readiness decisions. Provides API collection habits, cross-resource reconciliation rules, ICD-10/codebook validation, JSON answer-template conventions, and common pitfalls for EHR quality review tasks.
---

# Healthcare EHR Quality Governance

## Ground Rules

Use the task-provided EHR API as the source of truth. Do not inspect local service source code or infer hidden database state. Start from the prompt, `task_scope.json`, `answer_template.json`, and the environment base URL.

Always read `answer_template.json` before analysis. The final response must be exactly one JSON object with the requested keys, field types, enum casing, and list ordering. Do not include prose around the JSON.

Prefer collection fetches plus local filtering. The API index may only advertise list endpoints, so do not assume per-record detail routes exist.

```bash
BASE="$TASK_ENV_BASE_URL"   # or the base URL supplied in environment_access.md
curl -sS "$BASE/health"
curl -sS "$BASE/api" | jq .
curl -sS "$BASE/api/patients" | jq --arg id "$PATIENT_ID" '.[] | select(.patient_id == $id)'
```

## API Collection Workflow

1. Identify target IDs from `task_scope.json` and the prompt.
2. Fetch `/api` to confirm available endpoints.
3. Pull the collection that owns the target object, then follow linked IDs:
   - Duplicate review: `/api/duplicate-candidates`, `/api/patients`, `/api/audit-log`, `/api/providers`.
   - Referral batch audit: `/api/referral-batches`, `/api/referrals`, `/api/codebook/icd10`, `/api/providers`.
   - Handoff review: `/api/handoff-packets`, `/api/patients`, `/api/providers`.
   - Service request validation: `/api/service-requests`, `/api/patients`, `/api/codebook/icd10`.
   - Referral/send-readiness decision: `/api/referrals`, `/api/patients`, `/api/providers`, `/api/codebook/icd10`, `/api/documents`.
4. Build a small evidence table for each output field. Track the endpoint and source field behind each decision so the final JSON is auditable.
5. Re-check the template immediately before final output.

## Output Conventions

Preserve the template shape exactly. Do not add explanatory keys, omit required keys, or use `null` unless the template explicitly allows it. Use `[]` for empty lists and `""` for empty strings when no better value is supported by evidence.

Use exact enum tokens from the template. Map source statuses into template enums only after confirming evidence; for example, audit log statuses may need conversion from lower snake case into uppercase enum tokens.

Sort stable identifier lists ascending unless the field is explicitly a priority queue or ranking. For named tier queues, keep the tier grouping and sort IDs inside each tier unless the prompt says otherwise. Counts are integers. Dates use `YYYY-MM-DD`; timestamps use ISO 8601.

For object maps such as corrected code suggestions, include only records that need an action. Do not include no-op referrals or placeholder map entries.

## Duplicate Chart Reconciliation

Fetch the duplicate candidate, all listed patient records, relevant providers, and audit-log entries. Compare identity fields first: legal name, DOB, phone, address, and any candidate `risk_flags`. A strong match with no current demographic conflict can proceed; different DOBs, conflicting current addresses, or "similar name only" evidence should block or reject the merge.

Find the duplicate-review audit event by matching the same patient ID set, not just one patient ID. Set the audit status from that event when present; if no matching event exists, use the template's no-event status and avoid claiming audit readiness.

Choose the canonical target as the most authoritative record to keep: the record with stronger active care context, active disclosure, fuller chart content, or otherwise more complete demographics. The source patient is the other record being merged. If the merge is blocked, do not invent a confident canonical/source relationship beyond what the schema requires.

Preserve only active clinical data. Union active medication IDs, active problem codes, and active allergy labels across merge-ready records; exclude inactive, resolved, historical, and duplicate values. Sort the resulting lists. Use `excluded_patient_ids` only for candidate records intentionally not merged.

Use contact-action fields for real follow-up needs: demographic conflicts, missing disclosure, absent audit event, or provider clarification. If no contact is needed but a contact object is required, set `action_required` to `false` and use empty strings or the task's no-op convention for action/provider fields.

## Referral Batch Quality Audits

Filter referrals to the target `batch_id`; do not mix rows from other months or service lines. Compare each row against the ICD-10 codebook and against other rows in the same batch.

Detect duplicate groups by matching patient name, DOB, insurance ID, and clinically equivalent diagnosis/body site/laterality. Notes such as same condition, duplicate, or second submission can confirm duplication. Sort IDs inside each group and sort groups by their first ID.

Flag insurance anomalies when the same insurance ID appears on unrelated patients. Separate IDs that are part of a true duplicate group from unrelated referrals that merely share the insurance identifier.

Validate ICD-10 codes using the codebook fields, not text intuition alone:
- `in_musculoskeletal_tracking_range` controls out-of-range flags for orthopedic tracking queues.
- `laterality` and `body_site` must agree with the referral narrative when the narrative names a side or site.
- A code can be in range but still be a narrative mismatch if its description/body site does not match the referral text.
- A code can be clinically orthopedic but out of the configured tracking range if the codebook marks it false.

Add corrected code suggestions only when the codebook contains a clear replacement matching the narrative diagnosis, body site, and laterality. Preserve the codebook's decimal and case style.

Compute missing counts directly from row fields: records missing when `records_received` is not yes, imaging missing when `imaging_received` is not yes, and authorization not submitted when authorization is required and `auth_status` says not submitted. Pending authorization is not the same as not submitted unless the task says so.

Prioritize queues by operational risk:
- Tier 1: urgent clinical/safety issues, oncology coordination, fractures/pathologic findings, or issues that should stop immediate scheduling.
- Tier 2: near-term quality blockers such as code/laterality corrections, duplicate resolution, or missing clinical evidence needed before routine processing.
- Tier 3: administrative cleanup such as authorization submission, insurance anomalies, or non-urgent missing paperwork.

## Handoff Packet Reviews

Fetch the handoff packet and patient chart. Compare `included_sections` and packet narrative fields against expected care-transition content: demographics, active problems, active medications, allergies, recent encounters, immunizations, functional status, cognitive status, transfer plan, and disclosure.

Treat a section as missing if it is absent from `included_sections` or the corresponding required narrative field is empty. Do not count a label as complete just because it appears in metadata.

Use only active chart items for active-problem, active-medication, and allergy outputs. Exclude inactive problems and inactive medications even when they appear in the chart. Select the most recent immunization by date. Select recent encounters that support the transfer context and exclude stale or unrelated encounters.

Determine disclosure status from active patient disclosures that match the transfer purpose or receiving organization. Missing or inactive disclosure is a readiness blocker.

Use readiness conservatively. `READY` requires complete packet sections, active disclosure, and no unresolved safety issue. `READY_WITH_WARNINGS` fits minor non-blocking concerns. Missing required sections, missing disclosure, or safety-critical omissions should use the incomplete or clarification/blocker enum from the template.

## Service Request And Order Validation

Fetch the service request, patient chart, linked encounters, and codebook entries for encounter diagnoses. Copy source order fields such as status, priority, service code, and specialty into `order_validation` unless the template asks for normalized values.

Parse SBAR note text by section labels. A section is present only when the label has non-empty content before the next label or the end of the note. A label followed by nothing is missing.

Check laterality against all available evidence: request note, active problems, linked encounter diagnoses, and codebook laterality for the clinical diagnosis. The service code itself may identify a service rather than a diagnosis, so use linked diagnosis evidence when validating side/site consistency.

Set `ready_to_sign` to `true` only when SBAR content is complete, laterality is consistent, the specialty/service is appropriate, and there are no blocker codes. Use concise uppercase blocker codes for concrete failures such as missing SBAR sections, laterality conflict, unsupported diagnosis, or unsafe order state.

## Referral Chart-Update And Send-Readiness Decisions

Fetch the referral, patient chart, providers, codebook, and any task-related document metadata. Verify that referral demographics match the patient record before deriving updates.

Choose the referral target from the provider list by receiving specialty and clinical fit, not from the referring physician fields. When a diagnosis is subspecialty-specific, prefer the provider whose specialty most closely matches the referral reason.

Use the codebook description for diagnosis updates when available. If the referral code conflicts with the narrative, derive the corrected code from the codebook before marking the referral ready.

Apply chart updates only from explicit evidence. Referral notes may require allergy, diagnosis, or safety updates before sending. If an allergy update is required, preserve the allergen, reaction, severity, and active status from the evidence; do not invent missing severity or reaction details beyond the task's convention.

Use recent encounter IDs that support the referral reason. Exclude unrelated maintenance encounters. Sort IDs unless a field explicitly requests chronology.

Set `send_ready` conservatively:
- `READY` only when required chart updates are represented, the target provider is appropriate, and no safety flags remain.
- `NEEDS_CLARIFICATION` for incomplete but non-dangerous ambiguity.
- `BLOCKED` for patient mismatch, unresolved safety-critical chart update, missing target, or other issue that should stop sending.

## Common Pitfalls

Do not use inactive chart items in active output fields.

Do not rely on diagnosis text alone for ICD-10 laterality; always compare to the codebook.

Do not count pending authorization as not submitted unless the row explicitly says not submitted.

Do not treat document metadata as document content. Use `related_ids` to discover relevance, but avoid hallucinating form fields or narrative from a title alone.

Do not output train-case IDs, worked examples, or reasoning. The final answer for a task is JSON only.

Before finalizing, validate: target IDs match the prompt, every output ID exists in fetched data, lists are sorted, enums match the template exactly, booleans are real booleans, and no extra prose surrounds the JSON.
