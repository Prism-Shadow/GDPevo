---
name: healthcare-ehr-quality-governance
description: Solve EHR quality-governance tasks involving duplicate reconciliation, referral batch audits, handoff packet review, service-request validation, and referral chart-update readiness using the shared HTTP API and strict JSON templates.
---

# Healthcare EHR Quality Governance

Use this skill when a task asks for a structured EHR quality decision from a remote API. The common pattern is to reconcile a scoped identifier against patient charts, referrals, providers, service requests, handoff packets, documents, codebooks, and audit events, then return one JSON object that exactly follows the provided `answer_template.json`.

## Core Workflow

1. Read the prompt, `task_scope.json`, and `answer_template.json` before calling the API.
2. Use the base URL from the environment access instructions and call `GET /api` to confirm available endpoints.
3. Fetch only the collections needed for the scoped IDs, then filter locally by stable IDs such as `patient_id`, `referral_id`, `batch_id`, `packet_id`, `request_id`, or duplicate candidate ID.
4. Keep a short evidence table while working: source row, chart evidence, codebook match, provider match, disclosure/audit status, and unresolved issue.
5. Build the JSON from the template keys only. Use exact enum casing from the template and source-string casing from the API.
6. Sort lists of stable identifiers ascending unless the field is explicitly a priority/ranking queue. When a list contains clinical labels or codes derived from chart items, prefer the chart item/stable-ID order if the template does not provide a stronger rule.

## API Habits

- Most endpoints are collection endpoints. It is normal to fetch a collection and select the scoped objects locally.
- Provider routing comes from `/api/providers`; do not invent a provider when the directory has a relevant specialty.
- ICD-10 validation comes from `/api/codebook/icd10`. Use it for description, body site, laterality, and whether a code is in the expected tracking range.
- Patient charts carry active and inactive clinical lists. Include only records with `status: "active"` unless the template explicitly asks otherwise.
- Audit and disclosure fields are separate from clinical facts. Check `/api/audit-log` for merge events and the patient `disclosures` array for authorization or care-transition status.

## Output Conventions

- Return JSON only, with no prose wrapper.
- Preserve template object structure and enum values exactly.
- Use API IDs, not display names, for ID fields.
- Use source strings for provider specialty, request status, request priority, allergy severity, and allergy status.
- For date fields, use `YYYY-MM-DD`; for timestamps, preserve ISO 8601.
- For booleans, use JSON booleans, not strings.
- For empty-but-required lists, return `[]`. For empty-but-required strings, use the task's established source convention only when the template clearly expects a string; otherwise prefer a meaningful source-derived value over an invented placeholder.

## Duplicate Reconciliation

- Confirm the candidate row, then inspect both patient records, disclosures, providers, documents, and audit events.
- A merge-ready duplicate should match on core demographics and contact/address data, with no identity conflict flags. Conflicting current address, different DOB, or other risk flags should push the decision to clarification or do-not-merge.
- Preserve the union of active clinical data from all records: active problem codes, active medication IDs, and active allergy labels. Exclude inactive items.
- Pick the canonical target using chart governance signals such as the more complete/current record, valid disclosure, primary provider continuity, and audit readiness. Keep the other duplicate as the source.
- The merge audit object should reflect the actual audit event. If no merge/review event exists, use the template's no-event status rather than inventing an event ID.
- Contact actions are only required for real blockers such as unresolved identity conflict, expired/missing disclosure, or provider clarification. Do not require contact just because a merge is otherwise ready.

## Referral Batch Audits

- Filter referrals by `batch_id` first; do not audit other batches.
- Detect duplicate groups by same patient identity plus same/similar condition, not by insurance alone.
- Treat a shared insurance ID as an anomaly when the same ID appears on unrelated patients; separate the duplicate-related referral IDs from unrelated referral IDs.
- Use the ICD-10 codebook to distinguish:
  - laterality mismatch: diagnosis text says left/right but the codebook code says the opposite side;
  - narrative mismatch: diagnosis text/body site does not match the code description;
  - out-of-range code: codebook marks it outside the tracking range for the queue.
- Suggest corrected ICD-10 codes only when the codebook contains a single clear replacement. Do not force a single correction for ambiguous or bilateral/nonspecific text when the available codebook does not support it.
- Count workflow gaps independently: missing imaging, missing records, and authorization not submitted can overlap on the same referral.
- Priority queues should reflect operational urgency:
  - tier 1 for immediate clinical safety or high-risk specialty coordination;
  - tier 2 for short-term clinical/code cleanup and missing clinical packet material;
  - tier 3 for administrative cleanup such as duplicate handling, insurance anomalies, or routine authorization follow-up.

## Handoff Packet Review

- Compare `included_sections` against actual nonempty packet fields. A section label is not complete if its corresponding field is blank.
- Active problems, medications, and allergies come from the patient chart, not from free text in the packet.
- Recent encounters should be selected from the patient chart by recency and relevance to the transfer reason; exclude stale encounters unrelated to the transition.
- The most recent immunization is the immunization with the latest date.
- Disclosure status should come from a care-transition disclosure for the receiving facility or recipient.
- Missing required packet sections should use the packet/API section key such as `cognitive_status`.
- A missing required handoff section blocks readiness as `BLOCKED_INCOMPLETE_PACKET`; do not downgrade it to a generic clarification when the packet is structurally incomplete.

## Service Request Validation

- Validate the order object fields directly from the service request: `status`, `priority`, `service_code`, and `specialty`.
- Parse SBAR note text by section labels. A label with no substantive content after it is missing.
- `sbar_sections_present` uses uppercase keys from the template. `missing_sbar_sections` should use the same uppercase section names.
- Compare laterality across note text, linked encounter diagnoses/care plan, active problems, and codebook entries.
- Evidence encounter IDs should be the linked encounters that support the order.
- A draft with missing SBAR content is not ready to sign. Use concise uppercase blocker codes, for example `MISSING_RECOMMENDATION` when the Recommendation section is empty.

## Referral Chart-Update Readiness

- Reconcile the referral row with the patient chart before deciding send readiness.
- `diagnosis_update` should use the referral ICD-10 code and the codebook/source description when they agree.
- `allergy_update` should be populated from explicit referral notes or chart evidence. Do not invent a clinical reaction that is not documented; if the template requires a reaction and the source omits it, use a clear nonclinical placeholder consistent with the task's string style.
- Route the referral to the most specific matching provider in the directory. For subspecialty diagnoses, prefer a subspecialty provider over a generic service-line guess.
- Recent encounter IDs should support the referral reason; do not include unrelated routine encounters merely because they are nearby in time.
- `send_ready` is an after-decision status. If all required chart updates are explicitly represented and no quality issue remains unresolved, `READY` can be appropriate even when the source chart did not already contain the update. Use `BLOCKED` or `NEEDS_CLARIFICATION` only when required evidence is missing, unsafe, contradictory, or cannot be represented by the returned update fields.
- Keep `unresolved_quality_issues` for issues that remain after the proposed updates, not for issues already handled by the structured update fields.

## Common Pitfalls

- Do not treat every urgent referral as tier 1; urgency alone is not the same as immediate quality/safety escalation.
- Do not conflate laterality mismatch with narrative/body-site mismatch; they are separate issue sets.
- Do not count `auth_status: "Pending"` as not submitted.
- Do not include inactive chart items in active lists.
- Do not mark an SBAR section present just because the label exists.
- Do not invent corrected codes when the codebook lacks a precise one-to-one correction.
- Do not use provider names where provider IDs are requested.
- Do not include development-only process notes in a final answer.
