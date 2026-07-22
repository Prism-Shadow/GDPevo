---
name: ehr-quality-packet-json
description: Generate normalized JSON packets and audits from read-only EHR quality-governance environments. Use when a task asks Codex to inspect EHR/referral/duplicate/service-request evidence through allowed API endpoints and return schema-conformant JSON for duplicate chart review, referral coordination, care transitions, service request quality checks, or referral batch audits.
---

# EHR Quality Packet JSON

Use this skill to produce evidence-grounded, normalized JSON for EHR quality-governance tasks. Treat the prompt and `input/payloads/answer_template.json` as the contract. Do not include prose outside the final JSON.

## Core Workflow

1. Read the task prompt, every file in `input/payloads/`, and `environment_access.md`.
2. Use only the base URL and endpoints listed in `environment_access.md` for network access.
3. Extract all requested stable IDs from the prompt and payloads: patient, duplicate candidate, referral, service request, provider, batch, document, or request IDs.
4. Inspect the primary object first, then fetch all supporting evidence needed by the template:
   - patient demographics and identifiers
   - active conditions, medications, and allergies
   - encounters, documents, immunizations, disclosures, and audit logs
   - duplicate candidates and duplicate details
   - referrals or referral batches
   - service requests, service codes, ICD-10 codes, and provider directory records
5. Build the answer from environment evidence only. Do not infer clinical facts, contact values, code chapters, readiness status, or missing-document status from names or narratives when an endpoint can verify them.
6. Return exactly one JSON object conforming to the template. Preserve required top-level keys and field types, including compatibility duplicate fields when a template asks for overlapping sections.

## Template Handling

- Treat `answer_template.json` as both schema and policy text. Honor embedded enum values, required values, set semantics, ordering rules, fixed lengths, and narrative labels.
- If the template contains wrapper keys such as `schema`, `types`, `required_top_level_keys`, or descriptions, output the requested data shape, not the template metadata.
- Use IDs and normalized keys exactly as returned by the API.
- Sort arrays exactly as specified. If the template says set semantics and gives no stricter order, sort stable string arrays ascending for deterministic output.
- For arrays of objects, use the ordering specified by the template, commonly by ID ascending, code ascending, risk flag ascending, or newest-to-oldest encounter date.
- Use `null` only where the template permits null. Otherwise leave no required field unknown: fetch more evidence or choose the correct enum from the evidence.
- Do not add explanatory fields, comments, provenance notes, markdown, or SOP text.

## Evidence Rules

- Prefer authoritative detail endpoints over previews, summaries, or prompt wording. If a duplicate preview omits active list items, use patient active-list endpoints as authoritative and record additions when the template asks.
- Active clinical lists mean active records only. Exclude inactive, entered-in-error, stale, unrelated, or non-case records unless a distractor/exclusion field explicitly asks for them.
- Validate ICD-10 codes through the ICD endpoint. Record chapter, validity, and whether the code matches patient evidence and referral narrative.
- Validate service codes through the service-code endpoint and provider roles/service lines through provider detail records.
- Select provider contact information from the provider directory, not from free text. Use the receiving, requester, performer, specialist, or primary-care role requested by the template.
- Select documents by task relevance, status, type, and date. Prefer final required clinical or identity/continuity documents when requested; exclude unrelated, preliminary, cancelled, stale, or wrong-purpose documents according to the template policy.
- Select encounters by the requested clinical handoff or referral relevance, status, and recency. Do not mechanically choose the latest encounter if the task asks for specific handoff, SBAR, diagnosis, medication, or care-plan evidence.
- Select disclosures only when they match the requested recipient or purpose and have an acceptable status under the template.
- Include audit IDs only when they directly support the requested packet, merge, identity, disclosure, or governance decision.

## Decision Patterns

For duplicate-review and merge packets:

- Verify candidate status, patient identity signals, demographics, insurance/address/phone/name/DOB signals, conflict signals, audit history, and related documents.
- Choose merge target/source from canonical indicators in the duplicate detail or governance evidence. If conflicts block automation, use the review-hold/readiness enum requested by the template.
- Produce active condition, medication, and allergy unions from the authoritative active endpoints for both patients.
- Keep match signals and conflict signals as normalized labels from evidence; do not invent synonyms.

For referral coordination:

- Reconcile the referral with the patient chart, active diagnoses, referral narrative, ICD validation, allergies, recent encounter evidence, required documents, authorization, receiving provider, and relevant active medications.
- Highlight medications because they are referral-relevant, not because they merely exist, unless the template asks for all active medications as fallback.
- Set readiness from blockers: authorization, missing required documents, allergy clarification, invalid diagnosis code, clinical mismatch, or missing provider.

For care transition packets:

- Return patient and recipient identifiers, active normalized clinical keys, the requested number of relevant handoff encounters, latest immunization, applicable disclosure, risk flags, evidence for each risk flag, and readiness.
- Risk flags must be backed by active conditions, active medications, relevant encounters, or allergies as the template permits.
- Exclude stale or unrelated encounters and list their IDs when the template asks for source selection exclusions.

For service-request quality checks:

- Validate status, intent, priority, requester, performer, performer service line, service code, dates, reason codes, and reason-code evidence.
- For SBAR-style fields, determine coverage from the actual sections/evidence and enumerate missing sections.
- Keep duplicate-review decisions separate from service-request validation, even when both appear in one output.

For referral batch audits:

- Retrieve the full batch or search result set before counting. Compute counts from audited rows, not from filtered subsets.
- Validate every referral diagnosis code, chapter, narrative/laterality consistency, authorization status, document status, imaging status, patient identity, provider ownership, and duplicate grouping.
- Separate same-patient duplicate resubmissions from same-patient separate clinical referrals and from shared-insurance/different-patient anomalies.
- Tier action plans from the template's policy: urgent coding or duplicate blockers first, routine coding/auth/document blockers next, administrative completion last.
- Make summary counts reconcile with the emitted arrays and queues.

## Final Checks

Before responding:

- Confirm every required top-level key is present.
- Confirm all enum values are copied exactly from the template.
- Confirm sorted arrays and fixed-length selections follow template rules.
- Confirm counts equal the records emitted or audited.
- Confirm no task-specific training values, hidden reasoning, or narrative text appear outside the JSON.
