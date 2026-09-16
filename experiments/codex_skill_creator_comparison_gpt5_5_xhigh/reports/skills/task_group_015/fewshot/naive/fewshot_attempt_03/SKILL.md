---
name: ehr-quality-packets
description: Solve EHR quality-governance tasks that require normalized JSON from a read-only task environment, including duplicate-chart merge readiness, referral coordination, care-transition packets, ServiceRequest quality review, ICD/service-code validation, and referral batch audits. Use when prompts mention an EHR/referral quality API, duplicate candidates, patient active lists, providers, disclosures, documents, audit logs, or answer templates for normalized packet output.
---

# EHR Quality Packets

## Core Workflow

1. Read the user prompt and the referenced answer template before fetching data. Treat the template as the exact output contract: preserve required top-level keys, enum strings, nullability, object shapes, and ordering notes.
2. Extract all explicit IDs from the prompt: patient, candidate, referral, batch, provider, and ServiceRequest IDs. Use the task environment base URL supplied by the prompt or environment file.
3. Fetch only read-only GET endpoints. Prefer exact detail endpoints when an ID is known, then fetch patient-scoped supporting data.
4. Build the answer from API evidence, not from prompt labels alone. When prompt wording conflicts with endpoint details, decide whether the template asks for raw source status or a normalized quality-review status.
5. Return JSON only. Do not include prose, comments, markdown fences, or fields not present in the template.

Useful fetch pattern:

```bash
BASE="${TASK_ENV_BASE_URL%/}"
curl -fsS "$BASE/api/referrals/<referral_id>" | jq .
curl -fsS "$BASE/api/patients/<patient_id>/conditions" | jq .
```

List endpoints in this environment usually return wrapper objects such as `{"patients":[...]}`, `{"referrals":[...]}`, `{"duplicate_candidates":[...]}`, and `{"providers":[...]}`.

## Endpoint Map

- Duplicate review: `/api/duplicates/{candidate_id}`, plus patient detail and active lists for every candidate patient.
- Patient packet: `/api/patients/{patient_id}`, `/conditions`, `/medications`, `/allergies`, `/encounters`, `/immunizations`, `/documents`, `/disclosures`, `/service-requests`.
- Referral packet or audit: `/api/referrals/{referral_id}` for a single referral; `/api/referrals` filtered by `batch_id` for batch audits.
- Evidence and directories: `/api/audit-logs`, `/api/providers/{provider_id}`, `/api/icd10/{code}`, `/api/service-codes/{code}`.

## General Normalization

- For active clinical lists, use patient-scoped active-list endpoints as authoritative. Filter records to `status == "active"` and emit `normalized_key` values, sorted alphabetically unless the template says otherwise.
- Do not rely on duplicate candidate preview lists alone. If asked for reconciliation, report active keys present in patient endpoints but missing from the preview.
- Sort set-like string arrays alphabetically. Sort object arrays by the template rule; otherwise use stable task-relevant order such as newest-to-oldest for selected encounters or ascending code/referral ID for audit findings.
- Use stable IDs in evidence arrays. Include documents, audit logs, disclosures, encounters, and providers only when their patient, recipient, type, status, date, and purpose match the packet.
- Exclude inactive, stale, cancelled, unrelated, wrong-patient, or wrong-recipient records unless the template explicitly asks for excluded distractors or risk evidence.

## Duplicate Merge Rules

- Use `match_signals`, `conflict_signals`, `patient_ids`, candidate `status`, and `merge_preview` target/source fields from the duplicate endpoint.
- A candidate with a preferred target/source, strong identity matches, and only non-blocking conflicts can be merge-ready. Choose the target from `preferred_target_patient_id` and source from `source_patient_id`; confirm against patient `canonical_status` and `canonical_patient_id` when available.
- A candidate with blocking demographic or clinical conflicts, missing target/source, or `status` indicating review should be held for manual review. Leave merge target/source null when the template allows nulls and no canonical pair is supported.
- Derive demographic match/conflict lists from patient detail comparisons: DOB, sex, phone, insurance, address normalization, PCP, given/family name variants, and explicit candidate signals.
- For merge packet evidence, include identity-review, external-continuity, and merge-relevant records. Exclude general chart summaries and unrelated audits/documents unless the template asks to list distractors.

## Referral Coordination

- Fetch referral detail, patient detail, active conditions/medications/allergies, encounters, documents, provider detail, and ICD-10 lookup for diagnosis codes.
- Active diagnoses should come from active conditions and any active referral-intake condition relevant to the referral narrative. Mark referral relevance by service line, referral code/narrative, and recent encounter diagnoses.
- Validate ICD codes through `/api/icd10/{code}`. Use the returned `chapter`, `expected_terms`, and `requires_laterality` to decide validity, service-line chapter fit, narrative match, laterality mismatch, narrative mismatch, or missing laterality.
- Allergy readiness is complete when active allergy details needed by the template are documented with allergen, reaction, severity, status, and source. If allergies are absent, incomplete, conflicting, or entered in error, use the corresponding readiness and blocker enum.
- Required document evidence must match both document type and usable status. Prefer final documents; treat missing, preliminary, cancelled, or absent required types as blockers.
- Medication highlights should include active referral-relevant medications first, then only additional active medications if the template asks for them. Use medication name, dose, route, frequency, status, and a normalized highlight reason.
- Overall readiness is blocked by authorization, missing required documents, incomplete allergy documentation, missing provider, invalid code, or clinical mismatch according to the template enums.

## Care Transition Packets

- Fetch patient, recipient provider, active lists, encounters, immunizations, disclosures, and documents if requested.
- Select handoff encounters by the stated service line and transition window. Prefer care-transition and recent signed/amended encounters relevant to the receiving specialty; order selected encounters newest to oldest.
- Track excluded encounter IDs when the template asks for source selection. Exclude stale, outside-window, duplicate, unsigned/draft if not acceptable, and unrelated encounters.
- Pick the latest immunization by date unless the template names a vaccine type.
- A disclosure is usable only when it names the patient, recipient provider or facility, permitted status, and matching purpose. Missing or non-permitted disclosure is a readiness blocker.
- Risk flags must be backed by active conditions, active medications, allergies, or encounter notes. Common mappings:
  - diabetes plus insulin medication implies insulin-dependent diabetes and perioperative glucose planning.
  - hypertension condition implies hypertension risk.
  - memory/cognitive condition or note implies cognitive-memory-loss risk.
  - orthopedic lower-extremity issues plus pain medication or fall note implies fall-risk note required.
  - active latex allergy implies latex-allergy risk.

## ServiceRequest Review

- Fetch patient-scoped service requests and select the object by `service_request_id`.
- Validate `service_code` with `/api/service-codes/{code}`. `service_code_valid` is true only when the code exists, is active, and matches the performer service line.
- Resolve requester and performer providers through the provider directory. Emit performer service line from the provider record.
- Validate every reason code with `/api/icd10/{code}` and compare against active conditions, encounter diagnoses, service line, and narrative/SBAR evidence.
- SBAR coverage is complete only when situation, background, assessment, and recommendation are all present and non-empty.
- If the template asks for quality-review output rather than raw source echo, normalize a draft request that has order intent, complete SBAR, valid service code, valid performer, and matching reason evidence as operationally ready/active; otherwise preserve the raw status.

## Referral Batch Audits

- Fetch `/api/referrals`, filter exactly by `batch_id`, then compute every count from the filtered rows.
- `record_count` is referral rows; `unique_patient_count` is distinct patient IDs.
- For each referral, look up the ICD code. Flag unknown codes and codes whose chapter does not match the expected service-line chapter. For orthopedics, the expected chapter is typically Musculoskeletal unless the template says otherwise.
- Compare referral narrative to ICD `expected_terms`. Flag `laterality_mismatch` when left/right conflicts, `missing_laterality` when the code requires laterality and the narrative omits it, and `narrative_mismatch` when the clinical concept does not match.
- Duplicate groups are same-patient resubmissions within the audited batch for the same service line/clinical request. Sort group referral IDs and apply the template disposition.
- Insurance anomalies are shared insurance across different patient IDs within relevant referrals; do not infer a merge from shared insurance alone.
- Follow-up queues come directly from referral blockers:
  - missing authorization -> authorization-missing queue.
  - pending authorization -> authorization-pending queue.
  - missing office note -> records-request queue.
  - missing or pending imaging required for the service line/request -> imaging-follow-up queue.
- Tier action plans should be mutually exclusive:
  - Tier 1: urgent referrals with coding blockers or duplicate blockers, plus duplicate-group rows when the template tiers all duplicate rows as blockers.
  - Tier 2: routine coding, authorization, or clinical-document blockers.
  - Tier 3: administrative document completion when no coding/auth/duplicate blocker drives a higher tier.
- Summary counts must equal the emitted arrays and queues, not a separate estimate.
