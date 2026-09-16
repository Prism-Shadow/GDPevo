---
name: ehr-quality-packets
description: Build normalized JSON for EHR quality-governance tasks that provide a TASK_ENV_BASE_URL and an answer_template. Use for duplicate merge readiness packets, referral coordination packets, care transition handoffs, ServiceRequest/SBAR validation, and referral batch audits that require reading patient, referral, duplicate-candidate, provider, ICD-10, service-code, document, audit, disclosure, immunization, encounter, condition, medication, and allergy endpoints.
---

# EHR Quality Packets

Use this skill to solve EHR quality-governance tasks that require a single normalized JSON response from a read-only task API.

## Workflow

1. Read the user prompt and `input/payloads/answer_template.json` first. Treat the template as the output contract: preserve required top-level keys, field names, types, enum spelling, nullability, and ordering notes. Do not include template metadata fields such as `description`, `schema`, `types`, or ordering annotations unless the template explicitly requires them in the final object.
2. Resolve `<TASK_ENV_BASE_URL>` from the task prompt, environment variable, or `environment_access.md` if present. Use only the public task API endpoints needed for the case.
3. Fetch evidence for every ID and batch named in the prompt. Also fetch dependent records referenced by those records, especially patient active lists, providers, ICD-10 entries, service-code entries, documents, encounters, disclosures, immunizations, and audit logs when the requested packet asks for them.
4. Reconcile each answer field against primary evidence, not just summary records. Patient active-list endpoints are authoritative for active conditions, medications, and allergies; duplicate previews and referral rows are starting points to cross-check.
5. Emit JSON only. Use stable IDs and normalized codes rather than narrative explanations. Sort arrays exactly as the template says; if it says a list is a set and gives no special order, sort strings alphabetically/ascending and objects by the ID or code field named in the template.
6. Validate before final: parse with `python3 -m json.tool`, compare keys against the template, verify every enum value is allowed, and check that no explanatory prose surrounds the JSON.

## Context Helper

Use `scripts/fetch_ehr_context.py` to collect task-local API evidence into one JSON file:

```bash
python3 scripts/fetch_ehr_context.py \
  --base-url "$TASK_ENV_BASE_URL" \
  --prompt input/prompt.txt \
  --template input/payloads/answer_template.json \
  --include-audit-logs \
  > /tmp/ehr_context.json
```

Pass explicit IDs when prompt parsing is insufficient:

```bash
python3 scripts/fetch_ehr_context.py --base-url "$TASK_ENV_BASE_URL" \
  --patient P-... --referral REF-... --duplicate DUP-... \
  --provider PRV-... --service-request SR-... --batch BATCH-ID \
  > /tmp/ehr_context.json
```

The helper does not make decisions. It fetches raw records, dependent records, ICD/service-code lookups, and warnings/errors so you can reason from complete evidence.

## General Normalization Rules

- Prefer endpoint status fields over inferred status. Include inactive, stale, preliminary, draft, denied, pending, or unrelated records only in fields that explicitly ask for exclusions, blockers, or reviewed-but-excluded evidence.
- Normalize active clinical list outputs to `normalized_key` strings from active records. Exclude inactive and entered-in-error records unless the template asks for distractors.
- When two sources disagree about active lists, use patient active-list endpoints as authoritative and record any keys added beyond summary/preview sources in reconciliation fields.
- Use provider-directory detail records for provider name, role, service line, facility, phone, and fax. Inline patient/referral provider snapshots can identify which provider to fetch.
- Use ICD-10 lookup records to validate diagnosis/reason codes, chapters, and expected terms. Use service-code lookup records to validate service codes and performer service lines.
- For date comparisons, parse `YYYY-MM-DD` lexicographically only after confirming all dates use that format. Newest means the greatest date.
- Preserve template nulls where evidence is missing and null is allowed. Use empty arrays for absent set fields unless the template specifies null.

## Duplicate Review And Merge Packets

- Fetch the duplicate candidate, both patient details, both active clinical lists, relevant patient documents, audit logs, and providers referenced by patient or packet requirements.
- Determine merge target/source from explicit candidate preview fields first. If absent, use patient canonical status and duplicate-shell pointers; do not invent target/source when conflicts or missing preview fields require review.
- Treat strong identity matches as same DOB, phone, insurance, normalized address/name variants, same PCP, sex, or shared external continuity evidence. Treat conflicts as different DOB/insurance/phone/address, incompatible name differences, laterality conflicts, or other explicit candidate conflict signals.
- Ready-to-merge dispositions require an active/open duplicate candidate, clear target/source, strong identity support, and no material conflicts requiring manual review. Otherwise choose the template's review-hold/manual-review disposition and set merge target/source to null when no canonical direction is supported.
- Clinical unions are the sorted union of active condition, medication, and allergy normalized keys from both patients' active endpoints. Reconciliation "added from active endpoints" fields are active endpoint keys missing from the duplicate preview.
- Packet evidence documents should be identity, merge, or external continuity records relevant to the duplicate decision. Exclude unrelated chart summaries and stale/non-final distractors unless requested as exclusions.

## Referral Coordination Packets

- Fetch referral detail, patient detail, active conditions/medications/allergies, recent encounters, patient documents, receiving provider, and ICD-10 lookups for referral and active diagnosis codes.
- Active diagnoses should combine active problem-list conditions with referral-intake diagnosis/symptom codes when the template expects both chart and referral evidence. Mark referral relevance by matching the service-line narrative, referral reason, recent encounter plan, or required diagnosis set.
- Choose primary and supporting diagnosis codes from the referral's intended clinical narrative, active chart evidence, and ICD validation. A symptom code is usually supporting when a disease code explains the referral.
- Allergy readiness is complete only when active allergy evidence has allergen, reaction, severity/status, and a trusted source. Use the template's incomplete/conflicting/no-known status when evidence is absent or inconsistent.
- Required document evidence must honor document type and finality. Missing required documents, pending/preliminary imaging, missing authorization, provider gaps, invalid diagnosis codes, and allergy ambiguity become blocking issues according to the template.
- Medication highlights should include referral-relevant active medications first, then any required supporting active medications. Use exact medication, dose, route, frequency, status, and a normalized highlight reason supported by the active medication list or recent encounter.
- Referral-letter choice fields are controlled-enum summaries of the evidence. Select the enum that matches all supporting evidence; use the generic/hold/other enum only when the exact option is not fully supported.

## Care Transition Packets

- Fetch patient detail, recipient provider, active clinical lists, encounters, immunizations, disclosures, documents if requested, and any encounter evidence needed for risk flags.
- Handoff encounters should be recent, relevant to the destination service line or transition purpose, and ordered newest-to-oldest unless the template states otherwise. Exclude stale, unrelated, draft-only, or outside-window encounters in the source-selection exclusion field when requested.
- Latest immunization is the newest immunization record by date, not the newest encounter mentioning a vaccine.
- Disclosure must match the recipient/provider or destination service, purpose, and permitted status. A missing, expired, denied, or wrong-recipient disclosure blocks readiness when the template lists disclosure blockers.
- Risk flags must be evidence-backed by active condition keys, medication keys, allergy keys when the schema supports them, and encounter IDs. Sort risk-flag evidence by risk flag and sort each evidence ID/key list.
- Packet readiness is ready with risk flags when all required records are present and permitted but non-blocking risks must be surfaced.

## ServiceRequest And SBAR Validation

- Fetch the ServiceRequest from the patient's service-request endpoint, requester/performer providers, the service-code lookup, ICD-10 lookups for all reason codes, patient active conditions, and relevant encounters.
- Validate ServiceRequest status, intent, priority, authored/occurrence dates, requester, performer, service line, and service code directly from the ServiceRequest and lookup records.
- A service code is valid only when the lookup exists, is active, and matches the requested service line/order kind.
- Reason-code validation requires the ICD-10 lookup to exist and the code's chapter/narrative to match patient evidence, referral/service reason, or encounter documentation.
- SBAR coverage is complete only when situation, background, assessment, and recommendation are all present in the relevant note/request evidence.

## Referral Batch Audits

- Fetch all referrals for the requested batch, then fetch patient/provider/ICD/service-code evidence as needed. Compute counts from the audited rows, not from filtered issue lists.
- Invalid or out-of-range code referrals include unknown ICD codes and valid ICD codes whose chapter is outside the expected service-line chapter. For orthopedics, the expected chapter is musculoskeletal unless the template states a different expectation.
- Laterality/narrative mismatches come from comparing referral diagnosis narrative to ICD expected terms and laterality. Use `laterality_mismatch` for opposite-sided evidence, `missing_laterality` when the code expects a side but the narrative omits it, and `narrative_mismatch` when the body part/problem does not match.
- Duplicate groups are same-patient resubmissions for the same clinical referral context. When the template defines all duplicate group rows as blockers, tier every referral ID in the group as a duplicate blocker, including the original row.
- Shared insurance across distinct patients is an insurance/patient anomaly, not automatic merge evidence. Classify it separately from same-patient duplicate referrals.
- Follow-up queues should be direct set membership from evidence: missing authorization, pending authorization, missing office note/records, and missing or pending imaging required by the service line.
- Tier 1 is for urgent coding issues or duplicate blockers. Tier 2 is for routine coding, authorization, or clinical/document blockers. Tier 3 is for administrative document completion without higher-priority blockers. Ready/no-follow-up referrals have no audit issues.
