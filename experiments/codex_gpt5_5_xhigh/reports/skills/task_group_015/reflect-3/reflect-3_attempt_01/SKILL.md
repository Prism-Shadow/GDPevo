---
name: ehr-quality-packet-builder
description: Build normalized JSON packets and audits from EHR quality-governance data. Use when Codex must reconcile patient charts, duplicate candidates, referrals, ServiceRequests, provider records, clinical lists, documents, encounters, immunizations, disclosures, ICD/service-code metadata, or batch referral queues into a strict answer template.
---

# EHR Quality Packet Builder

## Core Workflow

1. Read the user prompt and the answer template first. Treat the template as the contract for top-level keys, enum values, field names, sort order, and whether arrays are sets.
2. Identify the governing object IDs from the prompt, then gather the minimum supporting records needed for those IDs: primary objects, patient demographics, active clinical lists, provider details, documents, encounters, immunizations, disclosures, diagnosis-code metadata, and service-code metadata.
3. Build the answer from evidence, not narrative assumptions. Prefer directory/lookup records over free text when validating codes, providers, service lines, or contact fields.
4. Emit JSON only. Preserve the template shape, use `null` only when the template permits it, and do not add explanatory keys.
5. Sort ID arrays and normalized-key arrays ascending unless the template gives a different order. Sort encounter handoff lists by the requested clinical rule, commonly newest to oldest.
6. Keep counts synchronized with the arrays they summarize.

## Active Lists

- Include only active clinical records when a field asks for current condition, medication, or allergy keys.
- Use each record's `normalized_key`; deduplicate and sort.
- Exclude inactive, entered-in-error, stale, or unrelated distractor records unless the template explicitly asks for excluded evidence.
- When reconciling a duplicate preview against patient active-list records, prefer the patient active-list records as authoritative and report active keys present there but missing from the preview.
- For referral medication highlights, include medications relevant to the specialty reason first. Do not include every active medication unless the template asks for all active medications.

## Duplicate Review

- Use canonical patient links and duplicate-candidate merge previews when present to select target and source.
- A strong canonical link with only minor identity conflicts can still be merge-ready. Do not require manual review solely for address abbreviations or nickname/name-variant signals when demographics and canonical linkage support the merge.
- Hard conflicts such as different given names, different phones, opposite laterality problems, or no preferred merge target should hold the review rather than forcing a merge target/source.
- Keep match and conflict signal arrays copied from the governing duplicate record and sorted when set semantics apply.
- Evidence documents for merge packets should be identity or external-continuity records when the template asks for packet evidence; chart summaries are usually distractors unless explicitly requested.

## Referral Packets

- Validate the referral diagnosis through the diagnosis-code directory. Use the directory chapter and expected terms for chapter, narrative, and laterality checks.
- Include all active diagnoses when the template asks for active diagnoses, and mark referral relevance separately.
- A complete active allergy record with allergen, reaction, severity, status, and source is ready for a letter even when a coordination note says to confirm it. Treat allergy as blocking only when details are missing or records conflict.
- Use referral `documents_received` to satisfy document-presence booleans such as office-note receipt. Use document records when the template asks for a document ID, date, type, or final/preliminary status.
- Overall readiness is ready when authorization is approved, required documents are present, the receiving provider resolves, diagnosis coding matches, and allergies are documented.

## Care Transitions

- Select handoff encounters by specialty relevance, requested transition purpose, recency, and acceptable signed status. Exclude newer encounters that are unrelated to the transition and older stale records outside the useful handoff window.
- When the template specifies an exact handoff length, return exactly that many selected encounters and list reviewed exclusions separately if requested.
- Choose the latest immunization by date.
- Choose the disclosure matching the recipient/provider and required purpose; a permitted disclosure allows sending when other packet requirements are present.
- Risk flags come from active conditions, active medications, active allergies, and explicit encounter notes. Risk flags usually make the packet ready with risk flags rather than blocked unless the template defines a missing required item.

## ServiceRequest Quality

- A service code is valid when it is active in the service-code directory and aligns with the performer service line.
- Validate each reason code through the diagnosis-code directory. Record the directory chapter and whether the code matches active patient conditions or relevant encounters.
- Do not mark an existing diagnosis code invalid only because its chapter is not the specialty's usual chapter unless the template specifically asks for out-of-range specialty chapters.
- SBAR coverage is complete only when situation, background, assessment, and recommendation are all present and non-empty.

## Batch Referral Audits

- Filter exactly to the requested batch before computing rows, unique patients, counts, queues, duplicate groups, or action tiers.
- For invalid or out-of-range diagnosis queues, compare each code's directory chapter to the template's expected specialty chapter. Include existing codes from other chapters as out-of-range when the template requires that comparison; use unknown-code only when the lookup is absent.
- For narrative and laterality queues, compare the referral narrative to the code directory expected terms:
  - Use `laterality_mismatch` when the narrative names the opposite side.
  - Use `missing_laterality` when the code requires laterality and the narrative has no side.
  - Use `narrative_mismatch` when body site or condition does not match the expected terms.
- Build same-patient duplicate groups from repeated patient referrals and duplicate/resubmission notes. Tier every row in a same-patient duplicate group as a duplicate blocker when the template policy says so.
- Flag shared-insurance anomalies only for different patient IDs sharing the same insurance in the audited batch; keep them separate from same-patient duplicate groups.
- Queue missing authorization and pending authorization separately from document follow-up.
- Queue record requests when required office-note documentation is missing.
- Queue imaging follow-up when the referral says imaging is pending or when no imaging document is present.
- Assign tiers consistently:
  - Tier 1: urgent coding blockers and same-patient duplicate blockers.
  - Tier 2: routine coding, authorization, or substantive document blockers.
  - Tier 3: administrative document completion without coding or authorization blockers.
