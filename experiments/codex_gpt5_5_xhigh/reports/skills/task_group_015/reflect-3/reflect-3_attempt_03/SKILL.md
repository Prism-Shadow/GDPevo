---
name: ehr-quality-governance
description: Solve healthcare EHR quality governance tasks against a shared EHR quality HTTP API. Use when prompts provide target IDs and an answer_template.json for duplicate chart reconciliation, referral batch audits, handoff packet completeness, service request validation, referral readiness, chart updates, provider routing, ICD-10 validation, or structured EHR quality decisions.
---

# EHR Quality Governance

## Core Workflow

1. Read the prompt, `task_scope.json`, and `answer_template.json` before querying data.
2. Query the API index first, then fetch only records relevant to the target IDs plus directly linked records:
   - patients for chart lists, encounters, disclosures, immunizations, demographics, and primary provider IDs
   - duplicate candidates for merge candidates and match/risk reasons
   - referrals and referral batches for queue rows, missing-item counts, insurance reuse, and referral routing
   - handoff packets for included sections and transfer metadata
   - service requests for order fields, linked encounters, SBAR text, and laterality evidence
   - providers for provider ID, specialty, fax, and routing decisions
   - ICD-10 codebook for description, body site, laterality, and tracking-range checks
   - audit log only when the answer schema asks for audit status or event IDs
3. Build the answer from the template schema, not from prose alone. Return one JSON object with exactly the requested keys, enum casing, field types, and nested shapes.
4. Leave unknown optional outputs empty (`[]` or `{}`) rather than omitting required keys. Do not add explanatory text outside JSON.

## API Habits

- Prefer targeted filtering with `jq` after fetching endpoint arrays. Join records by stable IDs in the prompt and task scope.
- Treat the API as the source of truth for all chart facts. Do not infer chart content from a document title or metadata unless the document body is actually available.
- Fetch the codebook whenever an ICD-10 field is involved. The codebook's `description`, `body_site`, `laterality`, and tracking flag often decide mismatch fields.
- Fetch providers whenever the output asks for a provider ID, specialty, fax/contact action, referral target, or receiving/sending provider validation.
- Fetch audit events only for schemas with audit output fields; map source statuses into the exact uppercase enum requested by the template.

## Output Conventions

- Use enum values exactly as listed in `answer_template.json`.
- For fields that copy source-system values rather than template enums, preserve source casing and spelling, such as request `status`, `priority`, `service_code`, and `specialty`.
- Sort ID lists ascending unless the field is explicitly a priority queue. Sort duplicate group members ascending, then sort groups by their first ID.
- For non-ID derived codes such as blockers and risk flags, use concise uppercase snake-case codes (`MISSING_RECOMMENDATION`, `COGNITIVE_STATUS_MISSING`) unless the source data provides a different exact value.
- For required clinical text that is explicitly missing from the source note, prefer `Not documented` over inventing a reaction, symptom, or rationale.
- Use codebook descriptions for `diagnosis_update.description` when a diagnosis code is supplied, even if the referral text uses a close paraphrase.
- Keep counts as integers and count only the exact status named by the field. For example, `auth_not_submitted` counts `Not Submitted`, not `Pending`.

## Duplicate Chart Reconciliation

- Compare every patient in the duplicate candidate: legal name, DOB, phone, address, enterprise MRN, primary provider, active disclosures, active problems, active medications, and active allergies.
- Choose the canonical target as the record with the strongest continuity evidence: fuller active chart, active disclosure, existing care relationship, or otherwise the most complete/current record. Use the other true duplicate as source.
- Preserve the union of active clinical lists across records:
  - active problem codes, not inactive problems
  - active medication IDs
  - active allergy labels
- Exclude only patients that are actually part of the reviewed candidate but should not merge.
- Use `MERGE_READY` only when demographics and chart evidence align and no risk flag blocks the merge. Use clarification/block dispositions when address, disclosure, identity, or safety conflicts remain.
- If the schema asks for contact action, require provider contact only for a real unresolved clarification. Otherwise use a no-contact action code and the relevant primary provider ID if the field requires a target.

## Referral Batch Audits

- Detect duplicate groups by same patient identity plus same condition/body site, not by insurance alone.
- Flag insurance anomalies when a reused insurance ID belongs partly to a true duplicate group and partly to unrelated referrals.
- Separate mismatch types:
  - laterality mismatch: diagnosis narrative side disagrees with codebook laterality for the same body site
  - narrative mismatch: codebook body site/description does not match the diagnosis narrative
  - out-of-range code: codebook tracking flag says the code is outside the requested quality range
- Add corrected code suggestions only when the codebook contains a clear single replacement for the same clinical concept and correct side.
- Count missing records, imaging, and auth from explicit row values only.
- Triage priority queues by operational risk: urgent safety/oncology/fracture or severe code problems first, clinical-code and missing-packet work next, administrative duplicate/insurance/auth cleanup last.

## Handoff Packet Review

- Compare `included_sections` and packet text fields. A section with an empty value is missing even if a nearby heading exists.
- Active chart lists include only entries whose status is active. Use labels for allergy-label fields and IDs for medication/encounter fields.
- Recent encounters should support the current transition; exclude stale or unrelated historical encounters.
- Most recent immunization is the latest by date, not by array position.
- Disclosure status should reflect whether an active disclosure covers the receiving facility or transfer purpose.
- Use `BLOCKED_INCOMPLETE_PACKET` when a required handoff section is absent. Use `READY_WITH_WARNINGS` only when the packet is complete but non-blocking risks remain.

## Service Request Validation

- Copy `order_validation` fields from the service request record unless the template explicitly asks for normalized enums.
- Parse SBAR strictly. A heading with no substantive text after it is not present.
- `missing_sbar_sections` should use the uppercase section names from the schema.
- Use linked encounters and the patient problem list as evidence. Verify service specialty and laterality against the encounter diagnosis and ICD-10 codebook.
- `laterality_consistent` is true only when the note, encounter diagnosis, problem/referral code, and codebook side all agree or laterality is genuinely not applicable.
- A missing required SBAR section blocks signing; set a specific blocker code and `ready_to_sign: false`.

## Referral Chart-Update Decisions

- Route referrals to the provider whose specialty best matches the referral reason and diagnosis; prefer a subspecialty provider when the diagnosis is specific.
- Treat referral notes such as "add allergy before sending" as chart-update requirements. Populate `allergy_update` from the note and do not invent undocumented reactions.
- If a structured update fully resolves the note and no other blockers remain, `send_ready` can be `READY`; otherwise use `NEEDS_CLARIFICATION` for missing facts and `BLOCKED` for safety or order-stopping defects.
- Use recent encounter IDs that support the referral diagnosis or reason. Do not include unrelated chronic-care encounters just because they are recent.
- For letter merge fields, provide the patient/referral/provider values needed to generate the outbound letter unless the template clearly asks for placeholder names.
- Keep `unresolved_quality_issues` focused on defects still unresolved after the proposed structured updates.

## Common Pitfalls

- Do not treat `Pending` authorization as `Not Submitted`.
- Do not include inactive problems, medications, or allergies in active-list outputs.
- Do not collapse laterality mismatch into narrative mismatch when the body site and diagnosis otherwise match.
- Do not trust a referral's free-text diagnosis over the ICD-10 codebook for corrected-code decisions.
- Do not mark a service request ready when a required SBAR heading is present but blank.
- Do not fabricate document contents, allergy reactions, provider specialties, or audit events.
