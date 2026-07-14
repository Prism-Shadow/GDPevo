---
name: healthcare-ehr-quality-governance
description: Use for EHR quality-governance tasks that require querying a remote healthcare quality API to reconcile duplicate patient charts, audit referral batches, review care-transition handoff packets, validate service request/order drafts, or prepare referral chart-update decisions. Produces strict JSON matching task answer templates, with provider/codebook cross-checks, readiness and priority decisions, sorted issue lists, and healthcare quality business rules.
---

# Healthcare EHR Quality Governance

## Core workflow

1. Read the task prompt, `task_scope.json`, and `answer_template.json` first. Treat the template as the output contract: exact keys, enum casing, field types, and list ordering win over prose assumptions.
2. Set the base URL from the prompt or environment access file, then check `GET /health` and `GET /api`.
3. Use only the remote HTTP API for task facts. Fetch full endpoint arrays and filter by exact target IDs with `jq`; do not infer from nearby IDs.
4. Cross-check linked records instead of trusting one row: referrals need provider and ICD-10 checks; duplicate candidates need patient charts and audit log; handoffs need packet plus chart; service requests need linked encounters and chart evidence.
5. Return one JSON object only. Include required empty lists/objects when the template requires them.

Useful shell pattern:

```bash
BASE="$TASK_ENV_BASE_URL"
curl -sS "$BASE/api"
curl -sS "$BASE/api/patients" | jq '.[] | select(.patient_id==$id)' --arg id "$PATIENT_ID"
```

## Endpoint habits

- `/api/patients`: demographics, provider ID, active/inactive problems, medications, allergies, disclosures, encounters, immunizations, and patient document IDs.
- `/api/duplicate-candidates`: candidate ID, member patient IDs, match reasons, risk flags, and suggested action. Always inspect the member patient charts.
- `/api/referrals`: batch rows and individual referral rows. Many fields are strings such as `"Yes"`, `"No"`, `"Pending"`, `"Not Submitted"`, `"N/A"`, or `""`; normalize deliberately.
- `/api/referral-batches`: batch metadata only. Filter `/api/referrals` by `batch_id` for the actual worklist.
- `/api/handoff-packets`: packet sections and transition-specific fields. Verify against the patient chart rather than assuming the packet is complete.
- `/api/service-requests`: order draft metadata, note text, linked encounter IDs, service code/display, specialty, priority, and status.
- `/api/providers`: provider IDs, names, specialties, and fax numbers. Use provider IDs in outputs when requested.
- `/api/codebook/icd10`: ICD-10 description, body site, laterality, chapter prefix, and tracking-range flag. Preserve code case and decimal style from the codebook.
- `/api/documents`: document metadata only unless an endpoint exposes more. Do not invent unavailable document contents.
- `/api/audit-log`: audit events, patient ID sets, status, timestamp, user. Match duplicate-review events by the exact unordered patient ID set.

## JSON conventions

- Use only allowed enum strings from the template for enum fields.
- Sort stable identifier lists ascending unless a field explicitly represents a priority/ranking queue. For nested lists, sort inside each group and sort groups deterministically by their first ID.
- Counts are integers. Do not count `"Pending"` authorization as `"Not Submitted"`.
- For dynamic maps such as corrected-code suggestions, include only records that actually need that output.
- Use IDs where fields ask for IDs, labels where fields ask for labels, and ICD-10 codes where fields ask for codes.
- Treat empty strings, absent sections, and header-only note sections as missing content.
- Do not output explanatory prose, markdown, comments, or the base URL.

## Duplicate chart reconciliation

Review the duplicate candidate, all member patient charts, disclosures, providers, and matching audit-log event.

- Merge only when identity facts are compatible: legal name, DOB, phone/address, and clinical context should not conflict. Address/name/DOB conflicts or candidate risk flags usually block or require clarification.
- Map audit-log status to the template enum when available: a matching ready event supports `READY_FOR_MERGE`; a blocked address-conflict event supports `BLOCKED_ADDRESS_CONFLICT`; no exact event supports `NO_EVENT_FOUND`. Use the audit event ID when present; otherwise use the template's empty-string/null convention if one is implied.
- Choose the canonical target as the chart with better governance continuity: richer active clinical lists, active disclosures, current primary provider, or otherwise more complete/current data. The source is the non-canonical duplicate chart.
- Preserve active clinical information from every merge member. Problems are usually deduplicated by ICD-10 code, medications by medication ID, and allergies by label/allergen; inactive items are excluded unless the template asks otherwise.
- Populate excluded patient IDs only for candidate members that are not safe to merge.
- Contact action fields should reflect governance work that remains: no action when audit/disclosure/provider facts are clean; require provider or disclosure clarification when merge safety depends on missing authorization, provider mismatch, or an audit block.

## Referral batch audit

Filter referrals by the requested `batch_id`, then compute issue sets from referral rows plus codebook/provider checks.

- Missing counts:
  - `records_missing`: `records_received == "No"`.
  - `imaging_missing`: `imaging_received == "No"`.
  - `auth_not_submitted`: `auth_required == "Yes"` and `auth_status == "Not Submitted"`.
- Duplicate groups are same-patient/same-condition groups: match patient name plus DOB and compatible diagnosis/body site/laterality. Shared insurance alone is not a duplicate.
- Insurance anomalies are repeated insurance IDs that span both a duplicate group and unrelated referral rows. Separate `related_duplicate_referral_ids` from `unrelated_referral_ids`.
- Out-of-range code issues come from `in_musculoskeletal_tracking_range == false`, not from intuition about whether a condition is orthopedic.
- Laterality mismatch means the narrative/referral reason/notes explicitly say left or right and the codebook entry says the opposite side.
- Narrative mismatch means the ICD-10 codebook description/body site does not match the referral diagnosis narrative, even if laterality is absent.
- Corrected ICD-10 suggestions should be emitted only when one codebook entry unambiguously matches the diagnosis term, body site, and laterality. Do not guess a single code for bilateral or underspecified narratives.
- Priority queues should use the highest applicable severity for each referral:
  - Tier 1: urgent clinical/safety work, fracture/oncology/ER-style notes, or urgent rows with code/laterality defects.
  - Tier 2: non-urgent clinical-quality blockers such as duplicates, out-of-range or mismatched diagnosis coding, missing records, or missing imaging.
  - Tier 3: administrative-only cleanup such as authorization not submitted, scheduling/contact cleanup, or insurance cleanup when no clinical blocker is present.

## Handoff packet review

Inspect the packet, receiving/sending providers, patient chart, immunizations, encounters, and disclosures.

- Required packet content commonly includes demographics, active problems, active medications, allergies, recent encounters, immunizations, functional status, cognitive status, transfer plan, and disclosure. A section listed in `included_sections` is still missing if the corresponding content field is blank.
- Active clinical lists should include only records with active status. Sort medication IDs, problem codes, and allergy labels as the template requires.
- Recent encounters should be clinically relevant to the transfer and near the packet creation date; exclude stale unrelated history unless the prompt asks for a broader history.
- The most recent immunization is the immunization with the latest date, returned by ID.
- Disclosure status should be based on an active disclosure matching the transfer purpose/recipient when possible; missing or mismatched disclosure is a governance issue.
- Readiness rule of thumb: required packet content missing -> `BLOCKED_INCOMPLETE_PACKET`; disclosure/provider ambiguity -> `NEEDS_CLARIFICATION`; complete packet with clinical risks -> `READY_WITH_WARNINGS`; complete and low-risk -> `READY`.
- Risk flags should be concise stable codes grounded in evidence, such as severe allergies, anticoagulation/high-risk medications, fall/cognitive/functional risks, high-risk active diagnoses, missing disclosure, or missing packet sections.

## Service request validation

Inspect the service request draft, linked patient chart, linked encounters, and ICD-10 codebook.

- Do not treat the service request `service_code` as an ICD-10 code. Validate diagnosis evidence from linked encounters/problems and the codebook.
- Parse SBAR note text for `SITUATION`, `BACKGROUND`, `ASSESSMENT`, and `RECOMMENDATION`. A present header with no substantive text is missing.
- `sbar_sections_present` should indicate content presence, not just header presence.
- Evidence encounter IDs should be linked encounters that exist in the patient chart and support the requested service, diagnosis, body site, and laterality. Include additional chart encounters only if the template or prompt asks for all supporting evidence.
- Laterality is consistent only when the request text, note text, chart diagnoses, and ICD-10 codebook laterality agree. A neutral code is acceptable only when no explicit side is required.
- Blockers commonly include missing SBAR content, unsupported diagnosis evidence, laterality conflicts, inappropriate status/intent, or safety ambiguity. `ready_to_sign` is true only when there are no blockers and the draft is otherwise signable.

## Referral chart-update decision

For an individual referral, inspect the referral row, patient chart, recent encounters, providers, and codebook.

- Choose the referral target from an assigned physician when valid; otherwise match the referral specialty/diagnosis to the closest provider specialty. Return provider IDs, not names, when requested.
- Diagnosis updates should preserve the referral ICD-10 code and use the codebook description when the code exists there; otherwise use the referral description and flag ambiguity if needed.
- Allergy updates should come from explicit referral notes or chart evidence. Capture allergen, reaction, severity, and status; if a clinically required detail is not documented, flag it as unresolved rather than inventing it.
- Recent encounter IDs should support the referral reason or diagnosis near the referral date, not every historical encounter.
- Letter merge fields should be field keys needed or populated for the referral communication, not the actual patient values. Include only fields relevant to the template.
- Safety flags should be grounded in referral/chart evidence: severe allergy update needed, missing allergy reaction detail, diagnosis mismatch, missing required records, missing authorization, provider-target ambiguity, or similar send-safety blockers.
- `send_ready` should be `READY` only when required chart updates, records, authorization, target provider, and safety checks are complete; `NEEDS_CLARIFICATION` when needed details are ambiguous; `BLOCKED` when required records/auth/safety conditions are absent.

## Common pitfalls

- Do not use local environment source code; the API is the source of truth.
- Do not use records with similar non-target IDs to answer a target task.
- Do not assume `M` chapter codes are always acceptable or `S` chapter codes are always unacceptable; use the codebook tracking flag.
- Do not count authorization `Pending` as not submitted.
- Do not treat appointment not scheduled or empty assigned physician as an issue unless the template asks for scheduling/provider readiness.
- Do not include inactive problems, medications, or allergies in active-list fields.
- Do not output all possible issues when a field asks for unresolved issues after proposed updates; include only blockers still requiring action.
