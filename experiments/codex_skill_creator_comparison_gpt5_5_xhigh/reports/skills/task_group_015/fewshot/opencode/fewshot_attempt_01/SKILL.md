---
name: ehr-quality-json-packets
description: Produce normalized JSON for read-only EHR quality-governance tasks by querying task-environment APIs and reconciling duplicate candidates, referrals, ServiceRequests, care-transition packets, documents, providers, ICD-10 codes, and active clinical lists. Use whenever a prompt asks for an EHR/referral/duplicate/merge-readiness/care-transition/audit packet that must conform exactly to an answer_template.json.
---

# EHR Quality JSON Packets

Use this skill for read-only EHR quality tasks where the answer must be one normalized JSON object derived from a task environment API and a local `answer_template.json`.

## First Pass

1. Read the user prompt, `input/payloads/answer_template.json`, every other payload file, and `environment_access.md` if present.
2. Extract the explicit identifiers: patient IDs, candidate IDs, referral IDs, ServiceRequest IDs, provider IDs, batch IDs, service line, requested date, and requested packet type.
3. Treat the template as the output contract. Preserve required top-level keys, nested keys, JSON types, enum spelling, date format, nullability, and any ordering rules.
4. Use the API as the source of truth. Do not infer final values from identifier names, examples, or general medical knowledge when an endpoint can verify them.
5. Return JSON only. Do not include markdown, comments, prose, citations, or procedural notes outside the JSON object.

## API Collection Pattern

Use only endpoints permitted by the task environment. Fetch detail endpoints for IDs named in the prompt, then broaden through list/search endpoints only when a batch, patient relationship, or missing linked record requires it.

Common endpoint usage:

- Patient identity: `GET /api/patients/{patient_id}`.
- Active lists: `GET /api/patients/{patient_id}/conditions`, `/medications`, `/allergies`.
- Timeline evidence: `GET /api/patients/{patient_id}/encounters`, `/documents`, `/immunizations`, `/disclosures`, `/service-requests`.
- Duplicate review: `GET /api/duplicates/{candidate_id}` and candidate search/list if the detail links are incomplete.
- Referral work: `GET /api/referrals/{referral_id}` or `GET /api/referrals` filtered locally by batch, patient, service line, or requested date.
- Coding validation: `GET /api/icd10/{code}` for each diagnosis code and `GET /api/service-codes/{code}` for each service code.
- Provider contact: `GET /api/providers/{provider_id}` or provider list filtered locally by service line/facility/name.
- Audit evidence: `GET /api/audit-logs`, filtered to the relevant candidate, patient, referral, or merge event.

Practical collection sequence:

```text
read template -> collect named records -> collect linked patient/provider/coding records -> collect active lists -> collect evidence records -> classify -> sort -> validate JSON
```

If a list endpoint returns all records, filter locally. If a detail endpoint and a list endpoint disagree, prefer the endpoint that is most specific to the authoritative object unless the template explicitly names another authority.

## Normalization Rules

- Use IDs and normalized keys from records exactly as returned.
- Include only active/current clinical list items unless the template asks for inactive, excluded, or distractor records.
- Use patient active-list endpoints as authoritative for condition/medication/allergy unions; duplicate previews can omit active data.
- Represent absent optional evidence as `null` only when the template allows null; otherwise use the template's missing/blocked enum plus empty arrays.
- Sort string arrays ascending when the template says set semantics or gives no contrary order.
- Sort object arrays by the template rule. Common rules are by `code`, by `referral_id`, by `risk_flag`, newest-to-oldest encounter date, or referral-relevant medications first.
- When two template sections ask for the same concept under different names, fill them consistently from the same computed values.
- Compute summary counts from the finalized arrays and classifications, not from intermediate guesses.
- Never emit placeholder schema text such as `"string"` or `"enum: ..."`.

## Duplicate And Merge Review

For duplicate candidates and merge packets:

1. Fetch the duplicate candidate plus both patient records, their active lists, relevant documents, provider links, and audit history.
2. Use candidate status and candidate-provided target/source fields when present. If a source record is already marked as a duplicate of an active canonical record, target the active canonical patient.
3. Compare identity fields and normalized business signals: DOB, phone, insurance, address, name variants, sex, PCP, external continuity evidence, and any candidate match/conflict signals.
4. Strong identity agreement with no material conflicts supports merge readiness. Material conflicts such as different DOB, different phone, different given name, inconsistent laterality/problem evidence, or unclear candidate status require manual review/hold. A non-duplicate status supports do-not-merge.
5. Build active condition, medication, and allergy unions from both patient active-list endpoints. Record keys added from active endpoints when the duplicate preview omitted them.
6. Choose packet documents narrowly: identity-supporting, external continuity, or explicitly required final documents. Exclude chart summaries, stale items, preliminary/cancelled documents, unrelated patient documents, and unrelated audit logs when the template asks for exclusions.
7. Select packet contacts from provider records linked to the relevant specialist evidence and include PCP contact if requested.

## Referral Coordination

For one-referral packets:

1. Fetch the referral, patient detail, active diagnoses/medications/allergies, recent encounters, documents, receiving provider, and ICD-10 records for every diagnosis code.
2. Active diagnoses should include active problem-list conditions and referral-intake diagnoses when the template expects both. Mark referral relevance by matching the referral service line, narrative, recent encounter plan, or required letter diagnosis.
3. Choose the primary code from the referral's clinical reason and service line; put symptom or supporting codes in supporting-code arrays when they are not the primary diagnosis.
4. Validate code narratives against ICD lookup chapter, description, expected terms, laterality, and the referral narrative. Use exact template enums for valid, mismatch, invalid, or wrong-chapter outcomes.
5. Allergy readiness comes from active allergy records and referral form allergy evidence. Conflicting, incomplete, missing, or inactive-only allergy records should drive the readiness enum and blockers.
6. Recent encounter evidence should be the signed/amended encounter most relevant to the referral reason, not merely the latest encounter.
7. Required documents should be final/received and match the document type requested by the template. Missing office notes, imaging, authorization, medication list, or allergy confirmation should appear in the requested missing/blocking fields.
8. Highlight medications that affect the referral service line or packet readiness before ordinary active medications.
9. For referral-letter choice fields, select the exact enum whose meaning is supported by the evidence; do not invent new choice labels.

## Care Transition Packets

For care-transition summaries:

1. Fetch patient identity, recipient provider, active lists, encounters, immunizations, disclosures, documents if relevant, and provider directory records.
2. Select handoff encounters by the template's handoff rule: service-line relevance, transition purpose, signed/amended status, recency window, and requested count. Sort selected encounters newest to oldest.
3. Track excluded encounters when the template asks for a selection audit. Exclude stale, unrelated, unsigned/draft, or outside-window records according to the template.
4. Use the latest immunization by date, unless the template asks for a specific vaccine class.
5. Choose the disclosure that matches the recipient/provider, purpose, and permitted status. A missing, expired, denied, or pending disclosure is a readiness blocker when the template says disclosure is required.
6. Derive risk flags only from allowed template values and support each emitted flag with active condition keys, medication keys, allergy keys where represented by the schema, and encounter IDs when available.
7. Mark ready-with-risk-flags when risks exist but all required packet components are present and permitted. Mark not-ready only for true missing or blocking requirements.

## ServiceRequest Quality

For ServiceRequest quality review:

1. Fetch the ServiceRequest from the patient endpoint or detail source named by the prompt.
2. Validate `status`, `intent`, `priority`, authored/occurrence dates, requester, performer, performer service line, and service code.
3. Validate every reason code through ICD-10 lookup. A code can be valid while still requiring chapter or evidence review depending on the template.
4. Compare reason codes to active patient conditions, encounter evidence, and referral narrative. Laterality conflicts between the patient evidence and the reason code are quality signals, not formatting issues.
5. For SBAR coverage, inspect the request narrative or structured sections and report exactly which required sections are present or missing.

## Batch Referral Audits

For referral batch audits:

1. Fetch all referrals in the requested batch, then related ICD-10, patient, provider, document, and authorization evidence as needed.
2. Count total referral rows and distinct patients after filtering to the requested batch.
3. For each referral, validate the diagnosis code:
   - Unknown ICD lookup result means unknown-code.
   - Valid code from a chapter outside the expected service-line chapter is out-of-range when the template asks for service-line chapter compliance.
   - Narrative mismatch compares the referral narrative to ICD terms and common clinical synonyms from the lookup.
   - Laterality mismatch compares left/right in the code terms against left/right in the narrative or patient evidence.
   - Missing laterality applies when the code is lateralized but the narrative omits a required side.
4. Detect same-patient duplicate groups from repeated referrals for the same patient and same clinical episode/service. Do not collapse same-insurance different-patient cases into duplicate referrals; classify those as insurance/patient anomalies if requested.
5. Build follow-up queues from evidence fields: missing authorization, pending authorization, missing office note/records, and missing or pending imaging.
6. Tier action plans from finalized issues. Urgent referrals, duplicate blockers, and urgent coding blockers go to immediate action; routine coding/auth/document blockers go to short-term action; administrative document completion goes to administrative action.
7. Summary counts must equal the emitted arrays and queues, including duplicate group count, anomaly count, each follow-up queue count, tier counts, and validated-ready count.

## Final Verification

Before answering:

- Parse the JSON locally if possible.
- Check every required template key is present and no extra narrative keys were added.
- Check all enum values are copied exactly from the template.
- Check ordered arrays follow the template, especially encounter chronology and referral/object arrays.
- Recompute set arrays for duplicates and active-list unions from source records.
- Recompute summary counts after the final arrays are sorted.
- Confirm every emitted ID came from the API or task payloads.
- Confirm the final response is a single JSON object and nothing else.
