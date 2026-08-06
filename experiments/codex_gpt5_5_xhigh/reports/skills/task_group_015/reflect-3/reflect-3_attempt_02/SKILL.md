---
name: ehr-quality-packets
description: Produce normalized JSON packets for EHR quality governance tasks involving duplicate-chart review, referrals, care transitions, ServiceRequests, and referral batch audits.
---

# EHR Quality Packets

Use this skill when a task asks for a normalized JSON packet from a read-only EHR/referral quality environment. The goal is to reconcile case objects against chart evidence and return only the fields required by the task's answer template.

## Core Workflow

1. Read the prompt and answer template before collecting data. Extract every referenced patient, referral, duplicate candidate, ServiceRequest, provider, code, batch, and recipient identifier.
2. Collect the exact records named in the prompt, then collect directly related chart lists, documents, encounters, providers, service codes, disclosures, immunizations, and diagnosis-code metadata as needed by the requested packet.
3. Treat environment records as authoritative over narrative assumptions. Use stable record IDs and normalized keys from the records rather than display text.
4. Build the response from the template outward. Do not add explanatory prose, procedural notes, or fields not requested by the template.
5. Sort arrays that represent sets alphabetically. Preserve date or relevance order only when the template or prompt asks for "latest", "recent", "top", or an ordered handoff sequence.

## Normalization Rules

- Use `normalized_key` values for condition, medication, and allergy lists.
- Include only active clinical-list records unless the task explicitly asks for inactive, stale, or historical evidence.
- Exclude stale or unrelated distractors when the prompt is scoped to a packet purpose, specialty, laterality, or recipient service line.
- Use final/signed records as stronger evidence than draft, amended, stale, or unrelated records unless the task is specifically about draft quality.
- Prefer explicit review objects and preview fields over a raw union when a duplicate-review record already states the reviewed target, source, active key sets, match signals, or conflict signals.
- Use stable IDs in evidence fields: patient IDs, referral IDs, ServiceRequest IDs, document IDs, encounter IDs, condition IDs, audit IDs, provider IDs, service codes, and diagnosis codes.

## Duplicate Review

For duplicate-chart packets:

- Verify both patient demographics, canonical status, and candidate status.
- Derive merge target and source from explicit canonical status or duplicate-review preview fields.
- Do not mark a merge ready when target/source are absent, candidate status requires review, or conflict signals are material.
- Preserve reviewed active condition, medication, and allergy key sets from the duplicate-review record when available.
- Keep match signals and conflict signals separate and normalized.
- Use address abbreviations, nicknames, same DOB, shared phone, shared insurance, imported external documents, different names, different phone numbers, and opposite laterality as identity signals, not as narrative evidence.

## Referral Coordination

For referral packets:

- Reconcile the referral diagnosis code and narrative against active chart conditions, recent encounters, and diagnosis-code metadata.
- Include diagnosis codes that belong in the letter only when they are referral-relevant and supported by chart evidence.
- Classify readiness from authorization status, required documents, allergy verification, and unresolved coordination notes.
- Include allergy keys and medication keys only when they affect referral readiness or are relevant to the receiving specialty.
- Identify the receiving provider from the provider directory and verify the provider's service line matches the referral.
- Use recent signed encounters with matching diagnoses, care-plan notes, or mentioned medications as encounter evidence.

## Care Transitions

For transition or handoff packets:

- Verify the patient and recipient provider first, including the recipient service line and facility.
- Choose active condition, medication, and allergy keys according to the template: full current lists for current-chart fields, purpose-pruned lists for specialty-specific fields.
- Pick the latest immunization by date.
- Use the disclosure that matches the recipient or facility and has a permitted status.
- Select recent signed handoff encounters that match the recipient specialty, body site, diagnosis, and care-plan purpose; exclude unrelated encounters even if they are newer.
- Convert care-plan requirements, high-risk active conditions, relevant allergies, and recipient-specific concerns into normalized risk flags.
- Mark a packet not ready when required plans, disclosure permission, authorization, or required evidence is missing.

## ServiceRequest Quality

For ServiceRequest review:

- Validate that the request is attached to the intended patient and that requester and performer providers are plausible for their roles.
- Confirm the service code is active and belongs to the requested service line.
- Check every reason code against diagnosis-code metadata and the patient's active chart conditions.
- Verify laterality consistency across codes, narratives, conditions, encounters, and request text.
- Keep duplicate-review disposition separate from ServiceRequest quality: a draft may be clinically coherent but still held because identity review is unresolved.
- Report quality signals as normalized pass, defect, hold, or follow-up keys requested by the template.

## Referral Batch Audits

For batch audits:

- Filter to the exact batch and service line requested.
- Look up each diagnosis code and compare its chapter, expected terms, and laterality requirement with the referral narrative.
- Classify out-of-scope codes when the diagnosis belongs to another clinical domain for the requested service line.
- Classify laterality mismatches when a laterality-specific code conflicts with left/right terms in the narrative.
- Classify narrative-code mismatches when the narrative does not support the diagnosis-code expected terms, even if the code itself is in scope.
- Identify duplicates by explicit duplicate notes and by same patient, date, service line, body site, diagnosis family, or resubmission pattern.
- Build documentation queues from missing or pending clinical documents, unresolved clinical notes, or pending imaging requirements.
- Build authorization queues from missing, pending, or otherwise non-approved authorization status.
- Assign action tiers consistently: highest tier for stop/return issues such as out-of-scope codes or duplicates; middle tier for correction, documentation, authorization, or laterality follow-up; lowest tier for referrals ready for routine scheduling or monitoring.
- Recalculate summary counts from the final normalized queues, not from intermediate scratch lists.
