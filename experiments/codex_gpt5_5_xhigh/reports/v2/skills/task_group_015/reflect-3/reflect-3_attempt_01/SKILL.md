---
name: ehr-quality-governance
description: Use this skill for healthcare EHR quality-governance tasks that require inspecting a remote EHR quality API and returning strict JSON decisions for duplicate patient reconciliation, referral batch audits, care-transition handoff completeness, service request/order validation, or referral chart-update/send-readiness reviews.
---

# EHR Quality Governance

## Core Workflow

1. Read the task prompt, `task_scope.json`, and `answer_template.json` before calling the API.
2. Treat `answer_template.json` as the contract: emit one JSON object, with exactly the requested keys, field types, enum casing, and nested shape.
3. Use the task environment base URL and discover endpoints with `GET /api`. Query collection endpoints, then filter by the target IDs from `task_scope.json`.
4. Join records by stable IDs instead of names whenever possible: candidate IDs, patient IDs, referral IDs, batch IDs, packet IDs, request IDs, provider IDs, encounter IDs, and audit event IDs.
5. Keep raw API values when the output asks for record data: ICD-10 code casing/decimal style, provider specialty strings, service codes, request status/priority, chart status values, and encounter IDs.
6. Return JSON only. Do not include rationale prose, markdown, comments, or extra fields.

## Output Conventions

- Use allowed enum values exactly as listed in the template, including uppercase casing.
- Use empty arrays or empty objects for absent list/map results; avoid `null` unless the template explicitly allows it.
- Sort lists of stable identifiers ascending unless the field is explicitly a priority queue or otherwise asks for clinical ranking.
- For active chart lists, include only records whose `status` is `active`; exclude inactive problems, allergies, and medications.
- For date-sensitive selections, choose by the API date fields, not by array position. Example: most recent immunization is the latest immunization date.
- Preserve codebook descriptions exactly when a diagnosis update asks for an ICD-10 description.
- When a field is a free-form code such as `reason_code`, `blocker_codes`, `risk_flags`, or `safety_flags`, prefer concise uppercase, evidence-derived labels based on terms already present in the prompt/API. Do not invent narrative sentences.

## API Habits

- Pull only the relevant collection and filter locally, for example referrals by `batch_id` or patients by `patient_id`.
- Use the codebook for clinical validation instead of relying on diagnosis text alone. Check `code`, `description`, `body_site`, `laterality`, and any in-range flag exposed by the codebook.
- Use provider records to resolve target provider IDs and exact specialties; do not infer a provider ID from a specialty unless the provider endpoint supports it.
- Use audit-log entries for duplicate-review audit status and event IDs; map API statuses into the template enum casing.
- Be careful with mixed-type records when using `jq`; apply string tests only after selecting fields known to be strings.

## Duplicate Reconciliation

- Start from `/api/duplicate-candidates`, then fetch every patient in the candidate and the relevant audit-log rows.
- Confirm merge readiness from demographics and risk flags: same legal name, DOB, phone/email/address, and compatible clinical history support merge; conflicting current address or identity-risk flags should block or require clarification.
- Choose the canonical target as the more complete/current chart when there is a clear difference, especially the chart with active disclosure, richer active clinical lists, or the preferred enterprise record. Use the other duplicate as the source.
- Preserve the union of active allergy labels, active medication IDs, and active problem codes from merged charts. Do not carry inactive chart items.
- If an audit event exists, output its event ID and status mapped to the template enum. If not, use the template's no-event status.
- Contact actions should target the relevant provider only when clarification or correction is actually required; otherwise use a no-action convention consistently with the template.

## Referral Batch Audits

- Group duplicates by same patient identity plus the same clinical referral condition, not merely by shared insurance or shared referring fax.
- Flag insurance anomalies when a duplicate group shares an insurance ID with unrelated referral rows.
- Separate issue types:
  - `laterality_mismatch_referral_ids`: diagnosis text and ICD-10 laterality disagree.
  - `narrative_mismatch_referral_ids`: diagnosis text/body site does not match the codebook description beyond laterality alone.
  - `out_of_range_code_referral_ids`: codebook marks the code outside the queue's tracking range.
- Add corrected code suggestions only when the codebook contains a clear one-to-one corrected ICD-10 code. Do not guess when the narrative is ambiguous or bilateral but the codebook only offers unilateral choices.
- Count missing records, imaging, and authorization directly from row fields. Treat `Not Submitted` as not submitted; do not count `Pending` as missing submission.
- Priority queues should reflect operational urgency and blockers: urgent safety/oncology/code-blocking rows first, short-term rows for incomplete or correctable quality issues, and administrative rows for clean or low-risk follow-up.

## Handoff Packet Reviews

- Read the handoff packet and linked patient chart together.
- A section header is not enough if the corresponding packet field is empty; list the missing section.
- Missing material transition content, such as cognitive status for a receiving facility, should block completeness rather than be treated as a harmless warning.
- Use active chart problems, medications, and allergies only. Use recent encounter IDs that support the transition and exclude stale unrelated encounters.
- Derive disclosure status from an active disclosure matching the transfer purpose and recipient when possible.
- Risk flags should come from concrete evidence: high-risk medications, severe allergies, cardiopulmonary conditions, fall precautions, missing transition sections, or similar chart facts.

## Service Request Validation

- Preserve `order_validation` fields exactly from the request: `status`, `priority`, `service_code`, and `specialty`.
- Parse SBAR sections from `note_text`. A label with no content after it is missing/false.
- If any required SBAR section is empty, set `ready_to_sign` false, list the missing section, and use a blocker code that names the missing section.
- Validate laterality by comparing note text, linked encounter diagnoses, active problems, and the ICD-10 codebook.
- Evidence encounter IDs should be the linked encounters that actually support the order.

## Referral Chart-Update Decisions

- Cross-check referral row demographics with the patient chart before preparing updates.
- Diagnosis updates should use the referral ICD-10 code and the exact codebook description when the chart evidence supports it.
- Allergy updates should not invent reaction details. If the referral note supplies allergen and severity but not reaction, use a clearly non-invented placeholder only if the schema requires a reaction field.
- Select the referral target from the provider endpoint by the best specialty match, and preserve the provider's exact specialty string.
- If all required chart updates can be represented from available evidence, `send_ready` can be `READY` with no unresolved quality issues. Use `NEEDS_CLARIFICATION` or `BLOCKED` only when essential evidence is missing or unsafe to infer.
- Letter merge fields should be the concrete fields needed to generate/send the referral letter: patient identity, diagnosis/code, referral reason, referring provider/practice contact, target provider/specialty, and any required safety update such as a new allergy.

## Common Pitfalls

- Do not treat a referral note as already present in the chart; chart-update tasks often ask for a structured update because the chart is missing it.
- Do not collapse laterality mismatch and narrative/body-site mismatch unless the template asks for one combined issue set.
- Do not include inactive chart items in active lists just because they are clinically relevant historically.
- Do not mark a draft order ready when a required SBAR section is an empty header.
- Do not infer authorization problems from `Pending`; reserve not-submitted counts for explicit `Not Submitted`.
- Do not use provider names or specialties as IDs; output provider IDs where the schema asks for IDs.
