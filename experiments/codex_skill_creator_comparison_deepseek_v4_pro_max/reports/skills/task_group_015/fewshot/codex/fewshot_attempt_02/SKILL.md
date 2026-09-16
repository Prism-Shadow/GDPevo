---
name: ehr-quality-governance
description: Prepare normalized EHR quality-governance JSON packets against a simulated read-only FHIR-like API. Use when the task involves duplicate merge readiness, referral coordination, care transition packets, duplicate review with ServiceRequest validation, or batch referral audits. The skill covers the full endpoint catalog, ICD-10 validation, duplicate detection, clinical list normalization, document/audit evidence selection, provider directory lookups, and standardized output conventions (sorted arrays, enum values, normalized keys).
---

# EHR Quality Governance

## Overview

This skill covers preparing normalized JSON packets for EHR quality-governance workflows against a simulated read-only FHIR-like API at the URL provided in the task prompt as `<TASK_ENV_BASE_URL>`.
The five task families are:

1. **Duplicate merge readiness** — verify duplicate candidates, build canonical merge targets, compute clinical-key unions, identify evidence IDs, and produce a merge packet.
2. **Referral coordination** — reconcile a referral against the active chart, validate ICD-10 codes, assess allergy/documentation/authorization readiness, and select normalized referral-letter field values.
3. **Care transition handoff** — assemble active clinical lists, select recent handoff encounters, identify the latest immunization and applicable disclosure, flag risks, and assess packet readiness.
4. **Duplicate review + ServiceRequest validation** — evaluate a duplicate candidate, validate the SBAR coverage and quality signals of a draft ServiceRequest.
5. **Batch referral audit** — scan a referral batch for invalid/out-of-range codes, laterality/narrative mismatches, duplicate groups, insurance anomalies, and assign tiered action plans.

## General Methodology

### Step 1: Identify the task type and output shape

Read the task prompt and the answer template in `input/payloads/answer_template.json`. The template defines every required top-level key, array ordering, enum constraint, and nested structure. The answer must conform exactly — no extra keys, no prose outside the JSON object.

### Step 2: Gather evidence from the API

Consult [references/api_endpoints.md](references/api_endpoints.md) for the full endpoint catalog and request patterns. Every query targets `<TASK_ENV_BASE_URL>`.

Parallelize independent reads: fetch the primary record (patient, referral, duplicate candidate, etc.), then its sub-collections (conditions, medications, allergies, encounters, documents), then supporting records (providers, ICD-10 codes, audit logs) in parallel batches.

### Step 3: Normalize and cross-reference

All clinical items (conditions, medications, allergies) produce a `normalized_key` — a lowercase, snake_case identifier derived from the item's code or description, stripped of whitespace. See [references/domain_patterns.md](references/domain_patterns.md) for the derivation rules and known key catalog.

ICD-10 codes are validated by cross-referencing the `/api/icd10/{code}` endpoint: check that the code exists (not 404), that its chapter matches the service line expectation, and that the code narrative matches patient evidence.

Duplicate candidates are evaluated by comparing demographic fields (DOB, insurance, phone, address, name, sex) between the two patients. Match signals, conflict signals, and the merge disposition follow the rules in [references/domain_patterns.md](references/domain_patterns.md).

### Step 4: Apply domain-specific policies

Each task type has specific policies documented in [references/domain_patterns.md](references/domain_patterns.md):

- **Document selection**: only identity or external-continuity documents belong in evidence; exclude chart summaries.
- **Encounter selection**: for handoffs, select the N most recent relevant encounters within the surgical/referral window; exclude stale or unrelated encounters.
- **Duplicate tiering**: all rows in a duplicate group are assigned to the duplicate-blocker tier.
- **Insurance anomalies**: shared insurance across different patients triggers verification, not a merge.
- **Risk flag derivation**: map active conditions, medications, and encounters to standardized risk flags.

### Step 5: Produce the normalized JSON

Emit a single JSON object. Follow these conventions without exception:

- **Arrays labeled as sets** are sorted alphabetically (ascending) by string value.
- **Encounter arrays** are sorted newest-to-oldest by date.
- **ID arrays** inside objects are sorted ascending.
- **Referral objects** inside arrays are sorted by `referral_id` ascending.
- **Dates** use YYYY-MM-DD.
- **Enum values** must match exactly the allowed values in the template — no aliases, no abbreviations.
- **null** is used only for genuinely absent values; do not emit empty strings as placeholders.
- **Keys with no matching evidence** are emitted as empty arrays `[]`, not omitted.

## Task-Specific Workflows

### Duplicate Merge Readiness Packet

1. Fetch the duplicate candidate via `GET /api/duplicates/{candidate_id}`.
2. Fetch both patients via `GET /api/patients/{patient_id}`.
3. For each patient, fetch conditions, medications, allergies, documents, encounters (in parallel).
4. Query audit logs via `GET /api/audit-logs` and filter to the relevant patient/merge IDs.
5. Determine the merge target (the canonical/active record) and source (the duplicate shell).
6. Compute clinical-key unions from active records only. Do not include inactive records or distractors.
7. Compare demographics for match/conflict signals per [references/domain_patterns.md](references/domain_patterns.md).
8. Select evidence document IDs (identity/external-continuity only) and audit IDs (merge-related only).
9. Identify the specialist provider from document origin and the PCP from patient demographics.
10. Determine packet readiness: ready if all required evidence present; ready_with_review_note if minor ambiguities; blocked if critical data missing.

### Referral Coordination Packet

1. Fetch referral detail via `GET /api/referrals/{referral_id}`.
2. Fetch the patient and all sub-collections (conditions, medications, allergies, encounters, documents).
3. Cross-reference each active diagnosis against the ICD-10 directory via `GET /api/icd10/{code}`.
4. Identify the primary and supporting codes for the referral code set.
5. Assess allergy readiness from active allergy records and the referral form.
6. Identify the most recent relevant encounter (the one that triggered or relates to the referral).
7. Check for required documents (echo, office note) and note missing ones.
8. Look up the receiving provider via `GET /api/providers/{provider_id}`.
9. Determine authorization status and overall readiness.
10. Select referral-letter field values per [references/domain_patterns.md](references/domain_patterns.md).

### Care Transition Handoff Packet

1. Fetch the patient detail and all sub-collections.
2. Fetch the recipient provider via `GET /api/providers/{provider_id}`.
3. Extract active condition/medication/allergy keys.
4. Select the N most recent handoff-relevant encounters (typically 4, newest first); exclude stale or unrelated ones.
5. Identify the latest immunization by date across all immunization records.
6. Find the disclosure matching the recipient provider with permitted status.
7. Derive risk flags from active conditions, medications, and encounters per [references/domain_patterns.md](references/domain_patterns.md).
8. Build risk-flag evidence objects linking each flag to its supporting condition/medication/encounter IDs.
9. Set readiness: `ready` if no flags; `ready_with_risk_flags` if flags present but no blockers; `not_ready` if blocking issues.

### Duplicate Review + ServiceRequest Validation

1. Fetch the duplicate candidate, both patients, and their demographics.
2. Fetch the ServiceRequest via the patient's service-requests endpoint (or by ID if available).
3. Validate the ServiceRequest: status, intent, priority, service code validity via `/api/service-codes/{code}`, performer service line, reason codes via ICD-10 lookup.
4. Assess SBAR coverage: check whether the ServiceRequest contains situation, background, assessment, and recommendation sections.
5. Evaluate the duplicate: compare demographics for match/conflict signals as a set.
6. Return the composite JSON.

### Batch Referral Audit

1. Fetch all referrals via `GET /api/referrals` and filter to the target batch (by batch_id or date range).
2. For each referral in the batch, fetch patient detail and ICD-10 code detail in parallel.
3. Classify invalid/out-of-range referrals: codes whose ICD-10 chapter is not Musculoskeletal for orthopedics batches (or mismatched for other service lines).
4. Classify laterality/narrative mismatches: compare the referral's diagnosis narrative against the ICD-10 code description and expected terms.
5. Detect duplicate groups: same patient_id appearing in multiple referral rows.
6. Detect insurance anomalies: same insurance_id shared across different patient_ids.
7. Build follow-up queues: authorization_missing, authorization_pending, records_request, imaging_follow_up.
8. Assign tiered action plan: Tier 1 for urgent coding/duplicate blockers, Tier 2 for routine coding/auth/document issues, Tier 3 for administrative document completion.
9. Compute summary counts from the audit findings.

## Key Resources

- [references/api_endpoints.md](references/api_endpoints.md) — Full endpoint catalog with URLs, parameters, response shapes, and query patterns.
- [references/domain_patterns.md](references/domain_patterns.md) — Reusable domain rules: normalized keys, identity signals, clinical unions, ICD-10 validation, document selection, risk flags, duplicate handling, and sorting conventions.
