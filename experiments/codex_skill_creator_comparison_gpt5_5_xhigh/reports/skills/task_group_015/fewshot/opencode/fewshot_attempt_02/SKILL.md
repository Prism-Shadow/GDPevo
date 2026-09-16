---
name: ehr-quality-packet
description: Build normalized JSON packets from a read-only EHR quality/referral API. Use this skill whenever the user asks for an EHR duplicate-chart merge packet, referral coordination packet, orthopedic/cardiology referral audit, care-transition handoff packet, ServiceRequest quality review, ICD/provider/document evidence reconciliation, or any task that references TASK_ENV_BASE_URL and an answer_template.json schema.
---

# EHR Quality Packet

Use this skill to produce schema-conformant JSON from the task prompt, local payload templates, and the read-only EHR API. The expected answer is evidence-derived; do not reuse memorized example values.

## Core Workflow

1. Read the user prompt and every local payload file, especially `input/payloads/answer_template.json`.
2. Extract stable identifiers from the prompt and payloads: patient IDs, duplicate candidate IDs, referral IDs, batch IDs, ServiceRequest IDs, provider IDs, service line, and requested packet type.
3. Read `environment_access.md` only to get the base URL and allowed endpoint list. Query only the listed API endpoints.
4. Gather complete evidence before filling the template. Prefer endpoint data over prompt prose when they conflict, except when the template asks for a normalized recommendation rather than the raw record.
5. Fill exactly the top-level keys and field types requested by the template. Return JSON only, with no notes or Markdown.
6. Sort set-like arrays lexicographically unless the template defines a specific order. Preserve special ordering rules such as newest-to-oldest encounters, referral objects by `referral_id`, or risk evidence by `risk_flag`.

Use [`scripts/ehr_collect.py`](scripts/ehr_collect.py) when useful to collect the common evidence bundle:

```bash
python3 /path/to/skill/scripts/ehr_collect.py \
  --base-url "$TASK_ENV_BASE_URL" \
  --patient PATIENT_ID \
  --referral REFERRAL_ID \
  --duplicate CANDIDATE_ID \
  --batch BATCH_ID \
  --service-request SERVICE_REQUEST_ID \
  --provider PROVIDER_ID \
  --output evidence.json
```

The helper only fetches and filters evidence; you still need to apply the template and task-specific normalization rules below.

## API Evidence Rules

- Patient detail: `GET /api/patients/{patient_id}` for demographics, MRN, canonical status, PCP ID, and embedded PCP contact.
- Active clinical lists: fetch `/conditions`, `/medications`, and `/allergies` for each relevant patient. Use records with `status == "active"` for active-list keys and medication/allergy details.
- Encounters, documents, immunizations, disclosures, and service requests are patient-scoped. Fetch them from the patient endpoint family and then filter by the task's IDs, dates, service line, recipient, and narrative.
- Referrals: fetch a single referral with `/api/referrals/{referral_id}`. For batch audits, fetch `/api/referrals` and filter client-side by `batch_id`; do not assume query parameters filter the response.
- Duplicate candidates: fetch `/api/duplicates/{candidate_id}` and then fetch all patient-scoped resources for every listed patient ID. Treat the duplicate preview as a starting point, not as the authoritative active clinical list.
- Directory/code validation: use `/api/providers/{provider_id}`, `/api/service-codes/{code}`, and `/api/icd10/{code}` for contact fields, service-line validation, ICD chapter, expected terms, and laterality requirements.
- Audit logs: fetch `/api/audit-logs` and filter to patient IDs, candidate IDs, merge/import/identity events, or summaries relevant to the packet.

## Duplicate Review And Merge Packets

- Use the duplicate candidate's `match_signals`, `conflict_signals`, `patient_ids`, `status`, and `merge_preview`.
- Choose merge target/source from `merge_preview.preferred_target_patient_id` and `merge_preview.source_patient_id` only when present and supported by patient canonical status. If either is null, or candidate status/conflicts indicate unresolved identity or clinical disagreement, emit a manual-review or review-hold disposition according to the template enums.
- Build active condition/medication/allergy unions from the patient active-list endpoints across both records. Include each active `normalized_key` once, sorted. Compute "added from active endpoints" as endpoint active keys minus the duplicate preview keys.
- Compare demographics for exact matches and conflicts: DOB, sex, phone, insurance ID, PCP ID, given/family-name variants, and address normalization. Keep candidate-provided signals, but do not invent unsupported conflict labels.
- Select merge packet documents narrowly. Prefer final identity, external continuity, specialist, or merge-review documents. Exclude generic chart summaries and unrelated patient documents when the template asks for distractors or an explicit selection policy.
- Select audit evidence narrowly from identity review, external import, duplicate review, and merge-related events for the involved records.
- Provider contact should come from the provider directory or embedded PCP object, not from free-text notes.

## Referral Coordination Packets

- Reconcile the referral detail with the active chart. Include active problem-list diagnoses and any referral-intake diagnosis required by the template when it is clinically relevant.
- Validate diagnosis codes through `/api/icd10/{code}`. Use the ICD chapter and expected terms to set validation fields and narrative-match booleans.
- Pick the primary diagnosis from the referral's diagnosis code when it matches the referral narrative and service line. Put symptom/supporting codes in the supporting set when the encounter or referral narrative ties them to the request.
- Allergy readiness comes from active allergy records plus referral/intake evidence. Use complete documented status only when allergen, reaction, severity, status, and source are present and non-conflicting. Missing, inactive-only, or conflicting allergy evidence should set the corresponding hold/follow-up status.
- Recent encounter evidence should be the most recent signed or amended encounter that directly supports the referral reason, diagnosis, medications, or care plan. Do not select a newer unrelated visit.
- Required document evidence should combine referral `documents_received` with patient document records. Prefer final documents when a document object exists. Add missing document blockers exactly from template enum values.
- Medication highlights should include active medications relevant to the referral service and diagnosis first. Assign normalized highlight reasons from clinical role, such as disease-specific diuretic, blood-pressure management, diabetes management, lipid management, or other active medication.
- Receiving provider, authorization, urgency, and readiness fields come from referral detail and provider lookup. Approved/open referrals with all required clinical and document evidence are ready; pending/missing authorization or missing required evidence creates the corresponding hold and blocker codes.

## Care Transition Packets

- Use the requested patient and recipient provider IDs from the prompt. Fetch recipient details from the provider directory.
- Active condition, medication, and allergy key arrays come only from active patient endpoints.
- Select handoff encounters by relevance to the transition and service line, then date. For surgical/orthopedic handoffs, prefer signed or amended encounters in the handoff window that discuss surgical handoff, specialty evaluation, affected joints, perioperative plans, active relevant medications, or chronic conditions that affect surgery. Exclude stale encounters, unrelated visits, and later visits about unrelated problems even if they are newer.
- Latest immunization is the immunization with the greatest date unless the template narrows vaccine type.
- Disclosure must match the recipient provider or facility, permitted status, and packet purpose. If absent or not permitted, mark readiness blocked with the template's disclosure issue code.
- Derive risk flags only when supported by active lists or encounter evidence. Common mappings:
  - cognitive or memory condition evidence -> cognitive memory risk
  - active hypertension condition -> hypertension risk
  - active diabetes plus insulin medication -> insulin-dependent diabetes and perioperative glucose plan risk for surgery
  - active latex allergy -> latex allergy risk
  - orthopedic lower-extremity disease, pain medication, or fall-risk notes -> fall-risk note risk
- For risk evidence, include only schema-supported evidence arrays. If the schema has no allergy evidence field, an allergy-derived risk may have empty condition/medication/encounter arrays.
- Readiness is `ready_with_risk_flags` when all required packet components exist and only nonblocking risk flags remain.

## ServiceRequest Quality Reviews

- Patient-scoped service requests are under `/api/patients/{patient_id}/service-requests`; filter by `service_request_id`.
- Validate service code through `/api/service-codes/{code}`. `service_code_valid` requires an active code whose service line matches the performer.
- Lookup requester and performer providers. Use performer service line from the performer provider directory record.
- Validate every reason code with `/api/icd10/{code}` and compare each code to patient conditions, encounters, imaging/document narrative, and ServiceRequest SBAR text.
- SBAR coverage is complete only when situation, background, assessment, and recommendation are present and substantive.
- Some quality-queue tasks ask for a normalized order state, not the raw draft state. If the prompt describes validation of a draft request and all required fields, service code, reason codes, performer, occurrence date, and SBAR are valid, emit the normalized active/order-ready status requested by the template. Keep raw `draft` only when the template clearly asks for raw source state or evidence remains incomplete.

## Referral Batch Audits

- Filter `/api/referrals` by the requested `batch_id`. Batch counts are over referral rows after filtering; unique patient counts are distinct `patient_id` values.
- For service-line-specific code audits, validate each referral diagnosis code through ICD lookup. If the actual chapter differs from the expected chapter in the template, emit an out-of-range issue. Unknown codes are `unknown_code`.
- Laterality and narrative mismatch rules:
  - Lowercase and normalize punctuation before comparison.
  - Use ICD `expected_terms` as the source of expected anatomy, diagnosis, and laterality.
  - Emit `laterality_mismatch` when expected terms contain left/right and the narrative contains the opposite side.
  - Emit `missing_laterality` only when the narrative otherwise matches the expected diagnosis/anatomy but omits the required side.
  - Emit `narrative_mismatch` when the narrative points to a different body part, diagnosis, or clinical domain. If the narrative is wholly unrelated, narrative mismatch is enough even if it also lacks side words.
- Duplicate referral groups are same-patient resubmissions, usually signaled by duplicate IDs, duplicate/resubmission coordination notes, same service line/date, and overlapping diagnosis context. Include all rows in the group and tier all group rows as duplicate blockers when the template says so.
- Insurance/patient anomalies are cross-patient signals, especially shared insurance IDs among different patients in the batch. Do not turn these into merge decisions unless duplicate evidence supports it; use a verify-membership disposition when requested.
- Follow-up queues:
  - authorization missing/pending come directly from referral authorization status.
  - records requests usually mean required office-note records are absent from `documents_received`.
  - imaging follow-up includes rows whose coordination note indicates imaging is pending or whose service-line-appropriate imaging evidence is absent.
- Action tiers:
  - Tier 1: urgent coding problems, urgent clinical blockers, or duplicate-blocker group rows.
  - Tier 2: routine coding, authorization, clinical mismatch, or document blockers.
  - Tier 3: administrative document completion only, with no coding, authorization, duplicate, or clinical mismatch blocker.
  - Owner provider is usually the receiving/performing provider unless the template defines another assignment rule.
- Summary counts must equal the emitted arrays and source referral counts. Recompute them after sorting and de-duplicating.

## Final JSON Checks

- Match the template's top-level keys exactly. Do not add commentary, provenance notes, or unused evidence.
- Preserve booleans, nulls, integers, dates, and enum strings exactly as the template expects.
- Use stable IDs for evidence. Use narrative text only for fields that explicitly ask for descriptions, care-plan tags, document types, or diagnosis narratives.
- Re-open the final JSON mentally against the prompt: every requested object should be supported by API evidence, and every exclusion should be intentional.
