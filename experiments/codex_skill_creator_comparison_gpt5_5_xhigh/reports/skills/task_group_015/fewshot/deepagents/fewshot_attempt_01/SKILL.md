---
name: ehr-quality-json-packets
description: Create normalized JSON packets for EHR quality-governance tasks that require querying a read-only task API. Use for duplicate chart merge readiness, referral coordination, care transition handoff packets, ServiceRequest quality checks, ICD-10 and service-code validation, and referral batch audits where the prompt provides an answer_template.json and IDs such as patient, referral, duplicate candidate, provider, ServiceRequest, or batch identifiers.
---

# EHR Quality JSON Packets

## Core Workflow

1. Read the prompt and `input/payloads/answer_template.json` before querying.
2. Extract all identifiers from the prompt and payloads: patient IDs, duplicate candidate IDs, referral IDs, ServiceRequest IDs, provider IDs, batch IDs, requested service line, requested recipient, and required output sections.
3. Query the task API for direct records and supporting evidence. Use `scripts/ehr_quality_fetch.py` when it helps collect a bundle quickly, or use `curl`/Python directly.
4. Build the answer from live API evidence and the template only. Do not use memorized train-case values, hidden assumptions, or narrative explanations outside JSON.
5. Conform exactly to the requested schema. Preserve required keys, enum strings, booleans, nullability, and date format. Sort arrays whenever the template says set semantics, sorted ascending, or stable ordering.
6. Before finalizing, recompute all summary counts and readiness fields from the emitted arrays and blocking issues.

## API Collection

Use the base URL supplied by the task prompt or environment. The helper accepts `--base-url`; otherwise set `TASK_ENV_BASE_URL`.

```bash
python skill/scripts/ehr_quality_fetch.py --base-url "$TASK_ENV_BASE_URL" \
  --patient PATIENT_ID --referral REFERRAL_ID --candidate CANDIDATE_ID \
  --service-request SERVICE_REQUEST_ID --provider PROVIDER_ID --batch BATCH_ID \
  --out /tmp/ehr_bundle.json
```

Useful endpoint families:

- Patient detail and active lists: `/api/patients/{id}`, `/conditions`, `/medications`, `/allergies`
- Patient context: `/encounters`, `/immunizations`, `/documents`, `/service-requests`, `/disclosures`
- Queue objects: `/api/duplicates/{candidate_id}`, `/api/referrals/{referral_id}`, `/api/referrals`, `/api/audit-logs`
- Directories: `/api/providers/{provider_id}`, `/api/icd10/{code}`, `/api/service-codes/{code}`

If a list endpoint ignores query parameters, fetch the list and filter client-side by exact `batch_id`, `patient_id`, or ID fields.

## Normalization Rules

- Active clinical keys come from patient active-list endpoints, not duplicate previews or summaries. Include records whose status is active or clearly current; exclude inactive, entered-in-error, stale, unrelated, and distractor records.
- For duplicate merge packets, reconcile preview keys against both patients' active endpoints. Emit keys added from active endpoints when the preview omits active evidence.
- Use `normalized_key` for condition, medication, and allergy unions. Sort string sets alphabetically unless the template requires chronological or code order.
- Treat answer-template object arrays as sets only when the template says so. Otherwise preserve its specified ordering, commonly newest-to-oldest dates, code ascending, referral_id ascending, or risk_flag ascending.
- Prefer stable IDs over narrative text in evidence fields. Use document IDs, audit IDs, encounter IDs, disclosure IDs, provider IDs, referral IDs, and codes from the API.
- Select only evidence relevant to the requested packet. Do not include unrelated chart summaries, inactive clinical items, stale handoff encounters, or records for other patients unless the template explicitly asks for excluded distractors or anomalies.

## Duplicate Review And Merge Packets

Collect the duplicate candidate, both patient records, active lists, documents, audit logs, and relevant providers.

- Use candidate `match_signals` and `conflict_signals` directly when available, sorted as requested.
- Compare patient demographics for requested match/conflict fields: date of birth, phone, insurance, sex, primary care provider, address, and name variants. Normalize minor spelling/address variants into the labels requested by the template.
- Choose a canonical merge target only when the candidate and patient evidence support a merge. Strong merge-ready signals include an open or confirmed candidate, a candidate preferred target/source, matching core identity signals, and no hard demographic or clinical conflict.
- Put the active canonical chart or candidate preferred target as target, and the duplicate shell/source as source. If hard conflicts remain, emit the template's review-hold disposition and leave merge target/source null when required.
- Use active-list endpoint unions for clinical preservation. Preview values are supporting evidence, not authoritative.
- Merge-packet document evidence should be identity, external continuity, duplicate-review, or merge-governance documents. Exclude unrelated chart summaries and documents for other cases.
- Audit evidence should be candidate-specific duplicate, merge, review, or source-target audit records. Exclude unrelated audit IDs unless the schema asks for distractors.
- Specialist contact should come from the receiving specialist, external continuity document provider, or requested service line. Primary care contact comes from the patient PCP field when requested.

## Referral Coordination Packets

Collect referral detail, patient detail, active conditions/medications/allergies, recent encounters, documents, receiving provider, ICD-10 lookup for diagnosis and supporting codes, and any authorization/document fields.

- Active diagnoses should include active condition records and referral-intake diagnoses that the referral relies on. Mark `referral_relevant` true when the condition/code matches the referral diagnosis, narrative, encounter care plan, or service line.
- Validate the primary diagnosis with `/api/icd10/{code}`. Use the ICD chapter and expected terms to decide whether the code matches the narrative and service line.
- Supporting codes usually come from referral-relevant symptoms or encounter diagnoses tied to the same referral narrative.
- Allergy readiness is complete when active/referral allergies include allergen, reaction, severity, and status with no unresolved conflict. Use incomplete or conflicting statuses when details are missing, inactive/active records disagree, or the referral note asks for clarification.
- Select the most recent signed or amended encounter that directly supports the referral narrative, not merely the latest visit. Capture diagnosis codes, mentioned medications, and the requested care-plan tag.
- Required document evidence depends on service line and template. For cardiology, check final echo plus office note when requested. For orthopedics, common records are office note, imaging, xray, MRI, or physical therapy note as named by the task/template.
- Authorization readiness blocks sending for missing/denied/pending authorization, missing required documents, incomplete allergies, missing provider, invalid code, or clinical mismatch according to the template enum names.
- Medication highlights should include active medications relevant to the referral service and diagnosis before generic active meds. Examples of reusable mappings: diuretics for heart failure, ACE/ARB or antihypertensives for blood pressure, insulin for diabetes/perioperative planning, analgesics or anti-inflammatories for orthopedic pain when requested.
- For template choice fields, choose the most specific enum matching the evidence. Do not invent enum strings; if none fits, use the template's generic `other`, unresolved, hold, or incomplete option.

## Care Transition Packets

Collect patient, recipient provider, active lists, encounters, immunizations, disclosures, documents if requested, and provider directory details.

- Patient and recipient sections should be copied from API detail records, with service line from the provider directory.
- Handoff encounters should be clinically relevant to the requested transition and sorted newest to oldest. Prefer signed/amended care-transition, pre-op, surgical handoff, or specialty-relevant office visits in the requested window. Exclude stale, unrelated, outside-window, or wrong-specialty encounters, but keep them available as risk evidence if the template asks.
- Latest immunization means the newest valid immunization record by date unless the template names a vaccine type.
- Disclosure must match the requested recipient/provider, purpose, and status. A non-permitted, missing, denied, pending, or expired disclosure is a readiness blocker when disclosure is required.
- Infer risk flags from active evidence and relevant encounters:
  - cognitive or memory-loss condition or note -> cognitive memory-loss flag
  - active hypertension condition -> hypertension flag
  - diabetes plus active insulin -> insulin-dependent diabetes flag
  - perioperative or surgery note plus diabetes/insulin -> perioperative glucose-plan flag
  - latex active allergy -> latex-allergy flag
  - orthopedic mobility/fall note, hip/knee osteoarthritis, or analgesic evidence -> fall-risk note flag when the template allows it
- Risk evidence should cite only active condition keys, active medication keys, and encounter IDs that substantiate each emitted flag. Sort by risk flag.
- Packet readiness is `ready` when required patient, recipient, active lists, handoff encounters, immunization, and disclosure are present with no risk flags or blockers; `ready_with_risk_flags` when sendable but flags are present; otherwise `not_ready`.

## ServiceRequest Quality Checks

Collect the ServiceRequest from the patient service-request endpoint, patient evidence, requester/performer providers, service-code lookup, ICD-10 lookups, and relevant encounters or conditions.

- If the prompt names a ServiceRequest ID, search the named patient's service-request list and select the exact ID.
- Normalize ServiceRequest status from API evidence. If surrounding quality evidence indicates the draft was activated or corrected, use the current authoritative API field required by the template.
- Validate service code through `/api/service-codes/{code}` and confirm its service line matches the performer and requested specialty.
- Validate each reason code with `/api/icd10/{code}`. Emit validity, chapter, and whether it matches patient evidence from active conditions, encounters, diagnosis narrative, and laterality.
- SBAR coverage is complete only when situation, background, assessment, and recommendation are all present and non-empty.

## Referral Batch Audits

Collect all referrals for the batch, then collect ICD-10, patient, and provider records needed to validate every row.

- Batch counts: `record_count` is referral rows in the batch; `unique_patient_count` is distinct patient IDs.
- For service-line chapter checks, compare ICD chapter with the template's expected chapter. Unknown lookup -> `unknown_code`; valid code in a wrong chapter -> `out_of_range_chapter`.
- Narrative/laterality mismatch:
  - Use ICD expected terms and diagnosis description to identify body part, condition, and laterality.
  - Emit `laterality_mismatch` when left/right conflicts.
  - Emit `missing_laterality` when the code is lateralized but narrative omits side.
  - Emit `narrative_mismatch` when body part or condition differs even if laterality is absent.
- Duplicate groups are same-patient resubmissions for the same service line and clinical request. Sort group IDs and referral IDs. When the template's policy says all duplicate rows are blockers, place every referral in the group into the duplicate-blocker list.
- Insurance/patient anomalies are not merge instructions. Shared insurance across different patients should be flagged for membership verification; same-patient separate clinical referrals should stay separate when diagnosis/request evidence differs.
- Follow-up queues come directly from referral status fields and documents received:
  - authorization missing -> missing auth queue
  - authorization pending -> pending auth queue
  - missing required office note -> records request
  - missing or pending required imaging -> imaging follow-up
- Action tiers:
  - Tier 1: urgent referrals with coding/clinical blockers, or duplicate-blocker rows.
  - Tier 2: routine coding, authorization, clinical, or document blockers.
  - Tier 3: administrative document completion without coding/clinical urgency.
  - Ready/no-follow-up rows have no invalid code, mismatch, duplicate blocker, anomaly needing action, auth blocker, records request, or imaging follow-up.
- Summary counts must equal the arrays and queues in the final JSON. Recount after sorting and before final output.

## Final JSON Check

Validate the answer as JSON before responding.

```bash
python -m json.tool /tmp/response.json >/dev/null
```

Return only the normalized JSON object. Do not include Markdown fences, comments, provenance notes, or unused keys.
