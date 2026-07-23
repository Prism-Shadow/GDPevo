---
name: ehr-quality-packet-audit
description: Produce normalized JSON for EHR quality-governance tasks using task-provided schemas and records, including duplicate chart merge readiness packets, referral coordination packets, orthopedic care-transition summaries, ServiceRequest validation, and referral batch audits.
---

# EHR Quality Packet Audit

## Core Workflow

1. Read the task prompt and answer template first. Treat required keys, enum values, nullability, and ordering rules as the output contract.
2. Gather only the records needed by the template from the task-provided EHR environment: case object, patient demographics, active clinical lists, encounters, documents, disclosures, immunizations, audit entries, providers, referrals, ServiceRequests, and code directories as applicable.
3. Output normalized JSON only. Use stable IDs from records, not prose explanations.
4. Sort arrays when the schema describes set semantics or an explicit sort order. Make summary counts match the emitted arrays exactly.
5. Prefer structured fields over narrative notes when they conflict. Use narrative notes to identify follow-up queues, handoff intent, or risk flags only when structured fields do not already resolve the field.

## Duplicate Review And Merge Packets

- Use the duplicate candidate's preferred target/source only when present and supported by patient canonical status. Leave target/source null when the candidate provides no merge target.
- Use active clinical-list records as authoritative for final active condition, medication, and allergy unions. Treat duplicate previews as incomplete and report active-list keys missing from the preview when the schema asks.
- Preserve every active normalized key, even if the key looks generic. Exclude inactive records and unrelated evidence.
- Copy source match and conflict signal labels exactly. Avoid invented reason labels unless the template requires a separate normalized reason-code field.
- Treat minor normalized-address differences as non-blocking conflict signals when strong identity matches and canonical duplicate status support a merge. Treat different names, different phones, and opposing laterality problems with no merge target as a review hold.
- Select packet documents for identity verification or external continuity evidence. Exclude routine chart summaries unless the template explicitly requests them.
- Resolve specialist and primary-care contacts from provider records tied to the referral, document source, or patient record.

## Referral Coordination

- Validate the referral diagnosis with the code directory. Set the primary code from the referral row and include supporting codes only for active diagnoses directly represented in the referral narrative or recent referral encounter.
- Mark active diagnoses as referral-relevant only when they directly support the referral diagnosis or narrative symptom. Do not mark stable comorbidities as referral-relevant just because they are specialty-adjacent.
- When an active allergy record has allergen, reaction, severity, status, and source, treat allergy readiness as complete unless there are conflicting allergy records. Do not create a blocker from a loose note asking to confirm details.
- For required documents, combine referral-received flags, document records, and signed encounter evidence. A signed encounter can satisfy an office-note requirement when no separate office-note document object exists.
- Set readiness blockers only for actual missing authorization, missing required documents, missing provider, invalid diagnosis code, or clinical mismatch.
- Highlight medications directly tied to referral management first. Include specialty-relevant active medications; omit unrelated active baseline medications unless the schema asks for all active medications.

## Care Transition Packets

- Use active condition, medication, and allergy records for current-list keys.
- Select explicit care-transition or handoff encounter series before newer unrelated encounters. Respect the required count and order selected encounters newest to oldest.
- Record selected encounter IDs and excluded reviewed encounter IDs when the schema asks for source selection.
- Derive risk flags from active conditions, medications, allergies, and handoff notes. Use minimal evidence arrays for each flag; if the schema has no allergy evidence field, leave condition, medication, and encounter arrays empty for allergy-only flags.
- Mark a packet ready with risk flags when patient, recipient, active lists, required handoff encounters, latest immunization, and permitted disclosure are present. Reserve not-ready status for missing required objects or non-permitted disclosure.

## ServiceRequest Quality Validation

- Use the actual ServiceRequest requester and performer fields from the record. Do not substitute a different provider from case context.
- Validate service code activity and service line through the service-code record.
- Validate each reason code through the code directory and patient evidence. Match patient evidence against active conditions and relevant encounters.
- Mark SBAR complete when situation, background, assessment, and recommendation are all present and non-empty.
- Preserve a duplicate candidate's raw review status when it is still under review. Use a review-hold decision for serious conflicts with no canonical merge target/source.

## Referral Batch Audits

- Filter to the requested batch before counting rows or unique patients.
- Follow the template's expected diagnosis chapter literally. If the code directory's actual chapter differs from the expected chapter, classify the referral as out-of-range even when the code may be clinically related.
- Detect narrative/code mismatches by comparing the referral narrative with the code directory's expected terms. Add `laterality_mismatch` for opposing left/right language and `missing_laterality` when the code requires laterality but the narrative gives no side.
- Identify duplicate groups from same-patient resubmission signals and include every row in the duplicate group when the policy requires all duplicate rows to be duplicate blockers.
- Identify shared-insurance anomalies across distinct patient IDs. Include all batch referral IDs attached to the anomalous patient IDs and do not infer a merge from shared insurance alone.
- Populate authorization queues directly from referral authorization status. Populate records requests from missing office-note evidence.
- Populate imaging follow-up from explicit imaging-pending notes or when a referral has no imaging document type at all.
- Tier each referral once at its highest applicable severity: Tier 1 for urgent coding issues or duplicate blockers, Tier 2 for routine coding, authorization, or document blockers, and Tier 3 for documentation-only administrative completion.
- Recompute all summary counts from the final emitted arrays and tier lists before returning JSON.
