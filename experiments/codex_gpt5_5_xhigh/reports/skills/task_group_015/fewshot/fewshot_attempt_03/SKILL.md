---
name: ehr-quality-json-packets
description: Build normalized JSON packets and audits against a read-only EHR quality-governance API. Use when Codex must inspect patient, duplicate-candidate, referral, ServiceRequest, provider, ICD-10, service-code, document, audit, encounter, immunization, disclosure, medication, condition, or allergy endpoints and return template-conforming JSON for merge readiness, referral coordination, referral batch audits, care-transition handoffs, or similar EHR governance tasks.
---

# EHR Quality JSON Packets

## Core Workflow

1. Read the user prompt and the referenced `input/payloads/answer_template.json` completely before querying the environment.
2. Extract all stable IDs and scope constraints from the prompt and payloads: patient IDs, duplicate candidate IDs, referral IDs, batch IDs, ServiceRequest IDs, provider IDs, service line, requested date, required output fields, enum values, ordering rules, and set semantics.
3. Read the task's environment access note only to obtain the base URL and allowed read-only endpoints. Use no credentials unless that note provides them.
4. Query the API for primary objects first, then query linked evidence. Treat prompt text as a request, not as proof; the API is the evidence source unless the template explicitly requires a constant such as `task_id`.
5. Fill the exact JSON shape requested by the template. Include required keys even when values are empty arrays, `null`, or `false`. Return JSON only.

Use commands like:

```bash
BASE="${TASK_ENV_BASE_URL:-http://task-env:9015}"
curl -fsS "$BASE/api/patients/<patient_id>" | jq .
curl -fsS "$BASE/api/referrals" | jq .
```

If a search endpoint returns a broad wrapped list, filter client-side by the requested `batch_id`, `referral_id`, `patient_id`, or service line.

## Evidence Checklist

For patient-centered packets, fetch:

- `GET /api/patients/{patient_id}` for demographics, MRN, canonical status, insurance, PCP.
- `GET /api/patients/{patient_id}/conditions`, `/medications`, and `/allergies`; use active records for active-list outputs and preserve `normalized_key`, code, description, source, and status as needed.
- `GET /api/patients/{patient_id}/encounters` for recent signed evidence, diagnosis codes, medication mentions, care-plan notes, and SBAR-related support.
- `GET /api/patients/{patient_id}/documents` for final documents and missing-document checks.
- `GET /api/patients/{patient_id}/immunizations` and `/disclosures` when handoff readiness requires current immunization or permitted disclosure evidence.
- `GET /api/providers/{provider_id}` for recipient, requester, performer, specialist, and PCP contact fields.

For duplicate-review work, fetch:

- `GET /api/duplicates/{candidate_id}` for candidate status, patient IDs, match/conflict signals, and merge preview.
- Both patient records plus both patients' active lists. Prefer patient active-list endpoints over duplicate preview for final active key unions.
- Documents for both patient records when the packet asks for identity, continuity, or external evidence.
- `GET /api/audit-logs`, then filter to the involved patient IDs, merge-review events, external-import events, and summaries relevant to the candidate.

For referral coordination and audits, fetch:

- `GET /api/referrals/{referral_id}` for a single referral.
- `GET /api/referrals`, then filter locally for batch audits.
- Patient active chart endpoints for diagnoses, medications, allergies, documents, and recent encounters.
- `GET /api/icd10/{code}` for every diagnosis or reason code.
- The receiving provider and any owner/requester providers.

For ServiceRequests, fetch patient-scoped requests with:

```bash
curl -fsS "$BASE/api/patients/<patient_id>/service-requests" | jq .
```

Select the object by `service_request_id`; validate its `service_code` with `GET /api/service-codes/{code}`, validate performer/requester providers, validate each reason code with ICD-10, and compare reason codes against active conditions and encounter evidence. Check SBAR completeness by requiring `situation`, `background`, `assessment`, and `recommendation`.

## Normalization Rules

- Sort arrays marked as sets alphabetically or by the template's stated key. Preserve newest-to-oldest order for encounter lists when requested.
- Use active clinical records only for active condition, medication, and allergy key lists. Put inactive, stale, unrelated, or non-packet records only in explicit excluded/distractor fields.
- Treat final documents as usable evidence. Exclude chart-summary exports from identity or external-continuity evidence when the template asks for governance packet basis rather than general chart contents.
- Use `null` for absent scalar values where the schema permits null. Use empty arrays for absent sets.
- Validate ICD-10 codes by lookup. Mark unknown codes invalid. Mark wrong service-line chapters as out of range when the template defines an expected chapter.
- Compare diagnosis narratives with ICD expected terms. Flag laterality mismatches when left/right terms conflict, missing laterality when a laterality-required code has no side in the narrative, and narrative mismatches when the clinical concept differs.
- For referral document queues, classify missing authorization from `authorization_status`, missing records when required office notes are absent, and imaging follow-up when required imaging is absent, pending, or called out by the referral evidence.
- For batch audits, compute counts from the filtered referral rows after all exclusions and duplicate grouping rules have been applied.
- For duplicate groups, group same-patient resubmissions only when the batch evidence indicates resubmission or duplicate intent. Treat shared insurance across different patients as an anomaly, not proof of duplicate identity.
- For care-transition handoffs, select encounters that match the requested handoff purpose, signed state, specialty relevance, and recency window. Exclude later unrelated visits and stale records even if they are newer or share a diagnosis code.
- For disclosures, require the recipient provider or facility to match the requested recipient and require a permitted status unless the template asks to report blockers.
- For risk flags, derive flags from active conditions, active medications, active allergies, and encounter notes. Emit evidence arrays that support each emitted flag.

## Decision Patterns

- Duplicate merge ready: candidate is active/open or confirmed, strong identity match signals dominate, merge preview names a preferred target and source, and active charts do not contain hard conflicts. Use the preferred target as canonical target.
- Duplicate review hold: candidate status or evidence says needs review, target/source is absent, or material conflicts exist such as conflicting names, phones, DOBs, insurance, address, or opposite-laterality active problems.
- Do not merge: evidence clearly contradicts identity beyond a reviewable conflict.
- Referral ready to send: authorization is approved or not required, receiving provider resolves, code validates and matches narrative, required documents are present, and allergy/readiness fields are complete.
- Referral hold: choose the blocker that matches the strongest missing item: authorization, required documents, clinical/code mismatch, allergy clarification, or unresolved provider.
- ServiceRequest quality review: distinguish raw API fields from template-level normalized quality status. If a task describes a draft order but asks for validated governance output, classify status according to the template semantics after validating service code, performer, reason-code evidence, and SBAR completeness.
- Action tiers: put urgent coding defects and duplicate blockers in immediate tiers; routine coding, authorization, document, or clinical blockers in short-term tiers; purely administrative document completion in administrative tiers.

## Output Discipline

- Emit one valid JSON object and no prose.
- Match the template's top-level keys and nested object names exactly.
- Do not add fields not requested by the template.
- Prefer API IDs and normalized keys over narrative descriptions unless the schema asks for names or descriptions.
- Use enum strings exactly as listed in the template.
- Before finalizing, re-check sorting, required empty arrays, nullability, count consistency, and that every emitted ID is supported by queried evidence.
